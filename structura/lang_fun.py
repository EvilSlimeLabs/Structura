"""The joke languages, generated from English rather than stored.

Pirate, LOLCAT, Shakespearean, upside-down and Enchanting are transformations of
the English strings, applied when the language is selected. Keeping them as
transforms rather than as columns in langs.csv matters for a practical reason:
there are sixty-odd strings and five of these languages, and every new label
added to the window would otherwise need three hundred more cells of nonsense
maintained by hand. Generated, they cover whatever the window asks for next.

**Format placeholders are protected.** The strings carry `{}` markers that get a
filename or a count substituted into them, so every transform runs over the text
between the placeholders and never over the placeholders themselves. Without
that, reversing "Built {}" produces "}{ ..." and breaks the substitution.

Enchanting is the exception: it is not a text transform at all. The enchanting
table alphabet is a *font*, and there is no Unicode block for it, so the strings
are left in English and `ui_fonts` hands the window the rune face that
tools/make_fonts.py builds from the resource pack's own glyph sheet.
"""
import re

## a placeholder like {} or {0} or {name}: never transformed
PLACEHOLDER = re.compile(r"(\{[^{}]*\})")


def _apply(text, transform, reverse=False):
    """Run `transform` over the text between placeholders only."""
    parts = PLACEHOLDER.split(text)
    out = [part if PLACEHOLDER.fullmatch(part) else transform(part)
           for part in parts]
    if reverse:
        out.reverse()
    return "".join(out)


def _words(text, table):
    """Replace whole words using `table`, keeping the original capitalisation."""
    def swap(match):
        word = match.group(0)
        replacement = table.get(word.lower())
        if replacement is None:
            return word
        if word.isupper() and len(word) > 1:
            return replacement.upper()
        if word[0].isupper():
            return replacement[0].upper() + replacement[1:]
        return replacement
    return re.sub(r"[A-Za-z']+", swap, text)


# --- pirate ----------------------------------------------------------------

PIRATE = {
    "you": "ye", "your": "yer", "yours": "yers", "my": "me", "mine": "me own",
    "is": "be", "are": "be", "am": "be", "was": "were",
    "the": "th'", "of": "o'", "to": "t'", "and": "an'", "for": "fer",
    "yes": "aye", "no": "nay", "friend": "matey", "friends": "hearties",
    "hello": "ahoy", "stop": "belay", "before": "afore", "over": "o'er",
    "file": "scroll", "files": "scrolls", "folder": "chest", "name": "moniker",
    "add": "hoist", "remove": "keelhaul", "make": "forge", "build": "raise",
    "built": "raised", "building": "raisin'", "settings": "riggin'",
    "language": "tongue", "theme": "colours", "close": "batten",
    "required": "demanded", "optional": "as ye please", "ready": "shipshape",
    "error": "blunder", "failed": "run aground", "structure": "wreck",
    "structures": "wrecks", "block": "barnacle", "blocks": "barnacles",
    "pack": "haul", "icon": "figurehead", "description": "yarn",
    "show": "spy", "reading": "readin'", "packing": "stowin'",
    "cannot": "can't", "could": "could", "with": "wi'", "more": "more",
    "than": "than", "one": "one", "least": "least", "must": "must",
    "unique": "one of a kind", "short": "brief", "big": "grand",
    "mode": "way", "offset": "bearin'", "transparency": "ghostliness",
    ## the labels that were coming through in plain English
    "get": "fetch", "global": "world-wide", "cords": "bearin's",
    "coordinates": "bearin's", "corner": "nook", "update": "refit",
    "browse": "rummage", "advanced": "seasoned", "bundle": "lash on",
    "system": "as she be", "light": "sunlit", "dark": "murky",
    "added": "hoisted", "removed": "keelhauled", "cleared": "swabbed",
    "help": "aid", "about": "concernin'", "website": "port o' call",
    "report": "log", "issue": "trouble", "original": "first",
    "authors": "scribes", "clear": "swab", "reset": "rig anew",
    "low": "lean", "high": "full", "geometry": "carvin'",
    "detail": "carvin'", "detailed": "finely carved", "shapes": "carvin's",
    "textures": "paintwork", "positions": "berths", "render": "paint",
    "graphics": "paintin'", "card": "engine", "draws": "paints",
    "simpler": "plainer", "large": "grand",
    "none": "nary a one", "compatibility": "sailin' together",
}


