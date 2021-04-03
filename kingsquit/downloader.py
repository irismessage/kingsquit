"""Module for downloading videos with youtube_dl and processing their subtitles into a timestamps file."""

import json
from pathlib import Path

import youtube_dl as youtube_yl  # youtube yownloader
import pycaption
import pysrt


def find_subtitle_file(video_path: Path, sub_extension: str = '.ttml'):
    """Find the subtitle file corresponding to the video.

    Args:
        video_path -- path of the video to compare the name of
        sub_extension -- file extension to search for
    If found, rename the subtitle file to rename the language suffix, if applicable, then return its path.
    If not found, return None.
    """
    video_folder = video_path.parent

    for file in video_folder.iterdir():
        if file.suffix == sub_extension:
            if len(file.suffixes) > 1:
                lang_suffix = file.suffixes[-2]
                stem_without_lang = file.stem[:-len(lang_suffix)]
            else:
                stem_without_lang = file.stem

            if stem_without_lang == video_path.stem:
                file = file.replace(file.with_stem(stem_without_lang))
                return file

    return None


def srt_to_timestamps(srt_path: Path):
    """Convert a .srt subtitles file to a list of tuple timestamps, and save it to json."""
    srt_subtitles = pysrt.open(srt_path)

    timestamps = [(s.start.ordinal/1000, s.end.ordinal/1000) for s in srt_subtitles]
    with open(srt_path.with_suffix('.json'), 'w') as timestamps_file:
        json.dump(timestamps, timestamps_file)


def convert_subs(subtitle_path: Path):
    """Convert any valid subtitle file to srt subtitles for processing, using pycaption; then process them.

    Args:
        subtitle_path -- path of subtitles to convert
    Return True if successful, False otherwise.
    """
    with open(subtitle_path, encoding='utf-8') as sub_file:
        subtitles = sub_file.read()
    subtitle_reader_class = pycaption.detect_format(subtitles)
    if not subtitle_reader_class:
        return False

    subtitle_reader = subtitle_reader_class()
    srt_subtitles = pycaption.SRTWriter().write(subtitle_reader.read(subtitles))
    with open(subtitle_path.with_suffix('.srt'), 'w', encoding='utf-8') as sub_file:
        sub_file.write(srt_subtitles)

    srt_to_timestamps(subtitle_path.with_suffix('.srt'))
    return True


progress_hook = {}


def extract_progress_hook(hook: dict):
    """Take the progress hook dict from ytdl and make it a global variable.

    A bit of a hack but the best way I can think of to get it right now.
    """
    global progress_hook
    progress_hook = hook


def process_progress_hook(hook: dict):
    """Process video once it's done downloading.

    Progress hook for ytdl. Once the download status is 'finished', get the subtitle path from the video path,
    and run convert_subs on it.
    """
    # would be nice if youtube_dl gave you all the downloaded files including the progress hook
    # and if it let you get the return value of the progress hook
    if hook['status'] != 'finished':
        return None, None

    video_path = Path(hook['filename'])
    subtitle_path = find_subtitle_file(video_path)
    if not subtitle_path:
        print('Subtitle file not found! (speech-to-text auto subtitling coming soon?)')
        return video_path, None

    if convert_subs(subtitle_path):
        return video_path, subtitle_path
    else:
        print('Unable to convert subtitles! (speech-to-text auto subtitling coming soon?)')
        return video_path, None


def main(dest: str = ''):
    """Download the video to the destination folder, and process its subtitles.

    Args:
        dest -- destination folder.
                must be a string, not a path object, and use forward slashes, not backslashes.
                should also have no trailing slash.
                appended to the start of the youtube dl default out template.
    Returns nothing.
    """
    global progress_hook

    ydl_opts = {
        'outtmpl': f'{dest}/{youtube_yl.DEFAULT_OUTTMPL}',
        'format': 'mp4',
        'writesubtitles': True,
        'writeautomaticsub': True,
        'subtitlesformat': 'ttml',
        'progress_hooks': [extract_progress_hook],
        # 'nooverwrites': True,
        # 'ignoreerrors': True,
    }

    # todo: remove this debug code
    # todo: put the subtitle etc. files in the video folder so as to not clog the main folder
    # url = input('Youtube url: ')
    # subtitleslang = input('Subtitle language to download (type nothing for any): ')
    url = 'https://www.youtube.com/watch?v=vDUYLDtC5Qw'
    subtitleslang = 'ko'
    if subtitleslang:
        ydl_opts['subtitleslangs'] = [subtitleslang]
    try:
        with youtube_yl.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except youtube_yl.DownloadError as err:
        if err.exc_info[0] == youtube_yl.utils.ExtractorError:
            # todo: stop youtube dl from logging the error message
            choice = input('Invalid url, run a search? (y/N/youtube-dl search identifier)\n').casefold()
            if not choice or choice == 'n':
                return None, None
            elif choice == 'y':
                ydl_opts['default_search'] = 'auto_warning'
            else:
                ydl_opts['default_search'] = choice

            with youtube_yl.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
        else:
            raise

    print('Processing subtitles')
    while True:
        if not progress_hook:
            continue
        video_path, subtitle_path = process_progress_hook(progress_hook)
        if video_path:
            return video_path, subtitle_path
        progress_hook = None


if __name__ == '__main__':
    main()
