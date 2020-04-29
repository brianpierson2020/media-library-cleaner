# Media Library Cleaner
A simple and blazing fast Python command-line tool for checking and cleaning media libraries. Specifically to test for subtitle inconsistencies, identifying possible duplicate folders and files in multiple ways or finding garbage files. It can also detect the actual language in a subtitle file and compare it with the claimed language (ISO 639-(1/2)) in the filename to find files that are wrongly named.

## Requirements
- Python 3.x

## Installation
```bash
pip install -r requirements.txt
```

## Usage

Test it on the included test folder `./test` or on a real media folder.

```
usage: cleaner.py [-h] [-s SCANFOLDER] [-v] [-a] [-fe] [-fn] [-iy] [-is]
                  [-si SUBTITLESISO639] [-sn] [-sl] [-gc] [-ls] [-lm] [-lf]
                  [-mr]

Media Library Cleaner v.0.9 beta

optional arguments:
  -h, --help            show this help message and exit
  -s SCANFOLDER, --scanfolder SCANFOLDER
                        specify the filepath for scanning
  -v, --version         get current version of Media Library Cleaner
  -a, --all             use all options (helpful for code testing)
  -fe, --foldernameexact
                        find folders with exact same foldername
  -fn, --foldernamesoundex
                        find similar foldernames with soundex
  -iy, --ignoreyearfolders
                        ignores folders with year-only names
  -is, --ignoreseasonfolders
                        ignores folders with season names
  -si SUBTITLESISO639, --subtitlesiso639 SUBTITLESISO639
                        find subtitles that do not comply with ISO 639
  -sn, --subtitlenaming
                        find subtitles that do not match the media name
  -sl, --subtitleslangcheck
                        compare actual subtitle language with claimed ISO 639-(1/2) in filename
  -gc, --garbagecollector
                        identifies garbage files and folders
  -ls, --listsubtitles  list all subtitle files
  -lm, --listmedia      list all media files
  -lf, --listfolders    list all folders
  -mr, --machine        output machine-readable only (supported JSON)
```

## For development

```bash
pip install pipreqs
pipreqs ./ --force # to create a new requirements.txt after adding/removing dependencies.
```