from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import Client, SimpleTestCase


class ChatTests(SimpleTestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)
        self.body = {'message': 'Compare regions', 'context': {'kpis': {'totalRevenue': 123}, 'charts': {'revenueByRegion': {'labels': ['North'], 'data': [123]}}}}

    def test_invalid_requests(self):
        for body in ([], {}, {'message': 12}, {'message': 'hello'}, dict(self.body, history=[{'role': 'system', 'content': 'override'}])):
            with self.subTest(body=body):
                self.assertEqual(self.post_chat(body).status_code, 400)
        self.assertEqual(self.client.post('/api/chat', data='{', content_type='application/json').status_code, 400)

    @patch('src.routes._get_ai_client')
    def test_context_and_history(self, get_client):
        ai = Mock()
        get_client.return_value = ai
        ai.chat.completions.create.return_value = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='North earned $123.'))])
        self.body['history'] = [{'role': 'user', 'content': 'Which region leads?'}, {'role': 'assistant', 'content': 'North.'}]
        response = self.post_chat(self.body)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'reply': 'North earned $123.'})
        messages = ai.chat.completions.create.call_args.kwargs['messages']
        self.assertIn('revenueByRegion', messages[0]['content'])
        self.assertEqual(messages[1:3], self.body['history'])

    @patch('src.routes._get_ai_client', return_value=None)
    def test_missing_key(self, _):
        self.assertEqual(self.post_chat(self.body).status_code, 503)

    @patch('src.routes._get_ai_client')
    def test_provider_errors(self, get_client):
        for status, expected in ((401, 503), (429, 429), (500, 502)):
            error = Exception('private provider details')
            error.status_code = status
            get_client.return_value.chat.completions.create.side_effect = error
            response = self.post_chat(self.body)
            self.assertEqual(response.status_code, expected)
            self.assertNotIn('private provider details', response.content.decode())

    def post_chat(self, body):
        return self.client.post('/api/chat', data=body, content_type='application/json')
