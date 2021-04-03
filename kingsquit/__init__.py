"""Main body of the code for shuffling dialogue in videos, including the main function."""

import json
import random
from decimal import Decimal
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

# note: you must install ffmpeg executable
import ffmpeg
import downloader


# polish for general release
# make the same dialogue make the same sound - record mappings, add text back to timestamps file
# gold coin
# todo: add argparse
# todo: give all relevant folders as arguments instead of getting them from video path - better code
# todo: update docstrings and write new ones
__version__ = '0.1.0'


t_type = tuple[float, float]
tl_type = list[t_type]
videos_folder = Path('kingsquit-videos')


def verify_timestamp_pairs(timestamps: tl_type, maximum: float) -> bool:
    """Verify that each timestamp is valid, and there are no overlapping timestamps.

    Args:
        timestamps -- a list of tuples containing a start time and an end time as floats
        maximum -- the maximum size of any timestamp (the duration of the video)
    Returns True if the timestamps list is valid, False otherwise.
    """
    last = 0.0
    for t in timestamps:
        if last >= t[0] or t[0] >= t[1]:
            return False
        if maximum and t[1] >= maximum:
            return False

    return True


class ProgressBarRunner:
    def __init__(self, total):
        self.total = total

        self.progress_bar_interval = self.total // 10
        self.last_log = 0
        self.done = 0

    def progress(self):
        self.done += 1

        if self.done == 1:
            print(f'Doing {self.total} clips\n█', end='')
        if self.done == self.total:
            print(f'\nDid {self.done} clips!')
        elif self.done >= self.last_log + self.progress_bar_interval:
            print('█', end='')
            self.last_log += self.progress_bar_interval


# made this way to work with ThreadPoolExecutor
class ClipRipper(ProgressBarRunner):
    """Class for storing the video path and output path for ripping clips."""

    def __init__(self, video_path, clips_folder, total):
        self.video_path = video_path
        self.clips_folder = clips_folder

        super().__init__(total)

    def rip_audio_clip(self, t: t_type):
        """Take a snippet of audio from a video and save it to its own mp3 file.

        Args:
            t -- a tuple of the time to start the clip and the time to end the clip, in seconds
        Returns nothing.

        Gets the video path and output folder path from the object. This is so it can easily be used in a
        ThreadPoolExecutor.
        Saves the mp3 file with the name {start time}d{duration}.mp3 where both start time and duration are in seconds,
        like the timestamp argument.
        """
        self.progress()

        t_duration = Decimal(str(t[1])) - Decimal(str(t[0]))
        clip_path = self.clips_folder / f'{t[0]}d{t_duration}.mp3'
        stream = ffmpeg.input(str(self.video_path), ss=t[0])
        # skip clips already ripped with -n
        stream = ffmpeg.output(stream, str(clip_path), t=t_duration).global_args('-n')
        ffmpeg.run(stream, quiet=True)


def rip_all_audio_clips(video_path: Path, timestamps: tl_type, dest='audio-clips') -> Path:
    """Rip an audio clip from the video for each timestamp.

    Args:
        video_path -- path to the video to rip clips from
        timestamps -- list of tuple start/end timestamps
        dest -- name of the destination folder
    Returns the path of the destination folder.
    """
    clips_folder = video_path.with_suffix('') / dest
    clips_folder.mkdir(parents=True, exist_ok=True)

    clip_ripper = ClipRipper(video_path, clips_folder, len(timestamps))
    # one thread
    # for t in timestamps:
    #     clip_ripper.rip_audio_clip(t)

    # multithread
    with ThreadPoolExecutor() as threads:
        threads.map(clip_ripper.rip_audio_clip, timestamps)

    return clips_folder


