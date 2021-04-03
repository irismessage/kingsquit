"""Build for pypi distribution.

Usage: python -m setup.py sdist bdist_wheel
Upload with twine
"""

import setuptools
import kingsquit


with open('README.md', 'r', encoding='utf-8') as readme_file:
    long_description = readme_file.read()

setuptools.setup(
    name='cmpc-timelapse',
    version=kingsquit.__version__,
    author='JMcB',
    author_email='joel.mcbride1@live.com',
    license='GPLv3',
    description='A dialogue randomiser for videos.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/JMcB17/auto_timelapse_script',
    packages=setuptools.find_packages(),
    entry_points={
        'console_scripts': [
            'kingsquit=kingsquit:main'
        ]
    },
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
    ],
    python_requires='>=3',
    install_requires=[
        'ffmpeg-python',
        'youtube-dl',
        'pysrt',
        'pycaption',
        'cchardet',
    ]
)
