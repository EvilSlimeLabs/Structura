"""Where Structura's data lives, in a checkout and inside a frozen build.

Up to 3.0 the executable shipped with `lookups/` and `Vanilla_Resource_Pack/`
sitting beside it, so the program could open them by relative path and a user
had to keep the extracted folder together. The release is now a single
self-contained executable: those directories are packed inside it and unpacked
to a private temporary folder that PyInstaller points `sys._MEIPASS` at.

Everything still resolves through here, and a copy **beside the executable still
wins**. That is deliberate and load-bearing:

  * the updater writes lookup drops next to the executable, and a bundle is read
    only -- without this the update path would have nowhere to put anything
  * anyone hand-editing a lookup table to add a block can drop the folder beside
    the exe and have it take effect, which is what `docs/Editing Blocks.md`
    describes

So the search order is: beside the executable, then inside the bundle, then the
source checkout, then the working directory.
"""
import os
import sys

## the directories that make up Structura's data
DATA_DIRS = ("lookups", "Vanilla_Resource_Pack")

_HERE = os.path.dirname(os.path.abspath(__file__))


def frozen():
    return getattr(sys, "frozen", False)


def beside_executable():
    """The folder the executable itself sits in, or the checkout when running
    from source. This is the writable one."""
    if frozen():
        return os.path.dirname(sys.executable)
    return _HERE


def bundled():
    """The folder PyInstaller unpacked the bundle into, if there is one."""
    return getattr(sys, "_MEIPASS", None)


def roots():
    """Every place data might be, best first."""
    found = [beside_executable()]
    inside = bundled()
    if inside:
        found.append(inside)
    for extra in (_HERE, os.getcwd()):
        if extra not in found:
            found.append(extra)
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