def rip_intermediate_audio_clips(video_path: Path, timestamps: tl_type, video_duration: float):
    """Calculate timestamps where there are is no dialogue and rip them.

    Args:
        video_path -- path to the video to rip clips from
        timestamps -- timestamps of dialogue, used to calculate where there is no dialogue
        video_duration -- length of the video in seconds, used to calculate the final timestamp
    Returns the path of the destination folder.

    Uses rip_all_audio_clips to rip the clips after calculating their timestamps.
    """
    intermediate_timestamps = []
    if timestamps[0][0] != 0.0:
        intermediate_timestamps.append((0.0, timestamps[0][0]))
    intermediate_timestamps += [(timestamps[i][1], timestamps[i+1][0]) for i in range(len(timestamps)-1)]
    if timestamps[-1][1] <= video_duration:
        intermediate_timestamps.append((timestamps[-1][1], video_duration))

    return rip_all_audio_clips(video_path, intermediate_timestamps, dest='audio-clips-intermediate')


def shuffle_clips(video_path: Path, jump_chance: float = 0.3):
    """Shuffle the files in the folder in chunks.

    Args:
        video_folder  -- path to the video, to find the audio-clips folder
        jump_chance -- chance that audio will jump to a new random clip instead of continuing to the next clip.
                       therefore, the size of each chunk on average should the number of clips / jump chance
    Returns a last of clips paths, shuffled.
    """
    video_folder = video_path.with_suffix('')
    clips_folder = video_folder / 'audio-clips'
    clips = list(clips_folder.iterdir())
    clips.sort()

    clips_shuffled = []
    # todo: more efficient implementation by just getting random indices then splitting at them?
    while clips:
        index = random.randint(0, len(clips))
        while jump_chance < random.random():
            try:
                clips_shuffled.append(clips.pop(index))
                index += 1
            except IndexError:
                break

    return clips_shuffled


def reform_one_clip(video_path: Path, timestamp: t_type, components: list[tuple[Path, float, float]]):
    """Take snippets from a few clips and combine them into one.

    Args:
        video_path -- path to the video to get the folder paths from
        timestamp -- timestamp of the clip we're making, used to pick the destination file name
        components -- a list of tuples, each containing clip path, start time, and end time
    Returns nothing.
    """
    video_folder = video_path.with_suffix('')
    components_folder = video_folder / 'audio-components'
    shuffled_clips_folder = video_folder / 'audio-shuffled'
    components_folder.mkdir(exist_ok=True)
    shuffled_clips_folder.mkdir(exist_ok=True)

    concat_file_path = components_folder / 'concat.txt'
    concat_list = []
    for component in components:
        if component[1] or component[2]:
            component_duration = Decimal(str(component[2])) - Decimal(str(component[1]))
            out_name = f'{component[1]}d{component_duration}.mp3'
            out_path = components_folder / out_name
            stream = ffmpeg.input(str(component[0]), ss=component[1])
            # todo: now that it works with to= in the output instead of input, try streamcopy again
            # stream = ffmpeg.output(stream, str(out_path), to=component[2], **{'c:a': 'copy'})
            stream = ffmpeg.output(stream, str(out_path), to=component[2])
            ffmpeg.run(stream, quiet=True, overwrite_output=True)

            concat_new_path = out_path
        else:
            concat_new_path = component[0]
        concat_new_str = str(concat_new_path.resolve()).replace('\\', '\\\\')
        concat_list.append(f"file '{concat_new_str}'\n")

    with open(concat_file_path, 'w') as concat_file:
        concat_file.writelines(concat_list)

    timestamp_duration = Decimal(str(timestamp[1])) - Decimal(str(timestamp[0]))
    out_path = shuffled_clips_folder / f'{timestamp[0]}d{timestamp_duration}.mp3'
    stream = ffmpeg.input(str(concat_file_path), format='concat', safe=0)
    stream = ffmpeg.output(stream, str(out_path), **{'c:a': 'copy'})
    ffmpeg.run(stream, quiet=True, overwrite_output=True)


