#!/usr/bin/env python

import json
import random
from decimal import Decimal
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

# note: you must install ffmpeg executable
import ffmpeg


# setup.py
# pyinstaller
# randomly use a subsequent audio clip, or select a new one
# randomly cut of audio clip even if the segment is ongoing
# polish for general release
# make the same dialogue make the same sound - record mappings, add text back to timestamps file
# gold coin
__version__ = '0.1.0'


t_type = tuple[float, float]
tl_type = list[t_type]
videos_folder = Path('videos')


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


def rip_all_audio_clips(video_path: Path, timestamps: list[tuple[float, float]], dest='audio-clips'):
    clips_folder = video_path.with_suffix('') / dest
    clips_folder.mkdir(parents=True, exist_ok=True)

    clip_ripper = ClipRipper(video_path, clips_folder)
    # one thread
    # for t in timestamps:
    #     clip_ripper.rip_audio_clip(t)

    # multithread
    with ThreadPoolExecutor() as threads:
        threads.map(clip_ripper.rip_audio_clip, timestamps)

    return clips_folder


def rip_intermediate_audio_clips(video_path: Path, timestamps: tl_type, video_duration: float):
    intermediate_timestamps = []
    if timestamps[0][0] != 0.0:
        intermediate_timestamps.append((0.0, timestamps[0][0]))
    intermediate_timestamps += [(timestamps[i][1], timestamps[i+1][0]) for i in range(len(timestamps)-1)]
    if timestamps[-1][1] <= video_duration:
        intermediate_timestamps.append((timestamps[-1][1], video_duration))

    return rip_all_audio_clips(video_path, intermediate_timestamps, dest='intermediate-audio-clips')


def shuffle_clips(video_folder: Path, jump_chance: float = 0.3):
    clips_folder = video_folder / 'audio-clips'
    clips = list(clips_folder.iterdir())
    clips.sort()

    clips_shuffled = []
    while clips:
        index = random.randint(0, len(clips))
        while jump_chance < random.random():
            try:
                clips_shuffled.append(clips.pop(index))
                index += 1
            except IndexError:
                break

    return clips_shuffled


def reform_shuffled_clips(video_path: Path, timestamps: tl_type, shuffled_clips: list[Path]):
    pass


def generate_new_video(video_path: Path):
    video_folder = videos_folder.with_suffix('')
    shuffled_clips_folder = video_folder / 'audio-shuffled'
    shuffled_clips = list(shuffled_clips_folder.iterdir())
    shuffled_clips.sort()

    # concatenate shuffled audio back into a single audio track
    concat_folder = video_folder / 'audio-concat'
    concat_folder.mkdir(exist_ok=True)
    concat_file = concat_folder / 'concat.txt'
    concat_output = concat_folder / 'audio.mp3'

    with open(concat_file, 'w') as concat_file:
        concat_file.writelines([f"file '{f}'" for f in shuffled_clips])
    stream = ffmpeg.input(str(concat_file), format='concat', safe=0)
    stream = ffmpeg.output(stream, str(concat_output), **{'c:v': 'copy', 'c:a': 'copy'})
    ffmpeg.run(stream)

    # combine new audio with video to create the new video
    final_result_path = video_path.with_stem('(SHUFFLED)' + video_path.stem)

    video_stream = ffmpeg.input(str(video_path)).video
    audio_stream = ffmpeg.input(str(concat_output))
    stream = ffmpeg.output(video_stream, audio_stream, str(final_result_path))
    ffmpeg.run(stream)


# doesn't work, keeping for now for referencing maybe writing reform_shuffled_clips
def generate_audio_track(video_path: Path, clips_folder: Path, timestamps: tl_type):
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
    video_folder = video_path.with_suffix('')
    video_folder.mkdir()

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
    rip_all_audio_clips(video_path, timestamps)
    rip_intermediate_audio_clips(video_path, timestamps, video_length_seconds)
    print('Shuffling audio')
    shuffled_clips = shuffle_clips(video_path)
    reform_shuffled_clips(video_path, timestamps, shuffled_clips)
    print('Creating new video with shuffled audio!')
    generate_new_video(video_path)
    print('Done.')
    input('Press enter to exit')


if __name__ == '__main__':
    main()