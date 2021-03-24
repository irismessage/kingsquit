#!/usr/bin/env python

import json
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


def add_audio_to_video(video_path: Path, audio_path: Path, timestamp: float, duration: float):
    """Add the audio onto the video at the timestamp with ffmpeg."""
    temp_video_path = video_path.with_stem(video_path.stem + '-temp')

    video_head = ffmpeg.input(str(video_path), t=timestamp)
    video_tail = ffmpeg.input(str(video_path), ss=timestamp+duration)

    video_to_merge = ffmpeg.input(str(video_path), ss=timestamp, t=duration)
    audio_to_merge = ffmpeg.input(str(audio_path), t=duration)
    audio_merged = ffmpeg.filter([video_to_merge.audio, audio_to_merge], 'amerge')
    video_merged = ffmpeg.concat(video_to_merge, audio_merged, v=1, a=1)

    stream = ffmpeg.concat(
        video_head,
        video_merged,
        video_tail
    )
    # stream = ffmpeg.output(stream, str(temp_video_path), vcodec='copy')
    stream = ffmpeg.output(stream, str(temp_video_path))
    print(ffmpeg.get_args(stream))
    ffmpeg.run(stream)

    video_path.unlink()
    temp_video_path.rename(video_path)


def fill_empty_audio(video_path: Path, timestamps: list[tuple[float, float]]):
    # todo: remove audio from video
    # will need to make algorithm more advanced if adding overlapping audio support
    for i in range(len(timestamps) - 1):
        t1 = timestamps[i]
        t2 = timestamps[i+1]
        duration = t1[1] - t2[0]
        add_audio_to_video(video_path, video_path, t1[1], duration)


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
    # convert subtitles to label track so user can edit it?
    if not verify_timestamp_pairs(timestamps):
        print('Invalid timestamps')
        return False

    print('Ripping audio clips')
    rip_all_audio_clips(video_path, timestamps)


if __name__ == '__main__':
    # main()
    vid = Path(r'C:\Users\joelm\Documents\_Programming\_python\kingsquit\videos\Half-Life VR but the AI is Self-Aware (ACT 1 - PART 1)-vDUYLDtC5Qw.mp4')
    aud = Path(r'C:\Users\joelm\Documents\_Programming\_python\kingsquit\videos\audio-clips\Half-Life VR but the AI is Self-Aware (ACT 1 - PART 1)-vDUYLDtC5Qw.mp4\1.62d0.78.mp3')
    add_audio_to_video(vid, aud, 0.0, 1.0)
