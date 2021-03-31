import json
from pathlib import Path

import youtube_dl as youtube_yl  # youtube yownloader
import pycaption
import pysrt


def srt_to_timestamps(srt_path: Path):
    srt_subtitles = pysrt.open(srt_path)

    timestamps = [(s.start.ordinal/1000, s.end.ordinal/1000) for s in srt_subtitles]
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


def main(dest: str):
    ydl_args = {
        'outtmpl': f'{dest}/{youtube_yl.DEFAULT_OUTTMPL}',
        'format': 'mp4',
        'writesubtitles': True,
        'writeautomaticsub': True,
        'subtitlesformat': 'ttml',
        'progress_hooks': [process],
    }

    url = input('Youtube url: ')
    subtitleslangs = input('Subtitle language to download (type nothing for any): ')
    if subtitleslangs:
        ydl_args['subtitleslangs'] = [subtitleslangs]
    with youtube_yl.YoutubeDL(ydl_args) as ydl:
        ydl.download([url])
