# kingsquit
A dialogue randomiser for videos. Just put in a youtube url - video and subtitles used to determine dialogue regions will be downloaded with youtube-dl.    
Support for local files, subtitle tracks, and audacity label tracks coming soon.

## installation
### I don't have Python
Just download the .exe executable from the [latest release](https://github.com/JMcB17/kingsquit/releases/latest) on github. I bundled it with pyinstaller to make the program easy to get.

### I have Python
`python -m pip install kingsquit`
This project is on PyPi.

Alternately, download this repository (e.g. `git clone https://github.com/JMcB17/kingsquit/`) and install from disk with pip, or install the requirements with pip then run from the downloaded folder.

## usage
Just run the executable file.    
If you installed with pip or git, just run `kingsquit` or `python -m kingsquit` in your console.

Then all you need to do is type or paste a youtube url. After that the program will download and shuffle the video in the `kingsquit-videos` folder.    
Finally, once the program is done downloading and processing, you can watch/upload the resulting video! Or run again on the same video, for a different random result.

The program is designed so you can resume from where you were, if you stop after/while downloading. This makes it easy to generate a new randomised video, you just have to re-run the program, not re-download the video. Existing randomised will not be overwritten, it will just make a new one.

## coming soon, hopefully
- [ ] Edit the marked areas to randomise using an audacity label track
- [ ] Run on existing local files as well as urls
- [ ] Try to automatically download subtitles
- [ ] If automatically downloading subtitles failed, generate them with speech-to-text

## donate
~~buY mE a COFfeE~~    
To donate please DM me on discord JMcB#7918, and we can arrange for you to trade me coins on old school runescape.
