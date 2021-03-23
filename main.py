#!/usr/bin/env python

import json
from decimal import Decimal
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

import ffmpeg


# randomly use a subsequent audio clip, or select a new one
# randomly cut of audio clip even if the segment is ongoing
# polish for general release


videos_folder = Path('videos')
audio_clips_folder = videos_folder / 'audio-clips'


def verify_timestamp_pairs(timestamps: list[tuple[float, float]], maximum: float = 0.0) -> bool:
    last = 0.0
    for t in timestamps:
        if last >= t[0] or t[0] >= t[1]:
            return False
        if maximum and t[1] >= maximum:
            return False

    return True


# made this way to work with ThreadPoolExecutor
class ClipRipper:
    def __init__(self, video_path, clips_folder):
        self.video_path = video_path
        self.clips_folder = clips_folder

    def rip_audio_clip(self, t: tuple[float, float]):
        duration = Decimal(str(t[1])) - Decimal(str(t[0]))
        clip_path = self.clips_folder / f'{t[0]}d{duration}.mp3'
        stream = ffmpeg.input(str(self.video_path), ss=t[0])
        stream = ffmpeg.output(stream, str(clip_path), t=duration)
        ffmpeg.run(stream)


def rip_all_audio_clips(video_path: Path, timestamps: list[tuple[float, float]]):
    specific_clips_folder = audio_clips_folder / video_path.name
    specific_clips_folder.mkdir(parents=True, exist_ok=True)

    clip_ripper = ClipRipper(video_path, specific_clips_folder)
    # one thread
    # for t in timestamps:
    #     clip_ripper.rip_audio_clip(t)

    # multithread
    with ThreadPoolExecutor() as threads:
        threads.map(clip_ripper.rip_audio_clip, timestamps)


def add_audio_to_video(video_path: Path, audio_path: Path, timestamp: float, duration: float):
    # add the audio onto the video at the timestamp with ffmpeg
    pass


def fill_empty_audio(video_path: Path, timestamps: list[tuple[float, float]]):
    # remove audio from video
    # for any duration not covered by a timestamp, add the original audio back
    # will need to make algorithm more advanced if adding overlapping audio support
    pass


def main():
    # if starts with http or https, use ydl to download video and subtitles
    video_name = input('Video name: ')
    video_path = videos_folder / video_name
    if not video_path.is_file():
        print("Video doesn't exist")
        return False

    print('Checking for timestamps file')
    # todo: change to just .json
    with open(video_path.with_suffix('.ko.json')) as timestamps_file:
        timestamps = json.load(timestamps_file)
        print('Loaded timestamps file')
    # look for subtitle file by name
    # look for subtitle file by extension
    # look for subtitle file with subtitle on pypi
    if not verify_timestamp_pairs(timestamps):
        print('Invalid timestamps')
        return False

    print('Ripping audio clips')
    rip_all_audio_clips(video_path, timestamps)


if __name__ == '__main__':
    main()
