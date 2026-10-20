"""Kiểm thử đọc phụ đề và tạo karaoke offline."""
import json
import tempfile
import unittest
from pathlib import Path

from template_studio.karaoke import (
    _ass_time, _parse_timed_json, find_caption_file,
    load_words, parse_capcut_draft, parse_srt, write_ass,
)


class KaraokeTests(unittest.TestCase):
    def test_srt_estimated_alignment(self):
        words = parse_srt("1\n00:00:01,000 --> 00:00:02,000\nHello wonderful world!\n")
        self.assertEqual([w['text'] for w in words], ['Hello','wonderful','world!'])
        self.assertAlmostEqual(words[0]['start'], 1.0)
        self.assertAlmostEqual(words[-1]['end'], 2.0)

    def test_real_capcut_shape_referenced_child_and_words(self):
        caption_text = {'id': 'txt1', 'recognize_text': 'hello world',
                        'words': {'text': ['hello', ' ', 'world'],
                                  'start_time': [0, 300, 400],
                                  'end_time': [300, 300, 900]}}
        child = {'materials': {'texts':[caption_text], 'text_templates': [
            {'id': 'templ1', 'text_info_resources':[{'text_material_id':'txt1'}]}]},
                 'tracks': [{'type': 'text','segments': [
                     {'material_id':'templ1','target_timerange':{'start': 1000000, 'duration': 1000000}}]}]}
        root = {'materials':{'drafts':[{'id':'child1','draft':child}]},
                'tracks':[{'type':'video','segments':[
                    {'target_timerange':{'start':3000000,'duration':3000000},
                     'source_timerange':{'start':0,'duration':3000000},
                     'extra_material_refs':['child1']}]}]}
        result = parse_capcut_draft(root)
        self.assertEqual([w['text'] for w in result], ['hello','world'])
        self.assertAlmostEqual(result[0]['start'], 4.0)
        self.assertAlmostEqual(result[-1]['end'], 4.9)

    def test_ass_red_active_word_and_video_offset(self):
        words=[{'text':'AND','start':3.,'end':3.4}, {'text':'LADIES','start':3.4,'end':4.}]
        with tempfile.TemporaryDirectory() as d:
            p=write_ass(words,Path(d)/'karaoke.ass',1080,1440,
                        source_offset=2,playback_rate=1,angle=-11,red='FF374A')
            content=p.read_text(encoding='utf-8-sig')
            self.assertIn(r'\frz11.00',content)
            self.assertIn('Dialogue: 0,0:00:01.00,0:00:01.40,',content)
            self.assertIn(r'\c&H4A37FF&',content)
            self.assertIn('LADIES',content)

    def test_reject_invalid_color_and_json(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError,'RRGGBB'):
                write_ass([{'text':'a','start':0,'end':1}],Path(d)/'x.ass',1080,1440,red='x')
        with self.assertRaises(ValueError):
            _parse_timed_json([{'text':'bad','start':3,'end':1}])

    def test_sidecar_priority_and_load(self):
        with tempfile.TemporaryDirectory() as d:
            clip=Path(d)/'sample.mp4';clip.touch()
            (Path(d)/'sample.srt').write_text('1\n00:00:00,000 --> 00:00:01,000\nhello world\n')
            self.assertEqual(find_caption_file(clip).suffix,'.srt')
            (Path(d)/'sample.words.json').write_text(json.dumps([{'text':'A','start':0,'end':1}]))
            self.assertEqual(find_caption_file(clip).name,'sample.words.json')
            self.assertEqual(load_words(find_caption_file(clip))[0]['text'],'A')

    def test_ass_time(self):
        self.assertEqual(_ass_time(3661.23), '1:01:01.23')

    def test_title_uses_actual_duration_and_words_are_clipped(self):
        with tempfile.TemporaryDirectory() as folder:
            path = write_ass([dict(text="CHÀO", start=0, end=1), dict(text="BẠN", start=4, end=5)],
                             Path(folder)/"x.ass", 1080, 1440, title="TIÊU ĐỀ", part_label="PART 2", duration=3)
            text = path.read_text(encoding="utf-8-sig")
            self.assertIn("Dialogue: 0,0:00:00.00,0:00:03.00,Header", text)
            self.assertIn("Dialogue: 0,0:00:00.00,0:00:03.00,Part", text)
            self.assertNotIn("0:00:04.00", text)

    def test_rate_offset_and_word_across_cut_are_mapped_once(self):
        with tempfile.TemporaryDirectory() as folder:
            path = write_ass([dict(text="QUA", start=3.0, end=4.2)], Path(folder)/"x.ass", 1080, 1440,
                             source_offset=1, timeline_offset=2, playback_rate=1.02, duration=2)
            text = path.read_text(encoding="utf-8-sig")
            self.assertIn("Dialogue: 0,0:00:00.00,0:00:01.14,Karaoke", text)

    def test_subtitle_content_cannot_inject_ass_tags(self):
        with tempfile.TemporaryDirectory() as folder:
            path = write_ass([dict(text=r"{\pos(0,0)}TEST", start=0, end=1)], Path(folder)/"x.ass", 1080, 1440)
            self.assertNotIn(r"{\pos(0,0)}", path.read_text(encoding="utf-8-sig"))

    def test_nested_draft_rejects_unsupported_speed(self):
        child = dict(materials={}, tracks=[])
        data = dict(materials=dict(drafts=[dict(id="child",draft=child)]), tracks=[dict(type="video",segments=[dict(
            target_timerange=dict(start=0,duration=1_000_000), source_timerange=dict(start=0,duration=2_000_000),
            extra_material_refs=["child"], speed=2,
        )])])
        with self.assertRaisesRegex(ValueError, "tốc độ"):
            parse_capcut_draft(data)

    def test_json_requires_valid_text_and_finite_timestamps(self):
        for value in ([dict(text="a")], [dict(text=None,start=0,end=1)], [dict(text="a",start=0,end=float("inf"))]):
            with self.subTest(value=value), self.assertRaises(ValueError):
                _parse_timed_json(value)

    def test_title_wraps_and_matches_reference_positions(self):
        with tempfile.TemporaryDirectory() as folder:
            path = write_ass([], Path(folder)/"x.ass", 1080, 1440, duration=3,
                             title="MELO CALLS OUT PABLO TORRE OVER LEBRON HELICOPTER INVESTIGATION", part_label="PART 2")
            text = path.read_text(encoding="utf-8-sig")
            self.assertIn(r"\pos(540,203)", text)
            self.assertIn(r"\pos(540,1231)", text)
            self.assertIn(r"OVER\NLEBRON", text)
            self.assertIn(r"\frz10.88", text)

    def test_phrases_do_not_show_the_next_sentence_early(self):
        words = [dict(text=t,start=i*.3,end=(i+1)*.3) for i,t in enumerate(
            ["AND","LADIES","AND","GENTLEMEN,","DO","NOT","FORGET","OCTOBER","30TH,"])]
        with tempfile.TemporaryDirectory() as folder:
            path = write_ass(words,Path(folder)/"x.ass",1080,1440)
            first = next(line for line in path.read_text(encoding="utf-8-sig").splitlines() if line.startswith("Dialogue:"))
            self.assertNotIn("FORGET",first)
            self.assertIn(r"\fs92",first)
            self.assertIn(r"\N{\fs66}",first)

    def test_part_context_excludes_words_from_previous_and_next_parts(self):
        words=[dict(text=t,start=i,end=i+1) for i,t in enumerate(["PREVIOUS","CURRENT","NEXT"])]
        with tempfile.TemporaryDirectory() as folder:
            path=write_ass(words,Path(folder)/"x.ass",1080,1440,source_offset=1,
                           context_start=1,context_end=2,duration=1)
            text=path.read_text(encoding="utf-8-sig")
            self.assertIn("CURRENT",text)
            self.assertNotIn("PREVIOUS",text)
            self.assertNotIn("NEXT",text)

    def test_part_colors_are_independent_from_header_and_old_calls_keep_shared_colors(self):
        with tempfile.TemporaryDirectory() as folder:
            path=write_ass([],Path(folder)/'colors.ass',1080,1440,duration=1,title='TIÊU ĐỀ',part_label='PART 1',
                title_color='FFFF00',title_background='000000',part_color='FF0000',part_background='00FFFF')
            lines=path.read_text(encoding='utf-8-sig').splitlines()
            header=next(line for line in lines if line.startswith('Style: Header,'))
            part=next(line for line in lines if line.startswith('Style: Part,'))
            self.assertIn('&H0000FFFF,&H0000FFFF,&H00000000,&H00000000',header)
            self.assertIn('&H000000FF,&H000000FF,&H00FFFF00,&H00FFFF00',part)
            path=write_ass([],Path(folder)/'old.ass',1080,1440,duration=1,title_color='123456',title_background='ABCDEF')
            lines=path.read_text(encoding='utf-8-sig').splitlines()
            header=next(line for line in lines if line.startswith('Style: Header,')).split(',')[3:7]
            part=next(line for line in lines if line.startswith('Style: Part,')).split(',')[3:7]
            self.assertEqual(header,part)

    def test_custom_colors_reach_styles_and_restore_base_after_highlight(self):
        with tempfile.TemporaryDirectory() as folder:
            path=write_ass([dict(text="XIN",start=0,end=.5),dict(text="CHÀO",start=.5,end=1)],
                Path(folder)/"x.ass",1080,1440,color="00FFCC",red="3366FF",outline_color="112233",
                title_color="AABBCC",title_background="102040",title="TIÊU ĐỀ",part_label="PART 5")
            text=path.read_text(encoding="utf-8-sig")
            self.assertIn("&H00CCFF00,&H00CCFF00,&H00332211",text)
            self.assertIn("&H00CCBBAA,&H00CCBBAA,&H00402010,&H00402010",text)
            self.assertIn(r"{\c&HFF6633&}XIN{\c&HCCFF00&}",text)
            self.assertNotIn(r"{\c&HFFFFFF&}",text)
            for invalid in (None,"#FFFFFF","FFFFFF00",r"\N0000"):
                with self.subTest(color=invalid),self.assertRaises(ValueError):
                    write_ass([],Path(folder)/"bad.ass",1080,1440,color=invalid)


if __name__=='__main__':
    unittest.main()
