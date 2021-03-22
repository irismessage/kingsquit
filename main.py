#!/usr/bin/env python

import json
from pathlib import Path

import ffmpeg


# randomly use a subsequent audio clip, or select a new one
# randomly cut of audio clip even if the segment is ongoing
# polish for general release


videos_folder = Path('videos')
audio_clips_folder = videos_folder / 'audio-clips'
timestamps_file_path = audio_clips_folder / 'timestamps.json'


def verify_timestamp_pairs(timestamps: list[tuple[float, float]], maximum: float = 0.0) -> bool:
    last = 0.0
    for t in timestamps:
        if last >= t[0] or t[0] >= t[1]:
            return False
        if maximum and t[1] >= maximum:
            return False

    return True


def rip_audio_clips(video_path: Path, timestamps: list[tuple[float, float]]):
    specific_clips_folder = audio_clips_folder / video_path.name
    specific_clips_folder.mkdir(parents=True, exist_ok=True)

    for t in timestamps:
        duration = t[1] - t[0]
        clip_path = specific_clips_folder / f'{t[0]}-{duration}.mp3'
        stream = ffmpeg.input(str(video_path), ss=t[0])
        stream.output(str(clip_path))
        stream.run()


def add_audio_to_video(video_path: Path, audio_path: Path, timestamp: float, duration: float):
    pass


def main():
    video_name = input('Video name: ')
    video_path = videos_folder / video_name

    print('Checking for timestamps file')
    with open(timestamps_file_path) as timestamps_file:
        timestamps = json.load(timestamps_file)
        print('Loaded timestamps file')
    if not verify_timestamp_pairs(timestamps):
        print('Invalid timestamps')
        return False

    print('Ripping audio clips')
    rip_audio_clips(video_path, timestamps)


if __name__ == '__main__':
    main()
