"""Đối chiếu byte khung hình khi seek giữa frame 24 FPS và xuất 30 FPS."""

import subprocess
import tempfile
import unittest
from pathlib import Path

import numpy as np

from offline_studio.process import NO_WINDOW, binary, probe
from template_studio.gpu.timing import decode_window


class DecodeTimingTests(unittest.TestCase):
    def test_seek_matches_continuous_render_at_noninteger_rate(self):
        try:
            ffmpeg = binary('ffmpeg')
        except FileNotFoundError:
            self.skipTest('Chưa chuẩn bị FFmpeg cho kiểm thử tích hợp.')
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder)/'nguồn.nut'
            frames = np.zeros((24*8,32,32,3),np.uint8)
            frames[:,:,:,0] = np.arange(len(frames))[:,None,None]
            subprocess.run([ffmpeg,'-v','error','-f','rawvideo','-pix_fmt','rgb24','-s','32x32','-r','24',
                '-i','pipe:0','-c:v','ffv1',str(source)],input=frames.tobytes(),check=True,creationflags=NO_WINDOW)
            info = probe(source)
            video = next(s for s in info['streams'] if s['codec_type']=='video')
            rate, first, count = 1.02931464386368, 165, 45

            def decode(offset, count):
                seek, vf = decode_window(video,info['format'],offset,rate,30,32,32)
                raw = subprocess.check_output([ffmpeg,'-v','error','-copyts','-start_at_zero','-ss',str(seek),
                    '-i',str(source),'-vf',vf,'-frames:v',str(count),'-f','rawvideo','-pix_fmt','rgb24','pipe:1'],
                    creationflags=NO_WINDOW)
                return np.frombuffer(raw,np.uint8).reshape(-1,32,32,3)

            continuous = decode(0,first+count)
            window = decode(first/30*rate,count)
            np.testing.assert_array_equal(window,continuous[first:first+count])
