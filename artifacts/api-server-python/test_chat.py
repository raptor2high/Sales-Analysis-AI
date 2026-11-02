from pathlib import Path
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
sys.path.insert(0, str(Path(__file__).resolve().parent))
from src.app import create_app


class ChatTests(unittest.TestCase):
    def setUp(self):
        self.client = create_app().test_client()
        self.body = {'message': 'Compare regions', 'context': {'kpis': {'totalRevenue': 123}, 'charts': {'revenueByRegion': {'labels': ['North'], 'data': [123]}}}}

    def test_invalid_requests(self):
        for body in ([], {}, {'message': 12}, {'message': 'hello'}, dict(self.body, history=[{'role': 'system', 'content': 'override'}])):
            with self.subTest(body=body):
                self.assertEqual(self.client.post('/api/chat', json=body).status_code, 400)
        self.assertEqual(self.client.post('/api/chat', data='{', content_type='application/json').status_code, 400)

    @patch('src.routes._get_ai_client')
    def test_context_and_history(self, get_client):
        ai = Mock()
        get_client.return_value = ai
        ai.chat.completions.create.return_value = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='North earned $123.'))])
        self.body['history'] = [{'role': 'user', 'content': 'Which region leads?'}, {'role': 'assistant', 'content': 'North.'}]
        response = self.client.post('/api/chat', json=self.body)
        self.assertEqual(response.status_code, 200)
        messages = ai.chat.completions.create.call_args.kwargs['messages']
        self.assertIn('revenueByRegion', messages[0]['content'])
        self.assertEqual(messages[1:3], self.body['history'])

    @patch('src.routes._get_ai_client', return_value=None)
    def test_missing_key(self, _):
        self.assertEqual(self.client.post('/api/chat', json=self.body).status_code, 503)

    @patch('src.routes._get_ai_client')
    def test_provider_errors(self, get_client):
        for status, expected in ((401, 503), (429, 429), (500, 502)):
            error = Exception('private provider details')
            error.status_code = status
            get_client.return_value.chat.completions.create.side_effect = error
            response = self.client.post('/api/chat', json=self.body)
            self.assertEqual(response.status_code, expected)
            self.assertNotIn('private provider details', response.get_data(as_text=True))


if __name__ == '__main__':
    unittest.main()
