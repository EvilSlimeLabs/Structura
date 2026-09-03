"""The Structura version, from the one place it is written down.

`pyproject.toml` holds it, in `[project] version`, which is where PEP 621 says a
version lives and where every packaging tool looks for it. Nothing else declares
one.

Reading it back has to work three ways, because Structura runs three ways:

  * **installed with pip**: the version is in the installed distribution's
    metadata, and `importlib.metadata` is the standard way to ask
  * **from a checkout**: there is no installed distribution, so the file itself
    is parsed
  * **frozen by PyInstaller**: there is no distribution metadata either, and
    the spec packs `pyproject.toml` into the bundle for this reason

`tomllib` is standard library from Python 3.11, which is what `requires-python`
asks for, so parsing costs no dependency.
"""
import os
import sys

FALLBACK = "0.0.0"
DISTRIBUTION = "structura"

_cached = None


def _from_metadata():
    """The version pip recorded at install time, if the package was installed."""
    try:
        from importlib import metadata

        return metadata.version(DISTRIBUTION)
    except Exception:
        return None


def _project_files():
    """Where pyproject.toml might be, nearest first."""
    if getattr(sys, "frozen", False):
        # beside the executable, then inside the bundle
        yield os.path.join(os.path.dirname(sys.executable), "pyproject.toml")
        inside = getattr(sys, "_MEIPASS", None)
        if inside:
            yield os.path.join(inside, "pyproject.toml")
    # a checkout: the directory above this package
    here = os.path.dirname(os.path.abspath(__file__))
    yield os.path.join(os.path.dirname(here), "pyproject.toml")


def _from_project_file():
    """The version out of pyproject.toml itself."""
    try:
        import tomllib
    except ImportError:                     # pragma: no cover - before 3.11
        return None
    for path in _project_files():
        if not os.path.isfile(path):
            continue
        try:
            with open(path, "rb") as handle:
                found = tomllib.load(handle)["project"]["version"]
        except (OSError, KeyError, ValueError):
            continue
        if found:
            return found
    return None


def read():
    """The version string, or FALLBACK if it cannot be found at all.

    Answered once and remembered: it cannot change while the program runs, and
    it is asked for by the manifest, the credits line and the window title.
    """
    global _cached
    if _cached is None:
        _cached = _from_metadata() or _from_project_file() or FALLBACK
    return _cached


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
