"""Where Structura's data lives, however Structura was installed.

`lookups/`, `Vanilla_Resource_Pack/`, `fonts/` and `images/` sit **inside** the
package, beside the code that opens them. That is what makes the project
installable: setuptools ships package data only from under the package
directory, so a `pip install` of a project that kept them at the repository root
would install a program with no tables and no textures.

Three ways the program can be running, and this handles all of them:

  * installed with pip, or run from a checkout, where the data is beside this
    file
  * frozen by PyInstaller, where the same directories are packed into the
    bundle and unpacked to the private folder `sys._MEIPASS` points at
  * frozen, with a copy dropped beside the executable, which **wins**, because
    a bundle is read only and this is how somebody hand-editing a lookup table
    makes it take effect without rebuilding. `docs/Editing Blocks.md` covers it.

The search order is therefore beside the executable, then inside the bundle,
then the package itself.
"""
import os
import sys

## the directories that make up Structura's data
DATA_DIRS = ("lookups", "Vanilla_Resource_Pack", "fonts", "images")

## the package, which is where the data is unless something nearer has it
_PACKAGE = os.path.dirname(os.path.abspath(__file__))


def frozen():
    return getattr(sys, "frozen", False)


def beside_executable():
    """The folder to write into, and the one an override is read from.

    Beside the executable when frozen; the package itself otherwise, since that
    is the only place a source or pip install has to put anything.
    """
    if frozen():
        return os.path.dirname(sys.executable)
    return _PACKAGE


def bundled():
    """The folder PyInstaller unpacked the bundle into, if there is one."""
    return getattr(sys, "_MEIPASS", None)


def roots():
    """Every place data might be, best first."""
    found = [beside_executable()]
    inside = bundled()
    if inside:
        found.append(inside)
    if _PACKAGE not in found:
        found.append(_PACKAGE)
    return found


def data(*parts):
    """The path to a data file, wherever it actually is.

    Falls back to the writable location when nothing exists yet, so a caller
    that is creating the file puts it somewhere sensible and an error message
    names a path a person can act on.
    """
    relative = os.path.join(*parts)
    for root in roots():
        candidate = os.path.join(root, relative)
        if os.path.exists(candidate):
            return candidate
    return os.path.join(beside_executable(), relative)


def writable(*parts):
    """Where a file should be written: always beside the executable."""
    return os.path.join(beside_executable(), *parts)


def vanilla_pack():
    """The trimmed vanilla resource pack the generator reads textures from."""
    return data("Vanilla_Resource_Pack")


def lookup(name):
    return data("lookups", name)


def documents():
    """The user's Documents folder, or the closest thing this platform has.

    Windows keeps it under the user profile and can have it redirected, so the
    shell is asked before falling back to the obvious path. Elsewhere there is
    no strong convention, and the home directory is the honest answer.
    """
    home = os.path.expanduser("~")
    if sys.platform.startswith("win"):
        try:
            import ctypes
            from ctypes import wintypes
            buffer = ctypes.create_unicode_buffer(wintypes.MAX_PATH)
            ## CSIDL_PERSONAL = 5, SHGFP_TYPE_CURRENT = 0
            if ctypes.windll.shell32.SHGetFolderPathW(None, 5, None, 0, buffer) == 0:
                if buffer.value:
                    return buffer.value
        except Exception:
            pass
        return os.path.join(home, "Documents")
    if sys.platform == "darwin":
        return os.path.join(home, "Documents")
    ## Linux: honour the XDG documents directory when the user has one
    xdg = os.environ.get("XDG_DOCUMENTS_DIR")
    if xdg and os.path.isdir(os.path.expandvars(xdg)):
        return os.path.expandvars(xdg)
    candidate = os.path.join(home, "Documents")
    return candidate if os.path.isdir(candidate) else home


def default_output_dir():
    """Where finished packs go unless the user picks somewhere else."""
    return os.path.join(documents(), "Structura Builds")
