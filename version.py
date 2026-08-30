"""Single source of truth for the Structura version.

The VERSION file at the repository root holds the version as `major.minor.fix`.
`build.py` copies it into the release zip beside the executable, so the same
lookup works from a source checkout and from a frozen build.
"""
import os
import sys

FALLBACK = "0.0.0"


def _candidate_dirs():
    """Where VERSION might live, nearest first."""
    if getattr(sys, "frozen", False):
        # a PyInstaller build runs from a temp dir; the file ships next to the exe
        yield os.path.dirname(sys.executable)
    yield os.path.dirname(os.path.abspath(__file__))
    yield os.getcwd()


def read():
    """The version string, or FALLBACK when the file is missing or empty."""
    for directory in _candidate_dirs():
        path = os.path.join(directory, "VERSION")
        if os.path.isfile(path):
            with open(path, encoding="utf-8-sig") as f:
                text = f.read().strip()
            if text:
                return text
    return FALLBACK


def as_tuple():
    """The version as the three-integer list a Bedrock manifest wants.

    Anything that is not a plain integer is dropped, and the result is padded
    or trimmed to three parts, so a pre-release suffix cannot break a build.
    """
    parts = []
    for part in read().split("."):
        digits = "".join(c for c in part if c.isdigit())
        parts.append(int(digits) if digits else 0)
    parts = (parts + [0, 0, 0])[:3]
    return parts


if __name__ == "__main__":
    print(read())