def pirate(text):
    def go(chunk):
        chunk = _words(chunk, PIRATE)
        chunk = re.sub(r"\bing\b", "in'", chunk)
        return chunk
    return _apply(text, go)


# --- lolcat ----------------------------------------------------------------

LOLCAT = {
    "the": "teh", "you": "u", "your": "ur", "you're": "ur", "are": "r",
    "is": "iz", "was": "wuz", "has": "haz", "have": "haz", "of": "ov",
    "with": "wif", "more": "moar", "than": "than", "please": "plz",
    "thanks": "thx", "yes": "yah", "no": "nope", "and": "an",
    "name": "naem", "names": "naemz", "file": "fiel", "files": "fielz",
    "add": "gimme", "remove": "nom", "make": "maek", "made": "maed",
    "build": "bild", "built": "bilt", "building": "bildin", "ready": "reddy",
    "settings": "settingz", "language": "langwij", "theme": "colorz",
    "close": "bai", "error": "oh noes", "failed": "did not want",
    "structure": "strukchur", "structures": "strukchurz",
    "block": "blok", "blocks": "blokz", "pack": "pak", "packs": "pakz",
    "packing": "pakin", "reading": "readin", "icon": "pikchur",
    "description": "wut it iz", "required": "needz", "optional": "if u want",
    "show": "shoo", "folder": "foldur", "cannot": "cant", "could": "cud",
    "offset": "moovs", "transparency": "seethru", "mode": "mode",
    "unique": "wun of a kind", "least": "leest", "short": "smol",
    "big": "BIG", "must": "gotta", "in": "in", "game": "gaem",
    ## the labels that were coming through in plain English
    "get": "haz", "global": "big", "cords": "numberz",
    "coordinates": "numberz", "corner": "cornr", "update": "updaet",
    "browse": "luk", "advanced": "fancy", "bundle": "stuf in",
    "system": "whatevr", "light": "brite", "dark": "nite",
    "added": "gotted", "removed": "nommed", "cleared": "all gawn",
    "help": "halp", "about": "bout", "website": "webz", "report": "tell",
    "issue": "problum", "original": "orijinal", "authors": "peeplz",
    "clear": "nom", "reset": "startz ovr",
    "low": "smol", "high": "big", "geometry": "shaypz", "detail": "stuf",
    "detailed": "fancy", "shapes": "shaypz", "textures": "skinz",
    "positions": "spotz", "render": "draw", "graphics": "grafix",
    "card": "kard", "draws": "drawz", "simpler": "simplr", "large": "big",
    "none": "nuffin", "compatibility": "getz along",
}


def lolcat(text):
    def go(chunk):
        chunk = _words(chunk, LOLCAT)
        chunk = re.sub(r"tion\b", "shun", chunk)
        return chunk
    return _apply(text, go)


# --- shakespearean ---------------------------------------------------------

SHAKESPEARE = {
    "you": "thou", "your": "thy", "yours": "thine", "you're": "thou art",
    "are": "art", "is": "is", "am": "am", "do": "dost", "does": "doth",
    "have": "hast", "has": "hath", "will": "shall", "yes": "aye", "no": "nay",
    "here": "hither", "there": "thither", "before": "ere", "often": "oft",
    "add": "prithee add", "remove": "banish", "make": "forge", "made": "wrought",
    "build": "raise", "built": "wrought", "building": "a-forging",
    "ready": "at the ready", "error": "misfortune", "failed": "hath faltered",
    "settings": "appointments", "language": "tongue", "theme": "raiment",
    "close": "depart", "file": "scroll", "files": "scrolls",
    "folder": "coffer", "name": "appellation", "icon": "likeness",
    "description": "epitaph", "required": "requir'd", "optional": "at thy pleasure",
    "structure": "edifice", "structures": "edifices", "block": "stone",
    "blocks": "stones", "pack": "bundle", "show": "reveal",
    "reading": "perusing", "packing": "binding", "cannot": "cannot",
    "could": "couldst", "must": "must needs", "unique": "singular",
    "least": "least", "more": "more", "than": "than", "with": "with",
    "short": "brief", "big": "grand", "mode": "manner", "offset": "displacement",
    "transparency": "translucence", "game": "revel",
    ## the labels that were coming through in plain English
    "get": "fetch", "global": "worldly", "cords": "bearings",
    "coordinates": "bearings", "corner": "nook", "update": "renew",
    "browse": "peruse", "advanced": "learn'd", "bundle": "bind",
    "system": "custom", "light": "fair", "dark": "sable",
    "added": "join'd", "removed": "banish'd", "cleared": "purg'd",
    "help": "succour", "about": "concerning", "website": "chronicle",
    "report": "recount", "issue": "grievance", "original": "first",
    "authors": "makers", "clear": "purge", "reset": "restore",
    "low": "plain", "high": "full", "geometry": "form", "detail": "nicety",
    "detailed": "wrought", "shapes": "forms", "textures": "hues",
    "positions": "stations", "render": "limn", "graphics": "limning",
    "card": "engine", "draws": "limns", "simpler": "plainer",
    "large": "vast",
    "none": "none at all", "compatibility": "concord",
}


