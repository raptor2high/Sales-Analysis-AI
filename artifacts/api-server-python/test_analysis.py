from pathlib import Path
import csv
import io
import json
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parent))
from src.app import create_app
from src.analyzer import parse_rows, analyze


class AnalysisWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.client = create_app().test_client()
        self.sample = (Path(__file__).parent.parent / 'sales-ai/public/sample.csv').read_bytes()

    def upload(self, content):
        return self.client.post('/api/analyze', data={'file': (io.BytesIO(content), 'sales.csv')})

    def test_upload_matches_engine(self):
        rows, warnings = parse_rows(csv.DictReader(io.StringIO(self.sample.decode())))
        response = self.upload(self.sample)
        self.assertEqual(response.status_code, 200)
        expected = json.loads((Path(__file__).parent / 'test_sample_expected.json').read_text(encoding='utf-8'))
        self.assertEqual(response.json['data'], expected)
        self.assertEqual(response.json['warnings'], warnings)
        self.assertEqual(response.json['rowCount'], len(rows))

    def test_bom_upload(self):
        self.assertEqual(self.upload(b'\xef\xbb\xbf' + self.sample).json, self.upload(self.sample).json)

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
        for path in ('/', '/app.js', '/sample.csv', '/api/healthz'):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                if path == '/app.js':
                    self.assertIn('function uploadAndAnalyze', response.text)
                response.close()


if __name__ == '__main__':
    unittest.main()
