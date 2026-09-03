"""User settings and translated strings, shared by the window and the CLI.

Kept out of both so the GUI module and the entry point can each read them
without importing the other. Importing this has no side effects; nothing is
read from disk until load() is called.
"""
import json
import os
import sys

from structura import lang_fun
from structura import lang_parse
from structura import paths
SETTINGS_NAME = ".structura"

## The settings file Structura 1.7 and earlier wrote. Read once, to carry an
## existing choice across, and never written to.
LEGACY_SETTINGS_FILE = "settings.json"


def settings_file():
    """The settings file to use.

    A `.structura` sitting next to the **executable** wins, which makes the
    program portable: put it on a stick with its settings beside it and it
    carries them between machines, touching nothing on the host. Otherwise
    settings live in the home directory, where they survive replacing the
    executable and work when the program is run from a folder the user cannot
    write to. The home copy is the one created when neither exists.

    Only a frozen build has somewhere meaningful to be "beside": an installed
    package sits in site-packages, which is shared between everyone using that
    interpreter and is not the user's to write to. `paths.beside_executable()`
    answers the package directory when not frozen, which is right for reading
    data and wrong for this, so this asks the question directly.
    """
    if paths.frozen():
        portable = os.path.join(os.path.dirname(sys.executable), SETTINGS_NAME)
        if os.path.isfile(portable):
            return portable
    return os.path.join(os.path.expanduser("~"), SETTINGS_NAME)

DEFAULT_LANGUAGE = "English"
## a placeholder column in langs.csv, useful for spotting a missing lookup but
## not something to offer in the menu
HIDDEN_LANGUAGES = {"Test"}

## "system" follows the desktop. It is the default, and falls back to dark when
## the desktop cannot be asked, because a dark window is the safer thing to show
## against an unknown background.
THEMES = ("system", "light", "dark")
DEFAULT_THEME = "system"
FALLBACK_THEME = "dark"

## The slider is transparency: 0 is a solid ghost block and 100 would be
## invisible. It stops at 99 so a ghost block always has some alpha left.
## Transparency is the number the user sets, so it is the one defined here and
## everything else is derived from it. The CLI's --opacity and the core's
## DEFAULT_ALPHA both have to land on the same ghost block as the slider does.
DEFAULT_TRANSPARENCY = 65
DEFAULT_OPACITY = 100 - DEFAULT_TRANSPARENCY
MAX_TRANSPARENCY = 99

def default_output_dir():
    return paths.default_output_dir()


## What a generated pack does about TechPack, remembered between runs. The
## default is to leave it alone: bundling somebody else's pack into yours is a
## deliberate act, not a thing to happen because a switch was left on.
TECH_PACK_MODES = ("none", "compatibility", "full")
DEFAULT_TECH_PACK = "none"

DEFAULTS = {"lang": DEFAULT_LANGUAGE,
            "theme": DEFAULT_THEME,
            "tech_pack": DEFAULT_TECH_PACK,
            "output_dir": ""}          # empty means "use the default"

settings = dict(DEFAULTS)
langs = {}


def transparency_to_alpha(transparency):
    """The slider reads as transparency; set_opacity wants an alpha fraction."""
    return (100 - float(transparency)) / 100


def language(name=None):
    """The strings for `name`, with English filling any gap.

    A translation column that is missing a row, or has it blank, would otherwise
    put an empty label on screen.
    """
    name = name or settings.get("lang", DEFAULT_LANGUAGE)
    strings = dict(langs.get(DEFAULT_LANGUAGE, {}))
    strings.update({k: v for k, v in langs.get(name, {}).items() if v})
    return strings


## The order the picker shows. English first because it is the source the rest
## are translated from and the fallback for anything missing; then the other
## real languages alphabetically by their own name; then the joke ones together
## at the end, where nobody scrolling for a real language has to pass them.
LANGUAGE_ORDER = ["English", "Cebuano", "Español", "Tagalog", "Українська", "简体中文"]


def choices():
    """The languages worth offering, in an order somebody would expect."""
    offered = [name for name in langs if name not in HIDDEN_LANGUAGES]
    real = [n for n in LANGUAGE_ORDER if n in offered]
    real += sorted(n for n in offered
                   if n not in LANGUAGE_ORDER and n not in lang_fun.names())
    invented = [n for n in lang_fun.names() if n in offered]
    return real + invented


def save():
    try:
        with open(settings_file(), "w+", encoding="utf-8") as file:
            json.dump(settings, file, indent=2)
    except OSError:
        ## a read-only working directory is not a reason to refuse to run
        pass


def read_languages():
    """Every language on offer: the CSV columns plus the generated ones.

    The constructed languages are transformations of English rather than stored
    columns, so they cover every string the window has without anyone
    maintaining them.
    """
    table = lang_parse.parse()
    english = table.get(DEFAULT_LANGUAGE, {})
    for name in lang_fun.names():
        table[name] = lang_fun.translate(name, english)
    return table


def _read(path):
    try:
        with open(path, encoding="utf-8") as file:
            stored = json.load(file)
        return stored if isinstance(stored, dict) else None
    except (OSError, ValueError):
        ## a truncated or hand-edited file must not stop the program starting
        return None


def load():
    """Read langs.csv and the settings file. Returns the language's strings."""
    global settings, langs
    langs = read_languages()
    settings = dict(DEFAULTS)
    stored = _read(settings_file())
    if stored is None and os.path.exists(LEGACY_SETTINGS_FILE):
        ## carry an older choice over the first time, then leave the old file
        ## alone rather than deleting something the user may still want
        stored = _read(LEGACY_SETTINGS_FILE)
    if stored:
        settings.update({k: v for k, v in stored.items() if k in DEFAULTS})
    ## an unknown language or theme must not stop the program starting either
    if settings.get("lang") not in langs:
        settings["lang"] = DEFAULT_LANGUAGE
    if settings.get("theme") not in THEMES:
        settings["theme"] = DEFAULT_THEME
    if settings.get("tech_pack") not in TECH_PACK_MODES:
        settings["tech_pack"] = DEFAULT_TECH_PACK
    if not isinstance(settings.get("output_dir"), str):
        settings["output_dir"] = ""
    save()
    return language()


def output_dir():
    """Where finished packs go. Empty means the platform default."""
    chosen = settings.get("output_dir") or ""
    return chosen or default_output_dir()


def set_output_dir(path):
    """Remember a folder. Storing the default as empty keeps the setting
    meaningful if the default ever moves."""
    path = (path or "").strip()
    settings["output_dir"] = "" if path == default_output_dir() else path
    save()
    return output_dir()


def set_language(name):
    if name in langs:
        settings["lang"] = name
        save()
    return language()


def set_tech_pack(mode):
    """Remember what to do about TechPack. Anything unrecognised means none."""
    settings["tech_pack"] = mode if mode in TECH_PACK_MODES else DEFAULT_TECH_PACK
    save()
    return settings["tech_pack"]


def set_theme(name):
    if name in THEMES:
        settings["theme"] = name
        save()
    return settings["theme"]
