#   -*- coding: utf-8 -*-
"""Media Library Cleaner."""

# import sys
import os
import soundex
import re
# import progress
# import terminaltables
import io
import pysrt
import argparse as ap
# import ConfigParser
from terminaltables import AsciiTable
from progress.bar import Bar
from langdetect import detect, detect_langs
# from HTMLParser import HTMLParser
from html.parser import HTMLParser # for python 3

# from colorama import init, Fore, Back, Style
from colorama import init, Fore, Style
from iso639 import is_valid639_1, is_valid639_2, to_iso639_1, to_iso639_2
from iso639 import to_name as iso639_to_name

# TODO: Implement thesubdb.com and/or opensubtitles.org
# TODO: Research possibilities of auto converting sub/idx/sup/ass to srt
# TODO: Research possibilities of auto converting srt file-encoding and
#       fix of long lines etc

APP_TITLE = "Media Library Cleaner"
APP_VERSION = "0.9 beta"
APP_STR_PADDING = 100
dependencies = ["terminaltables", "progress", "colorama", "soundex",
                "langdetect", "pysrt", "htmlparser", "iso639", "configparser"]
# TODO: Add --checkalldependencies to check all possible needed dependencies
# TODO: Disable "terminaltables" dependency when --notables is used
# TODO: Disable "progress" dependency when --noprogress is used
# TODO: Disable "colorama" dependency when --nocolours is used
# TODO: Disable "soundex" dependency when --nosoundex is NOT used
# TODO: Disable "langdetect" dependency when --nolangdetect is used

# === Enable colored output on Windows and other platforms
if os.name == 'nt':
    init(convert=True)
else:
    init(convert=False)


class MLStripper(HTMLParser):
    """Class for stripping HTML."""

    def __init__(self):
        """Initialize MLStripper class."""
        self.reset()
        self.fed = []

    def handle_data(self, d):
        """Handle HTML data."""
        self.fed.append(d)

    def get_data(self):
        """Get HTML data."""
        return ''.join(self.fed)


def strip_tags(html):
    """Strip HTML tags."""
    s = MLStripper()
    s.feed(html)
    return s.get_data()


def bold(string):
    """To print text bold."""
    return (Style.BRIGHT + str(string) + Style.NORMAL)


def green(string):
    """To print text green."""
    return (Fore.GREEN + string + Fore.WHITE)


def printNotificationTitle(str):
    """To print text with the title styling."""
    printString = "+ " + str + " "
    printString = printString . ljust(APP_STR_PADDING, '+')
    print(green(printString))


def printNotificationNew(str):
    """To print text with the new notification styling."""
    print("\n" + green(bold("[ new     ] ")) + str)


def printNotificationInfo(str):
    """To print text with the info notification styling."""
    print(Fore.CYAN + bold("[ info    ] ") + Fore.WHITE + str)


def printNotificationWarning(str):
    """To print text with warning notification styling."""
    print(Fore.YELLOW + bold("[ warning ] ") + Fore.WHITE + str)


def printNotificationDanger(str):
    """To print text with danger notification styling."""
    print(Fore.RED + bold("[ danger  ] ") + Fore.WHITE + str)


