import json
from pathlib import Path

import youtube_dl as youtube_yl  # youtube yownloader
import pycaption
import pysrt


def srt_to_timestamps(srt_path: Path):
    srt_subtitles = pysrt.open(srt_path)

    secs = lambda t: t.ordinal/1000
    timestamps = [(secs(s.start), secs(s.end)) for s in srt_subtitles]
    with open(srt_path.with_suffix('.json'), 'w') as timestamps_file:
        json.dump(timestamps, timestamps_file)


def convert_subs(subtitle_path: Path):
    with open(subtitle_path, encoding='utf-8') as sub_file:
        subtitles = sub_file.read()
    subtitle_reader_class = pycaption.detect_format(subtitles)
    subtitle_reader = subtitle_reader_class()
    srt_subtitles = pycaption.SRTWriter().write(subtitle_reader.read(subtitles))
    with open(subtitle_path.with_suffix('.srt'), 'w', encoding='utf-8') as sub_file:
        sub_file.write(srt_subtitles)

    srt_to_timestamps(subtitle_path.with_suffix('.srt'))


def process(hook: dict):
    if hook['status'] != 'finished':
        return

    video_path = Path(hook['filename'])
    subtitle_path = video_path.with_suffix('.ko.ttml')
    convert_subs(subtitle_path)


ydl_args = {
    'format': 'mp4',
    'writesubtitles': True,
    'subtitlesformat': 'ttml',
    'subtitleslangs': ['ko'],
    'progress_hooks': [process],
}


# with youtube_yl.YoutubeDL(ydl_args) as ydl:
#     ydl.download(['https://youtu.be/vDUYLDtC5Qw'])
convert_subs(Path('Half-Life VR but the AI is Self-Aware (ACT 1 - PART 1)-vDUYLDtC5Qw.ko.ttml'))
