"""Reads lookups/langs.csv, one column per language.

The CSV's column headings are the language's own name for itself, which is what
belongs in a language picker. Each one also carries an ISO 639-1 or ISO 639-2 code, because
the picker labels languages by code rather than by flag: a flag is a country and
several countries share a language, so a flag is the wrong symbol for the job.
"""
import csv
import os

import lang_fun
import paths

## column heading -> ISO 639-1/639-2 code. A language with no entry falls back to the
## first two letters of its own name, which is wrong often enough to be worth
## adding a row here rather than relying on.
CODES = {
    "English": "en",
    "Українська": "uk",
    "Español": "es",
    "简体中文": "zh",
    "Tagalog": "tl",
    "Cebuano": "ceb",      # no two-letter code exists; ISO 639-2 it is
    "Test": "xx",
}


def parse():
    values = {}
    with open(paths.lookup('langs.csv'), 'r', newline='', encoding='utf-8-sig') as csvfile:
        reader = csv.reader(csvfile)
        header = next(reader)
        for i in range(len(header)-1):
            values[header[i+1]] = {}
        for row in reader:
            ref = row[0]
            for i in range(len(row)-1):
                values[header[i+1]][ref] = row[i+1]
    return values


def code(language):
    """The badge label for a language.

    An ISO code where the language has one, and a made-up three letter tag for
    the constructed languages, which have none because they are not real
    languages -- that is the point of colouring their badges differently too.
    """
    invented = lang_fun.code(language)
    if invented:
        return invented
    return CODES.get(language, language[:2].lower())


def constructed(language):
    """Whether this is one of the joke languages rather than a real one."""
    return lang_fun.code(language) is not None
