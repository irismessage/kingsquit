#!/usr/bin/env python

import json
import random
from decimal import Decimal
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

# note: you must install ffmpeg executable
import ffmpeg


# randomly use a subsequent audio clip, or select a new one
# randomly cut of audio clip even if the segment is ongoing
# polish for general release
# make the same dialogue make the same sound - record mappings, add text back to timestamps file


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
        stream = ffmpeg.output(stream, str(clip_path), t=duration).global_args('-n')
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

    return specific_clips_folder


# new plan
# shuffle_clips
#   shuffle chunks of clips
#   re-mux clips to be the same duration for each timestamp again
# reform_video
#   add back original audio in between
#   concatenate all clips with concat demuxer
#   add to video
def generate_audio_track(video_path: Path, clips_folder: Path, timestamps: list[tuple[float, float]]):
    clips = list(clips_folder.iterdir())
    concats = []

    last = 0.0
    for t in timestamps:
        concats.append(ffmpeg.input(video_path, ss=last, to=t[0]).audio)

        t_duration = t[1] - t[0]
        cumulative_duration = 0.0
        while cumulative_duration < t_duration:
            random_clip = random.choice(clips)
            cn = random_clip.stem
            clip_duration = float(cn[cn.index('d')+1:])

            concat_duration = min(clip_duration, t_duration-cumulative_duration)
            cumulative_duration += concat_duration
            concats.append(ffmpeg.input(str(random_clip), t=concat_duration))
        last = t[1]

    out_file = video_path.with_suffix('.mp3')
    ffmpeg.concat(*concats).output(str(out_file), acodec='copy').run()
    return out_file


def main():
    # if starts with http or https, use ydl to download video and subtitles
    video_name = input('Video name: ')
    video_path = videos_folder / video_name
    if not video_path.is_file():
        print("Video doesn't exist")
        return False
    video_info = ffmpeg.probe(str(video_path))
    video_length_seconds = float(video_info['format']['duration'])

    print('Checking for timestamps file')
    # todo: change to just .json
    with open(video_path.with_suffix('.ko.json')) as timestamps_file:
        timestamps = json.load(timestamps_file)
        print('Loaded timestamps file')
    # look for subtitle file by name
    # look for subtitle file by extension
    # look for subtitle file with subtitle on pypi
    # convert subtitles to label track so user can edit it?
    if not verify_timestamp_pairs(timestamps, video_length_seconds):
        print('Invalid timestamps')
        return False

    print('Ripping audio clips')
    # clips_folder = rip_all_audio_clips(video_path, timestamps)

    print('Generating new audio track')
    # new_audio = generate_audio_track(video_path, clips_folder, timestamps)


if __name__ == '__main__':
    main()