def shakespeare(text):
    def go(chunk):
        return _words(chunk, SHAKESPEARE)
    return _apply(text, go)


# --- upside-down -----------------------------------------------------------

FLIP = {
    "a": "ɐ", "b": "q", "c": "ɔ", "d": "p", "e": "ǝ", "f": "ɟ", "g": "ƃ",
    "h": "ɥ", "i": "ᴉ", "j": "ɾ", "k": "ʞ", "l": "l", "m": "ɯ", "n": "u",
    "o": "o", "p": "d", "q": "b", "r": "ɹ", "s": "s", "t": "ʇ", "u": "n",
    "v": "ʌ", "w": "ʍ", "x": "x", "y": "ʎ", "z": "z",
    "A": "∀", "B": "𝐐", "C": "Ɔ", "D": "p", "E": "Ǝ", "F": "Ⅎ", "G": "פ",
    "H": "H", "I": "I", "J": "ſ", "K": "ʞ", "L": "˥", "M": "W", "N": "N",
    "O": "O", "P": "Ԁ", "Q": "Q", "R": "ɹ", "S": "S", "T": "┴", "U": "∩",
    "V": "Λ", "W": "M", "X": "X", "Y": "⅄", "Z": "Z",
    "0": "0", "1": "Ɩ", "2": "ᄅ", "3": "Ɛ", "4": "ㄣ", "5": "ϛ", "6": "9",
    "7": "ㄥ", "8": "8", "9": "6",
    ".": "˙", ",": "'", "'": ",", '"': "„", "?": "¿", "!": "¡",
    "(": ")", ")": "(", "[": "]", "]": "[", "<": ">", ">": "<",
    "_": "‾", "&": "⅋", "/": "\\", "\\": "/",
}


def upside_down(text):
    def go(chunk):
        return "".join(FLIP.get(ch, ch) for ch in reversed(chunk))
    ## the whole line turns over, so the pieces swap ends as well as the letters
    return _apply(text, go, reverse=True)


# --- enchanting ------------------------------------------------------------

def enchanting(text):
    """English, unchanged, because the enchanting alphabet is a *font*.

    The glyphs ship as a real font built from the resource pack's own sheet, so
    the text is left alone and the typeface does the work. That is what the game
    does, and it keeps the text decipherable letter by letter the way the
    alphabet is meant to be.
    """
    return text


# --- registry --------------------------------------------------------------

## name shown in the picker -> (transform, badge code)
TRANSFORMS = {
    "Enchanting":    (enchanting, "sga"),
    "Pirate Speak":  (pirate, "arr"),
    "LOLCAT":        (lolcat, "cat"),
    "Shakespearean": (shakespeare, "wil"),
    "ɥsᴉlƃuƎ":       (upside_down, "uen"),
}


def names():
    return list(TRANSFORMS)


def translate(name, english):
    """A whole string table, transformed. Unknown names come back unchanged."""
    entry = TRANSFORMS.get(name)
    if entry is None:
        return dict(english)
    transform = entry[0]
    return {key: transform(value) for key, value in english.items()}


def code(name):
    entry = TRANSFORMS.get(name)
    return entry[1] if entry else None
