"""Kiểm tra nguồn phát hành, toàn vẹn gói và giới hạn giải nén."""
import hashlib
import io
import json
import os
import stat
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from template_studio import updater
from template_studio.version import ASSET_NAME, REPOSITORY


def package_bytes(extra=None, version='2.0.0'):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as archive:
        for name, content in {
            'TemplateStudio/TemplateStudio.exe': b'MZ-binary-test',
            'TemplateStudio/_internal/marker.txt': b'Qt-test',
            'TemplateStudio/release.json': json.dumps({'version': version, 'platform': 'windows-x64'}),
            **(extra or {}),
        }.items():
            archive.writestr(name, content)
    return buffer.getvalue()


def release_data(payload):
    return dict(tag_name='v2.0.0', draft=False, prerelease=False, assets=[dict(
        name=ASSET_NAME, size=len(payload), state='uploaded',
        digest='sha256:' + hashlib.sha256(payload).hexdigest(),
        browser_download_url=f'https://github.com/{REPOSITORY}/releases/download/v2.0.0/{ASSET_NAME}')])


class ReleaseTests(unittest.TestCase):
    def test_version_order_and_stable_only(self):
        self.assertGreater(updater.version_tuple('v1.10.0'), updater.version_tuple('1.9.9'))
        for value in ('v1.0', 'v1.0.0-beta', '../v2.0.0'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                updater.version_tuple(value)
        release = release_data(package_bytes())
        self.assertIsNone(updater.parse_release(release, current='2.0.0'))
        release['prerelease'] = True
        self.assertIsNone(updater.parse_release(release, current='1.0.0'))

    def test_refuses_foreign_url_missing_digest_or_large_asset(self):
        for key, value in [('browser_download_url', 'https://example.com/app.zip'),
                           ('digest', None), ('size', updater.MAX_DOWNLOAD + 1), ('state', 'new')]:
            release = release_data(package_bytes())
            release['assets'][0][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                updater.parse_release(release, current='1.0.0')


class PackageTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.folder = Path(self.temporary.name)

    def archive(self, payload):
        archive = self.folder / 'app.zip'
        archive.write_bytes(payload)
        return archive

    def test_accepts_complete_package(self):
        stage = updater.extract_package(self.archive(package_bytes()), self.folder / 'stage', '2.0.0')
        self.assertTrue((stage / 'TemplateStudio.exe').is_file())

    def test_rejects_path_traversal_reserved_paths_and_user_data_before_extract(self):
        for name in ['../escape.txt', 'TemplateStudio/_internal/../../escape.txt',
                     'TemplateStudio/data/session.json', 'TemplateStudio/_internal/CON.txt',
                     'TemplateStudio/_internal/file:stream', 'TemplateStudio/_internal/folder./file',
                     'TemplateStudio//_internal/ambiguous']:
            with self.subTest(name=name):
                destination = self.folder / 'invalid'
                with self.assertRaises(ValueError):
                    updater.extract_package(self.archive(package_bytes({name: b'bad'})), destination, '2.0.0')
                self.assertFalse(destination.exists())
        self.assertFalse((self.folder / 'escape.txt').exists())
        # zipfile tự chuẩn hóa dấu \ khi tạo ZIP trên Windows; đổi header để kiểm tra gói ngoài.
        payload = package_bytes({'TemplateStudio/_internal/backslash': b'bad'}).replace(
            b'TemplateStudio/_internal/backslash', b'TemplateStudio\\_internal\\backslash')
        with self.assertRaises(ValueError):
            updater.extract_package(self.archive(payload), self.folder / 'backslash', '2.0.0')

    def test_rejects_symlink_and_wrong_manifest(self):
        buffer = io.BytesIO(package_bytes())
        with zipfile.ZipFile(buffer, 'a') as archive:
            link = zipfile.ZipInfo('TemplateStudio/_internal/link')
            link.create_system = 3
            link.external_attr = (stat.S_IFLNK | 0o777) << 16
            archive.writestr(link, '../../outside')
        with self.assertRaises(ValueError):
            updater.extract_package(self.archive(buffer.getvalue()), self.folder / 'symlink', '2.0.0')
        with self.assertRaises(ValueError):
            updater.extract_package(self.archive(package_bytes(version='3.0.0')), self.folder / 'wrong', '2.0.0')

    @unittest.skipUnless(os.name == 'nt', 'Cài cập nhật chỉ dành cho Windows')
    def test_download_verifies_hash_and_never_changes_running_install(self):
        payload = package_bytes()
        release = updater.parse_release(release_data(payload), current='1.0.0')
        target = self.folder / 'app'
        target.mkdir()
        executable = target / 'TemplateStudio.exe'
        executable.write_bytes(b'MZ-old-version')
        with patch.object(updater.sys, 'frozen', True, create=True), \
                patch.object(updater.sys, 'executable', str(executable)), \
                patch.object(updater, '_open', return_value=io.BytesIO(payload)):
            plan = updater.prepare_update(release, self.folder / 'home')
        self.assertTrue(plan.is_file())
        self.assertEqual(executable.read_bytes(), b'MZ-old-version')
        release['sha256'] = '0' * 64
        with patch.object(updater.sys, 'frozen', True, create=True), \
                patch.object(updater.sys, 'executable', str(executable)), \
                patch.object(updater, '_open', return_value=io.BytesIO(payload)), self.assertRaises(ValueError):
            updater.prepare_update(release, self.folder / 'home')
        self.assertEqual(executable.read_bytes(), b'MZ-old-version')
