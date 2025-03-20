#!/usr/bin/python3

import re, random

# A regex that matches a syllable, with three groups for the three
# segments of the syllable: onset (initial consonants), nucleus (vowels),
# and coda (final consonants).
# The regex also matches if there is just an onset (even an empty
# onset); this case corresponds to the final partial syllable of the
# stem, which is usually the consonant before a vowel ending (for
# example, the d in "ca-na-d a").
syllableRgx = re.compile(r"(y|[^aeiouy]*)([aeiouy]+|$)([^aeiouy]*)")
nameFile = "names.txt"

# Dictionary that holds the frequency of each syllable count (note that these
# are the syllables *before* the ending, so "al-ba-n ia" only counts two)
syllableCounts = {}

# List of four dictionaries (for onsets, nuclei, codas, and endings):
# Each dictionary's key/value pairs are prevSegment:segmentDict, where
# segmentDict is a frequency dictionary of various onsets, nuclei, codas,
# or endings, and prevSegment is a segment that can be the last nonempty
# segment preceding them. A prevSegment of None marks segments at the
# beginnings of names.
segmentData = [{}, {}, {}, {}]
ONSET = 0
NUCLEUS = 1
CODA = 2
ENDING = 3

# Read names from file and generate the segmentData structure
with open(nameFile) as f:
    for line in f.readlines():
        # Strip whitespace, ignore blank lines and comments
        line = line.strip()
        if not line:
            continue
        if line[0] == "#":
            continue
        stem, ending = line.split()
        # Endings should be of the format noun/adj
        if "/" not in ending:
            # The noun ending is given; the adjective ending can be
            # derived by appending -n
            ending = "{}/{}n".format(ending, ending)
        # Syllable count is the number of hyphens
        syllableCount = stem.count("-")
        if syllableCount in syllableCounts:
            syllableCounts[syllableCount] += 1
        else:
            syllableCounts[syllableCount] = 1

        # Add the segments in this name to segmentData
        prevSegment = None
        for syllable in stem.split("-"):
            segments = syllableRgx.match(syllable).groups()
            if segments[NUCLEUS] == segments[CODA] == "":
                # A syllable with emtpy nucleus and coda comes right before
                # the ending, so we only process the onset
                segments = (segments[ONSET],)
            for segType, segment in enumerate(segments):
                if prevSegment not in segmentData[segType]:
                    segmentData[segType][prevSegment] = {}
                segFrequencies = segmentData[segType][prevSegment]
                if segment in segFrequencies:
                    segFrequencies[segment] += 1
                else:
                    segFrequencies[segment] = 1
                if segment:
                    prevSegment = segment
        # Add the ending to segmentData
        if prevSegment not in segmentData[ENDING]:
            segmentData[ENDING][prevSegment] = {}
        endFrequencies = segmentData[ENDING][prevSegment]
        if ending in endFrequencies:
            endFrequencies[ending] += 1
        else:
            endFrequencies[ending] = 1


def randFromFrequencies(dictionary):
    "Returns a random dictionary key, where the values represent frequencies."

    keys = dictionary.keys()
    frequencies = dictionary.values()
    index = random.randrange(sum(dictionary.values()))
    for key, freq in dictionary.items():
        if index < freq:
            # Select this one
            return key
        else:
            index -= freq
    # Weird, should have returned something
    raise ValueError("randFromFrequencies didn't pick a value "
                     "(index remainder is {})".format(index))


def markovName(syllableCount):
    "Generate a country name using a Markov-chain-like process."

    prevSegment = None
    stem = ""
    for syll in range(syllableCount):
        for segType in [ONSET, NUCLEUS, CODA]:
            try:
                segFrequencies = segmentData[segType][prevSegment]
            except KeyError:
                # In the unusual situation that the chain fails to find an
                # appropriate next segment, it's too complicated to try to
                # roll back and pick a better prevSegment; so instead,
                # return None and let the caller generate a new name
                return None
            segment = randFromFrequencies(segFrequencies)
            stem += segment
            if segment:
                prevSegment = segment

    endingOnset = None
    # Try different onsets for the last syllable till we find one that's
    # legal before an ending; we also allow empty onsets. Because it's
    # possible we won't find one, we also limit the number of retries
    # allowed.
    retries = 10
    while (retries and endingOnset != ""
           and endingOnset not in segmentData[ENDING]):
        segFrequencies = segmentData[ONSET][prevSegment]
        endingOnset = randFromFrequencies(segFrequencies)
        retries -= 1
    stem += endingOnset
    if endingOnset != "":
        prevSegment = endingOnset
    if prevSegment in segmentData[ENDING]:
        # Pick an ending that goes with the prevSegment
        endFrequencies = segmentData[ENDING][prevSegment]
        endings = randFromFrequencies(endFrequencies)
    else:
        # It can happen, if we used an empty last-syllable onset, that
        # the previous segment does not appear before any ending in the
        # data set. In this case, we'll just use -a(n) for the ending.
        endings = "a/an"
    endings = endings.split("/")
    nounForm = stem + endings[0]
    # Filter out names that are too short or too long
    if len(nounForm) < 3:
        # This would give two-letter names like Mo, which don't appeal
        # to me
        return None
    # Filter out names with weird consonant clusters at the end
    for consonants in ["bl", "tn", "sr", "sn", "sm", "shm"]:
        if nounForm.endswith(consonants):
            return None
    # Filter out names that sound like anatomical references
    for bannedSubstring in ["vag", "coc", "cok", "kok", "peni"]:
        if bannedSubstring in stem:
            return None
    if nounForm == "ass":
        # This isn't a problem if it's part of a larger name like Assyria,
        # so filter it out only if it's the entire name
        return None
    return stem, endings


async def generate_country_names(count):
    names = []
    for i in range(count):
        syllableCount = randFromFrequencies(syllableCounts)
        nameInfo = markovName(syllableCount)
        while nameInfo is None:
            nameInfo = markovName(syllableCount)
        stem, endings = nameInfo
        stem = stem.capitalize()
        noun = stem + endings[0]
        adjective = stem + endings[1]
        names.append(f"{noun} ({adjective})")
    return names
