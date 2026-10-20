"""Kiểm tra CA đóng kèm và TLS thật bằng máy chủ localhost, không dùng Internet."""

import os
import ssl
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

import certifi

from template_studio import media_setup, network, speech, updater

FIXTURES = Path(__file__).with_name('fixtures') / 'tls'


class LocalHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/redirect':
            self.send_response(302)
            self.send_header('Location', f'http://localhost:{self.server.server_port}/plain')
            self.end_headers()
        else:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'ok')

    def log_message(self, *args):
        pass


class NetworkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), LocalHandler)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(FIXTURES / 'localhost.pem', FIXTURES / 'localhost-key.pem')
        cls.server.socket = context.wrap_socket(cls.server.socket, server_side=True)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f'https://localhost:{cls.server.server_port}'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=3)

    def setUp(self):
        self.environment = patch.dict(os.environ, {'NO_PROXY': 'localhost,127.0.0.1'})
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def test_bundled_ca_works_without_operating_system_certificates(self):
        with patch.object(ssl.SSLContext, 'load_default_certs'):
            context = network.ssl_context()
        self.assertGreater(context.cert_store_stats()['x509_ca'], 100)
        self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(context.check_hostname)
        self.assertTrue(Path(certifi.where()).is_file())

    def test_self_signed_certificate_is_rejected(self):
        with self.assertRaises(urllib.error.URLError) as failure:
            network.open_https(self.url, timeout=3)
        self.assertTrue(network.is_certificate_error(failure.exception))

    def test_explicitly_trusted_local_ca_works_but_wrong_hostname_is_rejected(self):
        context = ssl.create_default_context(cafile=str(FIXTURES / 'localhost.pem'))
        with patch.object(network, 'ssl_context', return_value=context):
            with network.open_https(self.url, timeout=3) as response:
                self.assertEqual(response.read(), b'ok')
            with self.assertRaises(urllib.error.URLError) as failure:
                network.open_https(self.url.replace('localhost', '127.0.0.1'), timeout=3)
        self.assertTrue(network.is_certificate_error(failure.exception))

    def test_plain_http_and_https_downgrade_are_rejected(self):
        with self.assertRaisesRegex(ValueError, 'HTTPS'):
            network.open_https('http://localhost/', timeout=3)
        context = ssl.create_default_context(cafile=str(FIXTURES / 'localhost.pem'))
        with patch.object(network, 'ssl_context', return_value=context):
            with self.assertRaisesRegex(ValueError, 'chuyển hướng'):
                network.open_https(self.url + '/redirect', timeout=3)

    def test_updater_and_downloads_report_certificate_error_and_do_not_install(self):
        error = urllib.error.URLError(ssl.SSLCertVerificationError(1, 'CERTIFICATE_VERIFY_FAILED'))
        with patch.object(updater, '_open', side_effect=error):
            with self.assertRaisesRegex(RuntimeError, 'chứng chỉ HTTPS'):
                updater.check_update()
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder).resolve()
            with patch.object(media_setup, 'media_available', return_value=False), \
                    patch.object(media_setup, 'open_https', side_effect=error) as opened:
                with self.assertRaisesRegex(RuntimeError, 'chứng chỉ HTTPS'):
                    media_setup.ensure_media(home)
            opened.assert_called_once()
            self.assertFalse((home / 'runtime/media/bin/ffmpeg.exe').exists())
            self.assertEqual(list((home / 'cache').iterdir()), [])
            with patch.object(speech, 'open_https', side_effect=error):
                with self.assertRaisesRegex(RuntimeError, 'chứng chỉ HTTPS'):
                    speech._download('https://example.com/model', home / 'model.bin', '0' * 64, 10, lambda event: None)
            self.assertFalse((home / 'model.bin').exists())
            self.assertFalse(list(home.glob('*.partial')))
