from pathlib import Path
import csv
import io
import json
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, SimpleTestCase, override_settings

from src.analyzer import parse_rows


class AnalysisWorkflowTests(SimpleTestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)
        self.sample = (Path(__file__).parent.parent / 'sales-ai/public/sample.csv').read_bytes()

    def upload(self, content):
        return self.client.post('/api/analyze', {'file': SimpleUploadedFile('sales.csv', content)})

    def test_upload_matches_engine(self):
        rows, warnings = parse_rows(csv.DictReader(io.StringIO(self.sample.decode())))
        response = self.upload(self.sample)
        self.assertEqual(response.status_code, 200)
        expected = json.loads((Path(__file__).parent / 'test_sample_expected.json').read_text(encoding='utf-8'))
        body = response.json()
        self.assertEqual(body['data'], expected)
        self.assertEqual(body['warnings'], warnings)
        self.assertEqual(body['rowCount'], len(rows))

    def test_bom_upload(self):
        self.assertEqual(self.upload(b'\xef\xbb\xbf' + self.sample).json(), self.upload(self.sample).json())

    @override_settings(FILE_UPLOAD_MAX_MEMORY_SIZE=0)
    def test_disk_backed_upload(self):
        response = self.upload(self.sample)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])

    def test_bad_uploads(self):
        for content in (b'', b'date,product\n2024-01-01,A', b'\xff\xfe'):
            with self.subTest(content=content):
                self.assertEqual(self.upload(content).status_code, 400)

    def test_malformed_row_is_skipped(self):
        raw = [{'date': '2024-01-01', 'product': 'A', 'revenue': '5', 'quantity': '1', 'region': 'N', None: ['extra']}]
        rows, warnings = parse_rows(iter(raw))
        self.assertEqual(rows, [])
        self.assertIn('extra CSV fields', warnings[0])

    def test_static_workflow(self):
        for path in ('/', '/app.js', '/sample.csv', '/logo.png'):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                try:
                    content = b''.join(response.streaming_content)
                    if path == '/app.js':
                        self.assertIn(b'function uploadAndAnalyze', content)
                    if path == '/sample.csv':
                        self.assertEqual(content, self.sample)
                finally:
                    response.close()

        self.assertEqual(self.client.get('/api/healthz').json(), {'status': 'ok'})

    def test_upload_preflight(self):
        response = self.client.options(
            '/api/analyze',
            headers={'origin': 'https://dashboard.example', 'access-control-request-method': 'POST'},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['Access-Control-Allow-Origin'], '*')
        self.assertIn('POST', response.headers['Access-Control-Allow-Methods'])
