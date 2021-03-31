"""Module for downloading videos with youtube_dl and processing their subtitles into a timestamps file."""

import json
from pathlib import Path

import youtube_dl as youtube_yl  # youtube yownloader
import pycaption
import pysrt


def srt_to_timestamps(srt_path: Path):
    """Convert a .srt subtitles file to a list of tuple timestamps, and save it to json."""
    srt_subtitles = pysrt.open(srt_path)

    timestamps = [(s.start.ordinal/1000, s.end.ordinal/1000) for s in srt_subtitles]
    with open(srt_path.with_suffix('.json'), 'w') as timestamps_file:
        json.dump(timestamps, timestamps_file)


def convert_subs(subtitle_path: Path):
    """Convert any valid subtitle file to srt subtitles for processing, using pycaption; then process them."""
    # todo: handle invalid subtitles
    with open(subtitle_path, encoding='utf-8') as sub_file:
        subtitles = sub_file.read()
    subtitle_reader_class = pycaption.detect_format(subtitles)
    subtitle_reader = subtitle_reader_class()
    srt_subtitles = pycaption.SRTWriter().write(subtitle_reader.read(subtitles))
    with open(subtitle_path.with_suffix('.srt'), 'w', encoding='utf-8') as sub_file:
        sub_file.write(srt_subtitles)

    srt_to_timestamps(subtitle_path.with_suffix('.srt'))


def process(hook: dict):
    """Process video once it's done downloading.

    Progress hook for ytdl. Once the download status is 'finished', get the subtitle path from the video path,
    and run convert_subs on it.
    """
    if hook['status'] != 'finished':
        return

    video_path = Path(hook['filename'])
    # todo: change
    subtitle_path = video_path.with_suffix('.ko.ttml')
    convert_subs(subtitle_path)


def main(dest: str):
    """Download the video to the destination folder, and process its subtitles.

    Args:
        dest -- destination folder. Should be a string, not a path objects, and must use / instead of \
                appended to the start of the youtube dl default out template.
    Returns nothing.
    """
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