# todo: add multithreading?
def reform_shuffled_clips(video_path: Path, timestamps: tl_type, shuffled_clips: list[Path]) -> Path:
    """Cut and join shuffled clips to match the timestamps again.

    Args:
        video_path -- path to the video, used to get the video folder and clips folder
        timestamps -- list of tuple timestamps to make the clips conform to
        shuffled_clips -- ordered list of clips paths
    Returns the path to the folder of shuffled and reformed clips.
    """
    video_folder = video_path.with_suffix('')
    shuffled_clips_folder = video_folder / 'audio-shuffled'

    progress_bar = ProgressBarRunner(len(timestamps))

    cursor_file_index = 0
    cursor_time = Decimal('0.0')
    for t in timestamps:
        t_duration = Decimal(str(t[1])) - Decimal(str(t[0]))
        time_to_fill = t_duration
        reformed_clip_content = []
        while time_to_fill > 0:
            clip_to_add = shuffled_clips[cursor_file_index]
            clip_duration = Decimal(clip_to_add.stem[clip_to_add.stem.index('d') + 1:])

            clip_start = cursor_time
            clip_duration_from_cursor = clip_duration - clip_start
            if clip_duration_from_cursor > time_to_fill:
                clip_end = clip_start + time_to_fill
                cursor_time = clip_end
            else:
                cursor_time = Decimal('0.0')
                cursor_file_index += 1
                if not clip_start:
                    clip_end = 0.0
                else:
                    clip_end = clip_duration

            reformed_clip_content.append((clip_to_add, clip_start, clip_end))
            time_to_fill -= clip_duration

        reform_one_clip(video_path, t, reformed_clip_content)
        progress_bar.progress()

    return shuffled_clips_folder


def generate_new_video(video_path: Path):
    """Reform shuffled clips into a single audio track, and join it back to the video.

    Args:
        video_path -- path to the video, also used to get the video folder and clips folder
    Returns nothing.

    Ran after the clips have been ripped, shuffled, and reforms. Concatenates the clips with the concat demuxer,
    then takes that and the original video to make a new video file.
    """
    video_folder = video_path.with_suffix('')
    shuffled_clips_folder = video_folder / 'audio-shuffled'
    intermediate_clips_folder = video_folder / 'audio-clips-intermediate'
    shuffled_clips = list(shuffled_clips_folder.iterdir()) + list(intermediate_clips_folder.iterdir())
    shuffled_clips.sort(key=lambda p: p.name)

    # concatenate shuffled audio back into a single audio track
    concat_folder = video_folder / 'audio-concat'
    concat_folder.mkdir(exist_ok=True)
    concat_file = concat_folder / 'concat.txt'
    concat_output = concat_folder / 'audio.mp3'

    with open(concat_file, 'w') as concat_file:
        concat_file.writelines([f"file '{f}'\n" for f in shuffled_clips])
    stream = ffmpeg.input(str(concat_file), format='concat', safe=0)
    stream = ffmpeg.output(stream, str(concat_output), **{'c:a': 'copy'})
    ffmpeg.run(stream)

    # combine new audio with video to create the new video
    final_result_path = video_path.with_stem('(SHUFFLED) ' + video_path.stem)

    video_stream = ffmpeg.input(str(video_path)).video
    audio_stream = ffmpeg.input(str(concat_output))
    stream = ffmpeg.output(video_stream, audio_stream, str(final_result_path), **{'c:v': 'copy', 'c:a': 'copy'})
    ffmpeg.run(stream)


def main():
    """Run the program."""
    # if starts with http or https, use ydl to download video and subtitles
    # video_name = input('Video name: ')
    # video_path = videos_folder / video_name
    video_path, subtitle_path = downloader.main(str(videos_folder))
    if not subtitle_path:
        return False

    if not video_path.is_file():
        print("Video doesn't exist")
        return False
    video_folder = video_path.with_suffix('')
    video_folder.mkdir(exist_ok=True)

    video_info = ffmpeg.probe(str(video_path))
    video_length_seconds = float(video_info['format']['duration'])

    print('Checking for timestamps file')
    try:
        with open(subtitle_path.with_suffix('.json')) as timestamps_file:
            timestamps = json.load(timestamps_file)
            print('Loaded timestamps file')
    except FileNotFoundError:
        print('Timestamps file not found!')
        return False
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
