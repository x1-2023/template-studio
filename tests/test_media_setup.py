"""Runtime thiếu/hỏng phải được sửa trước khi đọc nguồn và không bị GPU che lỗi."""

import hashlib
import io
import json
import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from PySide6.QtWidgets import QApplication

from template_studio.app import Controller
from template_studio import media_setup
from template_studio.presets import normalize


class MediaSetupTests(unittest.TestCase):
    def fixture(self, home):
        archive=home/'source.zip'
        files={'ffmpeg.exe':b'MZ-ffmpeg-thu','ffprobe.exe':b'MZ-ffprobe-thu'}
        with zipfile.ZipFile(archive,'w') as package:
            for name,data in files.items():
                package.writestr('ffmpeg-test/bin/'+name,data)
        return archive, {name:hashlib.sha256(data).hexdigest() for name,data in files.items()}

    def test_missing_ffprobe_repairs_from_verified_cache_without_network(self):
        with tempfile.TemporaryDirectory() as folder:
            home=Path(folder).resolve()
            archive,files=self.fixture(home)
            cache=home/'cache'/f'ffmpeg-{media_setup.MEDIA_VERSION}-verified.zip'
            cache.parent.mkdir()
            cache.write_bytes(archive.read_bytes())
            destination=home/'runtime/media/bin'
            destination.mkdir(parents=True)
            (destination/'ffmpeg.exe').write_bytes(b'cu')
            with patch.dict(os.environ,{'TEMPLATE_STUDIO_HOME':str(home)}), \
                    patch.object(media_setup,'FILES',files), \
                    patch.object(media_setup,'MEDIA_SHA256',hashlib.sha256(archive.read_bytes()).hexdigest()), \
                    patch.object(media_setup,'binary',side_effect=FileNotFoundError('ffprobe')), \
                    patch.object(media_setup,'open_https') as network:
                media_setup.ensure_media(home)
                network.assert_not_called()
            self.assertEqual((destination/'ffprobe.exe').read_bytes(),b'MZ-ffprobe-thu')
            self.assertEqual((destination/'ffmpeg.exe').read_bytes(),b'MZ-ffmpeg-thu')

    def test_download_retries_and_keeps_verified_installer_for_repairs(self):
        with tempfile.TemporaryDirectory() as folder:
            home=Path(folder).resolve()
            archive,files=self.fixture(home)
            contents=archive.read_bytes()
            with patch.dict(os.environ,{'TEMPLATE_STUDIO_HOME':str(home)}), \
                    patch.object(media_setup,'FILES',files), \
                    patch.object(media_setup,'MEDIA_SHA256',hashlib.sha256(contents).hexdigest()), \
                    patch.object(media_setup,'binary',side_effect=FileNotFoundError('ffprobe')), \
                    patch.object(media_setup.time,'sleep'), \
                    patch.object(media_setup,'open_https',side_effect=[OSError('mất mạng'),io.BytesIO(contents)]) as network:
                media_setup.ensure_media(home)
                self.assertEqual(network.call_count,2)
            self.assertEqual((home/'cache'/f'ffmpeg-{media_setup.MEDIA_VERSION}-verified.zip').read_bytes(),contents)
            self.assertEqual((home/'runtime/media/bin/ffprobe.exe').read_bytes(),b'MZ-ffprobe-thu')
            self.assertEqual(len(list((home/'cache').glob('*.zip'))),1)

    def test_corrupt_managed_binary_is_not_reported_as_ready(self):
        with tempfile.TemporaryDirectory() as folder:
            home=Path(folder).resolve()
            directory=home/'runtime/media/bin'
            directory.mkdir(parents=True)
            for name in media_setup.FILES:
                (directory/name).write_bytes(b'MZ-hong')
            with patch.dict(os.environ,{'TEMPLATE_STUDIO_HOME':str(home)}), \
                    patch.object(media_setup,'binary',side_effect=lambda name:str(directory/(name+'.exe'))):
                self.assertFalse(media_setup.media_available(home))

    def test_download_failure_is_clear_and_leaves_no_partial_installer(self):
        with tempfile.TemporaryDirectory() as folder:
            home=Path(folder).resolve()
            with patch.dict(os.environ,{'TEMPLATE_STUDIO_HOME':str(home)}), \
                    patch.object(media_setup,'media_available',return_value=False), \
                    patch.object(media_setup.time,'sleep'), \
                    patch.object(media_setup,'open_https',side_effect=OSError('mạng bị chặn')) as network:
                with self.assertRaisesRegex(RuntimeError,'Thử lại FFmpeg'):
                    media_setup.ensure_media(home)
                self.assertEqual(network.call_count,3)
            self.assertEqual(list((home/'cache').iterdir()),[])


class MediaControllerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QApplication.instance() or QApplication([])

    def controller(self, home):
        with patch.object(Controller,'prepareMedia'):
            controller=Controller(Path.cwd(),home)
        # Chạy callback đồng bộ để mô phỏng thứ tự setup lỗi -> GPU thành công.
        def submit(work, result=None, error=None, event=None, finished=None):
            try:
                value=work(event or (lambda value:None))
            except Exception as failure:
                if error:
                    error(str(failure))
                else:
                    raise
            else:
                if result:
                    result(value)
            finally:
                if finished:
                    finished()
        controller.pool.submit=submit
        return controller

    def test_gpu_success_does_not_hide_failed_media_setup(self):
        with tempfile.TemporaryDirectory() as folder:
            home=Path(folder).resolve()
            controller=self.controller(home)
            with patch('template_studio.app.ensure_media',side_effect=RuntimeError('mạng bị chặn')):
                controller.prepareMedia()
            with patch('template_studio.production.run_worker',return_value=dict(gpu='NVIDIA thử')), \
                    patch('template_studio.production.discover',return_value=None):
                controller.production.checkRuntime()
            self.assertFalse(controller.mediaReady)
            self.assertIn('FFmpeg/ffprobe',controller.production.runtimeNotice)
            self.assertIn('mạng bị chặn',controller.production.runtimeNotice)
            self.assertTrue((home/'media-setup-error.log').is_file())

    def test_runtime_repair_recovers_only_missing_tool_errors_and_preserves_configs(self):
        with tempfile.TemporaryDirectory() as folder:
            home=Path(folder).resolve()
            controller=self.controller(home)
            source=home/'nguồn.mp4'
            source.write_bytes(b'nguon')
            p=controller.production
            config=normalize(dict(video_bitrate=7,part_count=3))
            p._rows=[dict(id=str(i),path=str(source),name=source.name,status='Lỗi',percent=0,duration=0,meta='',
                detail=error,config=config.copy(),presetName='Mẫu riêng') for i,error in enumerate([
                    'Thiếu công cụ local ffprobe. Chuẩn bị gói offline trước khi chạy.','Video hỏng'])]
            metadata=dict(streams=[dict(codec_type='video',width=1080,height=1920,duration='8')],format=dict(duration='8'))
            with patch('template_studio.app.ensure_media'), \
                    patch('template_studio.app.detect',return_value=dict(nvenc=True,gpus=[],cpu='CPU thử')), \
                    patch('template_studio.production.probe',return_value=metadata):
                controller.prepareMedia()
            self.assertTrue(controller.mediaReady)
            self.assertEqual(p.rows[0]['status'],'Chờ xử lý')
            self.assertEqual(p.rows[0]['duration'],8)
            self.assertEqual(p.rows[0]['config'],config)
            self.assertEqual(p.rows[1]['detail'],'Video hỏng')
            saved=json.loads((home/'production.json').read_text(encoding='utf-8'))
            self.assertEqual(saved['rows'][0]['duration'],8)

    def test_import_checks_runtime_once_before_probing_and_does_not_mark_sources_bad(self):
        with tempfile.TemporaryDirectory() as folder:
            home=Path(folder).resolve()
            controller=self.controller(home)
            sources=[home/f'nguồn-{i}.mp4' for i in range(3)]
            for source in sources:
                source.write_bytes(b'nguon')
            with patch('template_studio.production.ensure_media',side_effect=RuntimeError('mạng lỗi')) as setup, \
                    patch('template_studio.production.probe') as read:
                controller.production.add_paths(sources)
            setup.assert_called_once()
            read.assert_not_called()
            self.assertEqual(controller.production.rows,[])
            self.assertFalse(controller.mediaReady)
            metadata=dict(streams=[dict(codec_type='video',width=1080,height=1920)],format=dict(duration='8'))
            events=[]
            with patch('template_studio.production.ensure_media',side_effect=lambda home,progress:events.append('setup')), \
                    patch('template_studio.production.probe',side_effect=lambda path:(events.append('probe') or metadata)):
                controller.production.add_paths(sources)
            self.assertEqual(events,['setup','probe','probe','probe'])
            self.assertTrue(controller.mediaReady)
            self.assertEqual(len(controller.production.rows),3)
