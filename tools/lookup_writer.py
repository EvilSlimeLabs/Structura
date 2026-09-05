"""Change one family in a lookup table without reformatting the rest.

`block_uv.json` is not formatted consistently, because some entries keep their
numeric arrays on one line and most do not. Rewriting the whole file from a
parsed copy therefore reformats entries nobody touched and buries the real
change in thousands of lines of noise. Everything here replaces or appends one
family's span and leaves every byte outside it alone.

Not shipped. The generated pack reads the tables, never this.
"""
import io
import json
import re

## a list whose items are numbers or lists, however deeply nested
_NUMERIC = re.compile(
    r"\[\s*((?:-?\d+(?:\.\d+)?|\[[^][]*\])"
    r"(?:\s*,\s*(?:-?\d+(?:\.\d+)?|\[[^][]*\]))*)\s*\]")


def compact(text, rounds=6):
    """Put arrays of plain numbers back on one line."""
    for _ in range(rounds):
        text = _NUMERIC.sub(
            lambda m: "[%s]" % re.sub(r"\s+", " ", m.group(1)).strip(), text)
    return text


def render(family, value, tight=False):
    """One family, formatted as the file writes them."""
    body = json.dumps({family: value}, indent="\t", ensure_ascii=False)
    body = body[body.index("\n") + 1:body.rindex("\n")]
    return compact(body) if tight else body


def _span(text, family):
    """Where a top-level family's entry starts and ends in the raw text."""
    opening = '\n\t"%s": {' % family
    start = text.find(opening)
    if start < 0:
        return None
    depth = 0
    for i in range(text.index("{", start + 1), len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return start + 1, i + 1
    raise ValueError("unbalanced braces after %r" % family)


def put(path, family, value, tight=False):
    """Replace a family if the file has it, or append it if it does not."""
    text = io.open(path, encoding="utf-8").read()
    block = render(family, value, tight)
    found = _span(text, family)
    if found:
        start, end = found
        text = text[:start] + block + text[end:]
        what = "replaced"
    else:
        close = text.rstrip().rfind("}")
        text = text[:close].rstrip() + ",\n" + block + "\n}\n"
        what = "added"
    io.open(path, "w", encoding="utf-8", newline="").write(text)
    ## a malformed edit should fail here rather than in a build weeks later
    json.loads(io.open(path, encoding="utf-8").read())
    return what


def drop(path, family):
    """Remove a family, if it is there."""
    text = io.open(path, encoding="utf-8").read()
    found = _span(text, family)
    if not found:
        return False
    start, end = found
    ## An entry is one item of an object, so exactly one of the two commas
    ## either side of it goes with it: the one after, unless this was the last
    ## item and there is none, in which case the one before. Taking both runs
    ## the two entries that were its neighbours together.
    after = end
    while after < len(text) and text[after] in " \t":
        after += 1
    if after < len(text) and text[after] == ",":
        text = text[:start] + text[after + 1:].lstrip("\n")
    else:
        text = (text[:start].rstrip().rstrip(",") + "\n"
                + text[end:].lstrip("\n"))
    io.open(path, "w", encoding="utf-8", newline="").write(text)
    json.loads(io.open(path, encoding="utf-8").read())
    return True
