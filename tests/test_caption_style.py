"""Kiểm tra cùng lịch chữ/emoji, tài nguyên công khai và nhập font riêng."""

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

from template_studio.caption_style import ASSETS, EmojiTrack, keyword_style
from template_studio.fonts import import_font, inspect_font, stage_font
from template_studio.gpu.timing import audio_window, decode_window
from template_studio.karaoke import caption_groups, parse_capcut_source_words, write_ass
from template_studio.presets import catalog, normalize


class CaptionStyleTests(unittest.TestCase):
    def test_1012_old_snapshots_gain_new_fields_without_overwriting_choices(self):
        old = next(p['config'] for p in catalog() if p['id']=='karaoke-1012')
        for key in ('audio_delay_ms','subtitle_keywords','subtitle_emoji'):
            old.pop(key)
        migrated = normalize(old)
        self.assertEqual(migrated['audio_delay_ms'],50)
        self.assertTrue(migrated['subtitle_keywords'])
        self.assertTrue(migrated['subtitle_emoji'])
        chosen = normalize(dict(old,audio_delay_ms=0,subtitle_keywords=False,subtitle_emoji=False))
        self.assertEqual(chosen['audio_delay_ms'],0)
        self.assertFalse(chosen['subtitle_emoji'])
        self.assertEqual(normalize({})['audio_delay_ms'],0)

    def test_emoji_assets_match_manifest(self):
        manifest = json.loads((ASSETS/'manifest.json').read_text(encoding='utf-8'))
        for record in manifest['files']:
            self.assertEqual(hashlib.sha256((ASSETS/record['file']).read_bytes()).hexdigest(), record['sha256'])
        self.assertIn('Creative Commons', (ASSETS/'LICENSE-GRAPHICS').read_text(encoding='utf-8'))

    def test_phrases_match_across_tokens_without_matching_fragments(self):
        colors, icon = keyword_style([dict(text='đồng'),dict(text='ý!')])
        self.assertEqual(set(colors), {0,1})
        self.assertEqual(icon, '1f44d')
        self.assertEqual(keyword_style([dict(text='ý')]), ({},None))
        self.assertEqual(keyword_style([dict(text='moneybags')]), ({},None))

    def test_emoji_obeys_group_interval_and_preview_context(self):
        words = [dict(text='money',start=2,end=2.5),dict(text='paid.',start=2.5,end=3)]
        cues = list(caption_groups(words, base=2.25, duration=1))
        track = EmojiTrack(cues, 1080,1440)
        blank = np.zeros((1440,1080,3),dtype=np.uint8)
        self.assertGreater(track.apply(blank.copy(),0).sum(),0)
        self.assertEqual(track.apply(blank.copy(),.75).sum(),0)
        self.assertEqual(track.apply(blank.copy(),-1).sum(),0)
        self.assertEqual(blank.sum(),0)

    def test_keywords_do_not_override_active_word_color(self):
        words = [dict(text='money',start=0,end=.5),dict(text='today.',start=.5,end=1)]
        with tempfile.TemporaryDirectory() as folder:
            text = write_ass(words,Path(folder)/'x.ass',1080,1440,keyword_colors=True,red='FF0000',
                font_name='ZY Trend',font_scale_x=100).read_text(encoding='utf-8-sig')
        self.assertIn(r'{\c&H0000FF&}MONEY',text)
        self.assertIn(r'{\c&H00FFFF&}MONEY',text)
        self.assertIn('Style: Karaoke,ZY Trend,',text)
        self.assertIn(',100,100,0,0,1,',text)

    def test_draft_maps_cut_and_speed_back_to_source(self):
        text = dict(id='txt',words=dict(text=['New York'],start_time=[100],end_time=[600]))
        child = dict(materials=dict(videos=[dict(id='v',path='C:/source.mp4')],texts=[text],
            text_templates=[dict(id='t',text_info_resources=[dict(text_material_id='txt')])]),tracks=[
            dict(type='video',segments=[dict(material_id='v',target_timerange=dict(start=0,duration=2_000_000),
                source_timerange=dict(start=10_000_000,duration=3_000_000))]),
            dict(type='text',segments=[dict(material_id='t',target_timerange=dict(start=1_000_000,duration=1_000_000))])])
        root = dict(materials=dict(drafts=[dict(id='c',draft=child)]),tracks=[dict(type='video',segments=[dict(extra_material_refs=['c'])])])
        words = parse_capcut_source_words(root)
        self.assertEqual(words[0]['text'],'New York')
        self.assertAlmostEqual(words[0]['start'],11.65)
        self.assertAlmostEqual(words[0]['end'],12.4)
        child['materials']['videos'].append(dict(id='other',path='C:/other.mp4'))
        child['tracks'][0]['segments'].append(dict(material_id='other',target_timerange=dict(start=3_000_000,duration=1_000_000),
            source_timerange=dict(start=0,duration=1_000_000)))
        with self.assertRaisesRegex(ValueError,'nguồn'):
            parse_capcut_source_words(root)

    def test_audio_delay_is_not_restarted_in_midpart_preview(self):
        seek, af = audio_window(10,1.02,2,50,10)
        self.assertEqual(seek,10)
        self.assertIn('adelay=50.000000',af)
        seek, af = audio_window(20,1.02,2,50,10)
        self.assertAlmostEqual(seek,19.949)
        self.assertNotIn('adelay',af)
        self.assertIn('apad,atrim=duration=2',af)
        seek, _ = audio_window(20,1.02,2,-50,10)
        self.assertAlmostEqual(seek,20.051)

    def test_decoder_keeps_absolute_phase(self):
        seek, filters = decode_window(dict(start_time='.2'),dict(start_time='0'),10.0123,1.0293,30,1920,1080)
        self.assertAlmostEqual(seek,9.2123)
        self.assertIn('PTS-(10.212300000000)/TB',filters)
        self.assertIn('start_time=0:round=up',filters)

    def test_font_import_is_private_and_validated(self):
        with tempfile.TemporaryDirectory() as folder:
            folder=Path(folder)
            source=folder/'font thử.ttf'
            source.write_bytes(b'font-gia-lap')
            with patch('template_studio.fonts.ImageFont.truetype') as read:
                read.return_value.getname.return_value=('Font thử','Regular')
                imported=import_font(source,folder/'data')
                self.assertEqual(imported['name'],'Font thử')
                self.assertEqual(Path(imported['path']).read_bytes(),source.read_bytes())
                self.assertEqual(stage_font(imported['path'],folder/'job'),'Font thử')
                self.assertTrue((folder/'job/fonts/caption.ttf').is_file())
            with self.assertRaisesRegex(ValueError,'Không đọc'):
                inspect_font(source)


if __name__ == '__main__':
    unittest.main()