def levenshtein(s1, s2):
    """Calculate levenshtein distance between two strings."""
    if len(s1) < len(s2):
        return levenshtein(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            # j+1 instead of j since previous_row and current_row
            # are one character longer
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1        # than s2
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    return previous_row[-1]


def getIsoLanguageCodeFromFilename(filename):
    """
    Return the iso language from filenames ending with a language code.

    Currently a tricky way of getting the part before the extension is used
    Assuming that only a dot is used before and after the language code
    TODO: Improve language code extraction using regex
    """
    (fileName, fileExt) = os.path.splitext(filename)
    (filenameWithoutLang, langCode) = os.path.splitext(fileName)
    return langCode[1:]


def matchFoldersOnExactName(scanfolder, ignoreyearfolders):
    """Find folders with the exact same name, recursively."""
    knownListFolderNames = {}
    total = 0
    duplicate = 0
    ignored = 0
    for subdir, dirs, files in os.walk(scanfolder):
        total = total + 1
        subdirName = os.path.basename(os.path.normpath(subdir))
        if subdirName not in knownListFolderNames:
            matchSubdirName = bool(re.match('^[0-9]{4}$', subdirName))
            if ignoreyearfolders is True and matchSubdirName is False:
                knownListFolderNames[subdirName] = subdir
            elif ignoreyearfolders is False:
                knownListFolderNames[subdirName] = subdir
            else:
                ignored = ignored + 1
        else:
            duplicate = duplicate + 1
            warning = "Found duplicate foldername \"" + bold(subdirName) + "\""
            warning += "\n\t1: " + knownListFolderNames[subdirName]
            warning += "\n\t2: " + subdir
            printNotificationWarning(warning)
    dataStatsTable = [
        ['Unique', str(len(knownListFolderNames))],
        ['Duplicate', str(duplicate)]
    ]

    if ignoreyearfolders:
        dataStatsTable.append(['Ignored', str(ignored)])
    heading = 'Total'.ljust((APP_STR_PADDING-(4+(3*1))-len(str(total))), ' ')
    dataStatsTable.append([heading, str(total)])
    statsTable = AsciiTable(dataStatsTable)
    statsTable.title = Fore.CYAN + '[info] ' + Fore.WHITE + 'Results'
    statsTable.inner_heading_row_border = False
    statsTable.justify_columns[1] = 'right'
    print(statsTable.table)


def matchFoldersOnSoundex(scanfolder, ignoreyearfolders):
    """Find similar foldernames based on soundex, recursively."""
    knownListFolderNames = {}
    total = 0
    duplicate = 0
    ignored = 0
    ignoreSoundex = ["10000000", "20000000"]
    dataStatsTable = []
    for subdir, dirs, files in os.walk(scanfolder):
        total = total + 1
        subdirName = os.path.basename(os.path.normpath(subdir))
        try:
            sss = soundex.Soundex()
            soundexOfName = sss.soundex(str(subdirName), 8)
            if soundexOfName not in knownListFolderNames:
                subdirNameMatch = bool(re.match('^[0-9]{4}$', subdirName))
                if (
                        ignoreyearfolders is True
                        and subdirNameMatch is False
                        and soundexOfName not in ignoreSoundex
                ):
                    knownListFolderNames[soundexOfName] = subdir
                elif ignoreyearfolders is False:
                    knownListFolderNames[soundexOfName] = subdir
                else:
                    ignored = ignored + 1
            else:
                duplicate = duplicate + 1
                oldSubdir = knownListFolderNames[soundexOfName]
                oldSubdirName = os.path.basename(os.path.normpath(oldSubdir))
                dataStatsTable.append([soundexOfName, oldSubdirName])
                dataStatsTable.append([soundexOfName, subdirName])
        except Exception:
            ignored = ignored + 1
            warning = "Could not calculate the soundex of foldername \""
            warning += bold(subdirName) + "\""
            printNotificationWarning(warning)
    dataStatsTable.sort(key=lambda x: x[0])
    dataStatsTable.insert(0, ["Soundex", "Folder name"])
    statsTable = AsciiTable(dataStatsTable)
    statsTable.title = Fore.CYAN + '[info] ' + Fore.WHITE + 'Results '
    print(statsTable.table)


def findSubtitlesNoneIso639(scanfolder, isoMode, disablelangdetect):
    """
    Detect subtitles that do not comply with ISO-639.

    TODO: Add more subtitle extensions (and read/parse them correctly for
          language detection)
    TODO: Seperate language detection better in different functions
    TODO: Add percentage of certainty and possible other languages when
          low certainty
    TODO: Handle unicode better to detect languages like German and Dutch
          better
    TODO: Use table
    """
    subtitleExts = ['.srt', '.sub', '.ass']
    total = 0
    incorrect = 0
    detectedlang = 0
    for subdir, dirnames, filenames in os.walk(scanfolder):
        for filename in filenames:
            incorrectSubtitle = False
            extension = os.path.splitext(filename)[1].lower()
            # subdirName = os.path.basename(os.path.normpath(subdir))
            if extension in subtitleExts:
                total = total + 1
                langcodeFromFilename = getIsoLanguageCodeFromFilename(filename)
                detectedLanguage = ""
                detectedIsoMode = False
                if is_valid639_1(langcodeFromFilename):
                    detectedIsoMode = "1"
                    detectedLanguage = iso639_to_name(langcodeFromFilename)
                if is_valid639_2(langcodeFromFilename):
                    detectedIsoMode = "2"
                    detectedLanguage = iso639_to_name(langcodeFromFilename)
                if detectedIsoMode is not isoMode:
                    isoShouldBe = ""
                    if isoMode == "1" and detectedIsoMode == "2":
                        isoShouldBe = to_iso639_1(langcodeFromFilename)
                    if isoMode == "2" and detectedIsoMode == "1":
                        isoShouldBe = to_iso639_2(langcodeFromFilename)
                    filepath = subdir + os.sep + filename
                    incorrectSubtitle = True
                    incorrect = incorrect + 1
                    warning = "Incorrectly named subtitle found at "
                    warning += bold(filepath)
                    printNotificationWarning(warning)
                    if detectedIsoMode is not False:
                        info = "\t\tLang code " + bold(langcodeFromFilename)
                        info += " (ISO 639-" + str(detectedIsoMode) + ") "
                        info += "detected. The ISO 639-" + isoMode + " code"
                        info += " for " + detectedLanguage + " is "
                        info += bold(isoShouldBe) + "."
                        printNotificationInfo(info)
                if incorrectSubtitle and not disablelangdetect:
                    filepath = subdir + os.sep + filename
                    try:
                        with io.open(filepath, "r", encoding="utf-8") as mfile:
                            my_unicode_string = mfile.read()
                        possibleLanguage = "\tDetected language is likely to "
                        possibleLanguage += "be \"" + detect(my_unicode_string)
                        possibleLanguage += "\"\n"
                        detectedlang = detectedlang + 1
                    except Exception:
                        possibleLanguage = "\tLanguage detection failed\n"
    info = "Found subtitle files " + bold(str(total)) + " of which "
    info += bold(str(incorrect)) + " are incorrectly named!"
    printNotificationInfo(info)


def findSubtitlesMediaNaming(scanfolder):
    """
    Find subtitles that do not use the media name.

    TODO: Use table
    TODO: If more mp4/mkv files are found, throw error that it's only
          supported with one mediafile on same level
    TODO: Make option/argument to exclude more than -trailers only
    TODO: Support multiple TV Series in one folder
    """
    subtitleExts = ['.srt', '.sub', '.ass']
    total = 0
    incorrect = 0
    subtitleFiles = []
    # Firstly search for subtitle files
    for subdir, dirnames, filenames in os.walk(scanfolder):
        for filename in filenames:
            subtitleFiles.append(os.path.join(subdir, filename))
    print(len(subtitleFiles))
    print(subtitleFiles)

    for subtitleFile in subtitleFiles:
        print(subtitleFile)
        print(os.path.dirname(subtitleFile))

    # incorrectSubtitle = False
    extension = os.path.splitext(filename)[1].lower()
    # subdirName = os.path.basename(os.path.normpath(subdir))
    if extension in subtitleExts:
        total = total + 1
        cm = len([name for name in os.listdir(subdir) if os.path.isfile(name)])
        if cm > 0:
            for mediafile in os.listdir(subdir):
                if (
                    (
                        mediafile.lower().endswith(".mp4")
                        or mediafile.lower().endswith(".mkv")
                        or mediafile.lower().endswith(".avi")
                        or mediafile.lower().endswith(".m4v")
                    )
                    and "-trailer" not in mediafile
                ):
                    sp1 = os.path.splitext(mediafile)
                    sp2 = os.path.splitext(filename)
                    (mediafileNameWithoutExt, mediafileExt) = sp1
                    (subfileNameWithoutExt, subfileExt) = sp2
                    sp3 = os.path.splitext(subfileNameWithoutExt)
                    (subtitleNameLikeMediaName, subtitleFilenameLangcode) = sp3
                    if mediafileNameWithoutExt != subtitleNameLikeMediaName:
                        incorrect = incorrect + 1
                        warning = "Incorrectly named subtitle found "
                        warning += os.path.join(subdir, filename)
                        warning += " (media filename: \"" + mediafile + "\")"
                        printNotificationWarning(warning)
        else:
            print("No media files in " + subdir)
    info = "Found " + bold(str(total)) + " subtitle files of which "
    info += bold(str(incorrect)) + " are incorrectly named"
    printNotificationInfo(info)


def garbagecollector(scanfolder):
    """
    Find garbage such as empty folders and empty.

    or very small files and undesired file extensions.
    """
    printNotificationInfo("Searching for empty folders")
    for subdir, dirnames, filenames in os.walk(scanfolder):
        if not os.listdir(subdir):
            printNotificationWarning("-- Found empty folder: " + subdir)
    printNotificationInfo("Searching for unexpected file extensions")
    allowExtensions = ['.mp4', '.mkv', '.avi', '.m4v', '.srt', '.sub', '.ass']
    for subdir, dirnames, filenames in os.walk(scanfolder):
        for filename in filenames:
            ext = os.path.splitext(filename)[1].lower()
            fullFilePath = os.path.join(subdir, filename)
            if os.path.isfile(fullFilePath) and ext not in allowExtensions:
                warning = "-- Found unexpected file extension: " + fullFilePath
                printNotificationWarning(warning)
    printNotificationInfo("Searching for unlikely small files")
    for subdir, dirnames, filenames in os.walk(scanfolder):
        for filename in filenames:
            fullFilePath = os.path.join(subdir, filename)
            if (
                os.path.isfile(fullFilePath)
                and os.path.getsize(fullFilePath) < (1024 * 4)
            ):
                warning = "-- Found unlikely small file: " + fullFilePath
                printNotificationWarning(warning)


def languagechecker(scanfolder):
    """
    Check language of subtitles in a folder.

    TODO: Handle unicode better to detect languages like German and
          Dutch better
    """
    subtitleExts = ['.srt', '.sub', '.ass']
    subtitleFilesCount = 0
    for subdir, dirnames, filenames in os.walk(scanfolder):
        for filename in filenames:
            extension = os.path.splitext(filename)[1].lower()
            if extension in subtitleExts:
                subtitleFilesCount = subtitleFilesCount+1
    printNotificationInfo(str(subtitleFilesCount) + " subtitle files found")
    bar = Bar('Processing', max=subtitleFilesCount)
    subtitleExts = ['.srt', '.sub', '.ass']
    failedDetection = 0
    detectedWrongLang = 0
    for subdir, dirnames, filenames in os.walk(scanfolder):
        for filename in filenames:
            extension = os.path.splitext(filename)[1].lower()
            if extension in subtitleExts:
                (fileName, fileExt) = os.path.splitext(filename)
                # Only works when suffix is correctly set with .en.srt
                (filenameWithoutLang, langCode) = os.path.splitext(fileName)
                langCode = langCode[1:]
                filepath = subdir + os.sep + filename
                try:
                    # 1. Reading SRT file
                    # 2. Removing HTML (English)
                    # 3. Timing information for language check
                    subs = pysrt.open(filepath, encoding='iso-8859-1')
                    c = 0
                    ts = ""
                    for sub in subs:
                        # skip the first, because it's usually ads (in English)
                        if c > 0:
                            ts += "\n" + strip_tags(subs[c].text)
                            c = c+1
                    possibleLanguage = detect(ts)
                    if langCode != possibleLanguage:
                        detectedWrongLang = detectedWrongLang + 1
                        warning = "Detected lang \"" + possibleLanguage + "\""
                        warning += "(" + iso639_to_name(possibleLanguage) + ")"
                        warning += " but \"" + langCode + "\""
                        warning += "(" + iso639_to_name(langCode) + ") is used"
                        warning += " in filename " + filename
                        printNotificationWarning()
                        print("\t\t" + str(detect_langs(ts)) + "\n")
                except Exception:
                    error = 1
                bar.next()
    bar.finish()
    if error:
        printNotificationDanger("Caught an exception")
    printNotificationInfo("Attempted detections: " + str(subtitleFilesCount))
    printNotificationInfo("Failed detections: " + str(failedDetection))
    printNotificationInfo("Detected wrong language: " + str(detectedWrongLang))


def printApplicationHeader():
    """Print application header."""
    str1 = "                                     __                "
    str2 = "   |\/| _ _|. _   |  .|_  _ _  _    /  | _ _  _  _ _   "
    str3 = "   |  |(-(_||(_|  |__||_)| (_|| \/  \__|(-(_|| )(-|    "
    str4 = "                                /                      "
    print(Fore.GREEN + Style.BRIGHT + "".center(APP_STR_PADDING, "+"))
    print(str1.center(APP_STR_PADDING, "+"))
    print(str2.center(APP_STR_PADDING, "+"))
    print(str3.center(APP_STR_PADDING, "+"))
    print(str4.center(APP_STR_PADDING, "+"))
    print("".center(APP_STR_PADDING, "+") + Style.NORMAL + Fore.WHITE)


def initArguments():
    """Initialize script arguments."""
    parser = ap.ArgumentParser(description=APP_TITLE + " v." + APP_VERSION)
    # TODO: Add more consistency:
    # - startletters for parameters
    # F = File
    # D = Directory (do not use "folder" anymore)
    # L = Listing parameters
    # S = Subtitle parameters
    # I = Ignore parameters
    # O = Other parameters
    parser.add_argument("-s", "--scanfolder",
                        required=False,
                        help='specify the filepath for scanning')
    parser.add_argument("-v", "--version",
                        required=False,
                        help='get current version of ' + APP_TITLE,
                        action='store_true')
    parser.add_argument("-a", "--all",
                        required=False,
                        help='use all options (helpful for code testing)',
                        action='store_true')
    parser.add_argument("-fe", "--foldernameexact",
                        required=False,
                        help='find folders with exact same foldername',
                        action='store_true')
    parser.add_argument("-fn", "--foldernamesoundex",
                        required=False,
                        help='find similar foldernames with soundex',
                        action='store_true')
    parser.add_argument("-iy", "--ignoreyearfolders",
                        required=False,
                        help='ignores folders with year-only names',
                        action='store_true')
    parser.add_argument("-is", "--ignoreseasonfolders",
                        required=False,
                        help='ignores folders with season names',
                        action='store_true')
    parser.add_argument("-si", "--subtitlesiso639",
                        required=False,
                        help='find subtitles that do not comply with ISO 639')
    parser.add_argument("-sn", "--subtitlenaming",
                        required=False,
                        help='find subtitles that do not match the media name',
                        action='store_true')
    parser.add_argument("-sl", "--subtitleslangcheck",
                        required=False,
                        help='compare actual subtitle language with claimed ISO 639-(1/2) in filename',
                        action='store_true')
    parser.add_argument("-gc", "--garbagecollector",
                        required=False,
                        help='identifies garbage files and folders',
                        action='store_true')
    parser.add_argument("-ls", "--listsubtitles",
                        required=False,
                        help='list all subtitle files',
                        action='store_true')
    parser.add_argument("-lm", "--listmedia",
                        required=False,
                        help='list all media files',
                        action='store_true')
    parser.add_argument("-lf", "--listfolders",
                        required=False,
                        help='list all folders',
                        action='store_true')
    parser.add_argument("-mr", "--machine",
                        required=False,
                        help='output machine-readable only (supported JSON)',
                        action='store_true')
    args = parser.parse_args()

    # === Actions for argument "--version"
    if args.version is True:
        printNotificationInfo(APP_TITLE + " v." + APP_VERSION)
        exit()
    else:
        if args.scanfolder is None:
            printNotificationDanger("argument -s/--scanfolder is required")
            exit()

    if args.all is True:
        args.machine = True
        args.listfolders = True
        args.listmedia = True
        args.listsubtitles = True
        args.garbagecollector = True
        args.subtitleslangcheck = True
        args.subtitlenaming = True
        args.foldernamesoundex = True
        args.foldernameexact = True
        args.subtitlesiso639 = "1"  # TODO: Get from INI file
        args.ignoreyearfolders = False  # TODO: Get from INI file
    return args


def main():
    """Initialize app."""
    printApplicationHeader()
    args = initArguments()
    printNotificationNew("Initiating " + APP_TITLE + " v." + APP_VERSION)
    # === Actions for argument "--scanfolder"
    if args.scanfolder is not None:
        normpath = os.path.normpath(str(args.scanfolder))
        abspath = os.path.abspath(normpath)
        info = "Set scan folder \"" + bold(abspath)
        printNotificationInfo(info)
        if not os.path.isdir(args.scanfolder):
            danger = "Folder \""
            danger += bold(abspath)
            danger += "\" as specified in --scanfolder does not exist or "
            danger += "is not accessible"
            printNotificationDanger(danger)
            exit()
        APP_SCANFOLDER = abspath
        APP_COUNT_FILES = 1    # Will be used as count
        APP_COUNT_FOLDERS = 1  # Will be used as count
        for _, dirnames, filenames in os.walk(APP_SCANFOLDER):
            APP_COUNT_FILES += len(filenames)
            APP_COUNT_FOLDERS += len(dirnames)
        info1 = "Scan folder contains " + bold("{:,}".format(APP_COUNT_FILES))
        info1 += " files"
        printNotificationInfo(info1)
        boldCount = bold("{:,}".format(APP_COUNT_FOLDERS))
        info2 = "Scan folder contains " + boldCount + " folders"
        printNotificationInfo(info2)

    # === Actions for argument "--foldernameexact"
    if args.foldernameexact is True:
        new = "--foldernameexact! Finding folders with exact same foldername"
        printNotificationNew(new)
        if args.ignoreyearfolders is True:
            info = "--ignoreyearfolders! Ignoring folders with year-only names"
            printNotificationInfo(info)
        if args.ignoreseasonfolders is True:
            info = "--ignoreseasonfolders! Ignoring season named folders"
        matchFoldersOnExactName(APP_SCANFOLDER, args.ignoreyearfolders)

    # === Actions for argument "--foldernamesoundex"
    if args.foldernamesoundex is True:
        new = "--foldernamesoundex! Finding similar foldernames with soundex"
        printNotificationNew(new)
        if args.ignoreyearfolders is True:
            info = "--ignoreyearfolders! Ignoring folders with years only"
            printNotificationInfo(info)
        if args.ignoreseasonfolders is True:
            info = "--ignoreseasonfolders! Ignoring season named folders"
        matchFoldersOnSoundex(APP_SCANFOLDER, args.ignoreyearfolders)

    # === Actions for argument "--subtitlesiso639"
    if args.subtitlesiso639 is not None:
        new = "--subtitlesiso639! Finding subtitle files that do not contain"
        new += "ISO 639 language codes in filenames"
        printNotificationNew(new)
        if args.subtitlesiso639 != "1" and args.subtitlesiso639 != "2":
            danger = "Expected --subtitlesiso639=1 for ISO 639-1 (two letter "
            danger += "language code) or --subtitlesiso639=2 for ISO 639-2 "
            danger += "(three letter language code)"
            printNotificationDanger(danger)
            exit()
        else:
            isoType = args.subtitlesiso639
            if isoType == "1":
                info = "Using ISO 639-1 (two letter language code) for "
                info += "subtitle filename validation"
                printNotificationInfo(info)
            else:
                info = "Using ISO 639-2 (three letter language code) for "
                info += "subtitle filename validation"
                printNotificationInfo(info)
            findSubtitlesNoneIso639(APP_SCANFOLDER, isoType, False)

    # === Actions for argument "--subtitlenaming"
    if args.subtitlenaming is True:
        new = "--subtitlenaming! Finding subtitle files that do not match the "
        new += "media naming"
        printNotificationNew(new)
        findSubtitlesMediaNaming(APP_SCANFOLDER)

    # === Actions for argument "--subtitleslangcheck"
    if args.subtitleslangcheck is True:
        new = "--subtitleslangcheck! Checking determined language against "
        new += "used language on subtitle files"
        printNotificationNew(new)

    # === Actions for argument "--garbagecollector"
    if args.garbagecollector is True:
        new = "--garbagecollector! Identifying garbage files and folders"
        printNotificationNew(new)
        garbagecollector(APP_SCANFOLDER)

    # === Actions for argument "--subtitleslangcheck"
    if args.subtitleslangcheck is True:
        new = "--languagechecker! Attempting to check the real subtitle "
        new += "language with the used ISO 639 language code"
        printNotificationNew(new)
        languagechecker(APP_SCANFOLDER)
    exit()

    # PoC
    printNotificationInfo('Foldername comparing (levenshtein, distance=3)')
    countt = 0
    for sd, dirs, files in os.walk(APP_SCANFOLDER):
        countt = countt + 1
    bar = Bar('Processing', max=countt)
    knownListFolderNamesLevenshtein = []
    for sd, dirs, files in os.walk(APP_SCANFOLDER):
        subdir = os.path.basename(os.path.normpath(sd))
        if not bool(re.match('^[0-9]{4}$', subdir)):
            for oldSubdir in knownListFolderNamesLevenshtein:
                if (
                    not bool(re.match('^[0-9]{4}$', oldSubdir))
                    and not bool(re.match('^[0-9]{4}$', subdir))
                ):
                    distance = levenshtein(oldSubdir, subdir)
                    if distance <= 3:
                        info = oldSubdir + " - " + subdir + " - levenshtein "
                        info += "distance = " + str(distance)
                        printNotificationInfo(info)
            if subdir not in knownListFolderNamesLevenshtein:
                knownListFolderNamesLevenshtein.append(subdir)
        bar.next()
    bar.finish()

    printNotificationInfo('Filename comparing (exact match)')
    knownFileListNames = []
    for subdir, dirs, files in os.walk(APP_SCANFOLDER):
        for file in files:
            if file not in knownFileListNames:
                knownFileListNames.append(file)
            else:
                print('Found double filename found: ' + subdir + file)


if __name__ == "__main__":
    main()
