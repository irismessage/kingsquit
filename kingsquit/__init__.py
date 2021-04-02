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


# made this way to work with ThreadPoolExecutor
class ClipRipper:
    """Class for storing the video path and output path for ripping clips."""

    def __init__(self, video_path, clips_folder):
        self.video_path = video_path
        self.clips_folder = clips_folder

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
        duration = Decimal(str(t[1])) - Decimal(str(t[0]))
        clip_path = self.clips_folder / f'{t[0]}d{duration}.mp3'
        stream = ffmpeg.input(str(self.video_path), ss=t[0])
        # no need to streamcopy because it's fast anyway
        # also skip clips already ripped
        stream = ffmpeg.output(stream, str(clip_path), t=duration).global_args('-n')
        ffmpeg.run(stream)


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

    clip_ripper = ClipRipper(video_path, clips_folder)
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

    return rip_all_audio_clips(video_path, intermediate_timestamps, dest='intermediate-audio-clips')


def shuffle_clips(video_folder: Path, jump_chance: float = 0.3):
    """Shuffle the files in the folder in chunks.

    Args:
        video_folder  -- path to the base folder containing the audio-clips folder
        jump_chance -- chance that audio will jump to a new random clip instead of continuing to the next clip.
                       therefore, the size of each chunk on average should the number of clips / jump chance
    Returns a last of clips paths, shuffled.
    """
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

    concat_file_path = components_folder / 'concat.txt'
    concat_list = []
    for component in components:
        if not (component[1] or component[2]):
            out_path = components_folder / f'{component[1]}d{component[2] - component[1]}.mp3'
            stream = ffmpeg.input(str(component[0]), ss=component[1], to=component[2])
            stream = ffmpeg.output(stream, str(out_path))
            stream.run()

            concat_new_path = out_path
        else:
            concat_new_path = component[0]
        concat_new_str = str(concat_new_path.resolve()).replace('\\', '\\\\')
        concat_list.append(f"file '{concat_new_str}'")

    with open(concat_file_path, 'w') as concat_file:
        concat_file.writelines(concat_list)

    out_path = shuffled_clips_folder / f'{timestamp[0]}d{timestamp[1] - timestamp[0]}.mp3'
    stream = ffmpeg.input(str(concat_file_path), format='concat', safe=0)
    stream = ffmpeg.output(stream, str(out_path))
    stream.run()


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

    cursor_file = 0
    cursor_time = 0.0
    for t in timestamps:
        t_duration = t[1] - t[0]
        # cumulative
        cum_duration = 0.0
        reformed_clip_content = []
        while cum_duration < t_duration:
            clip_to_add = shuffled_clips[cursor_file]
            cursor_file += 1

            clip_duration = float(clip_to_add.stem[clip_to_add.stem.index('d') + 1:])

            if cursor_time != 0.0:
                clip_duration -= cursor_time
                cursor_time = 0.0
                clip_end = 0.0
            else:
                clip_end = clip_duration
            reformed_clip_content.append((clip_to_add, cursor_time, clip_end))
            cum_duration += clip_duration

        cursor_time = cum_duration - t_duration

        reform_one_clip(video_path, t, reformed_clip_content)

    return shuffled_clips_folder


def generate_new_video(video_path: Path):
    """Reform shuffled clips into a single audio track, and join it back to the video.

    Args:
        video_path -- path to the video, also used to get the video folder and clips folder
    Returns nothing.

    Ran after the clips have been ripped, shuffled, and reforms. Concatenates the clips with the concat demuxer,
    then takes that and the original video to make a new video file.
    """
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
    video_folder.mkdir()

    video_info = ffmpeg.probe(str(video_path))
    video_length_seconds = float(video_info['format']['duration'])

    print('Checking for timestamps file')
    with open(subtitle_path.with_suffix('.json')) as timestamps_file:
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
