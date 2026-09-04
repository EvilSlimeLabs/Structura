"""Whether a newer Structura has been released, and putting it in place.

Structura ships as one executable, so an update is one file: the new build
takes the place of the running one and the program restarts into it.

**A running executable cannot be written over on Windows, but it can be moved.**
That is what makes this work, and it is the whole shape of `install`. The
download lands beside the running file under another name and is checked there,
where nothing is at stake; only once it has been shown to run is the running
file renamed out of the way and the new one put where it stood.

**Nothing touches the running build until the new one has answered for itself.**
The download has to match the SHA-256 the release publishes for it, in a
`SHA256SUMS.txt` asset `build.py` writes; then it has to look like a program;
then it has to run. A release with no fingerprints for its assets is refused
rather than taken on trust, and a download that fails any of the three is thrown
away with the running program untouched.

**The fingerprint is not a signature.** It is fetched from the same release as
the build it describes, over the same connection, so it proves the file arrived
whole and unaltered, not that the release is the project's own work. Signing
would need a certificate and a key kept somewhere neither of those things is.

After the swap the displaced build is still on disk, because a file a live
process is running from can be renamed but not deleted. It is hidden, and the
next launch takes it away. Should the new build ever fail to start, renaming
that file back is the way home.

Releases come from the project's own GitHub releases, over HTTPS, and the asset
taken is the one named after the running executable, so the windowed build
replaces itself and the console build replaces itself. **The download is not
signed.** What it rests on is the transport and the repository, not a signature,
and anyone building their own release should know that.

Nothing here runs unless asked: `settings` decides whether the launch asks, and
the window's About dialog asks on demand.
"""
import hashlib
import hmac
import http.client
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

from structura import paths
from structura import version

REPOSITORY = "EvilSlimeLabs/Structura"
LATEST = "https://api.github.com/repos/%s/releases/latest" % REPOSITORY
RELEASES = "https://github.com/%s/releases" % REPOSITORY

## GitHub asks for a user agent and answers 403 without one
AGENT = "Structura/%s" % version.read()
TIMEOUT = 10

## what the two working files are called, beside the executable itself
DISPLACED = ".old"
INCOMING = ".new"

## the release asset holding a SHA-256 for every other asset, written by
## build.py in sha256sum's own format so it also checks a hand download
SUMS = "SHA256SUMS.txt"

## How long to keep retrying a file operation something else is holding up, and
## how often. Windows refuses to rename or replace a file another process has
## open, and an antivirus opens a freshly written executable to scan it. The
## scan is over in moments, so asking again is all that is needed.
PATIENCE = 5.0
STEP = 0.25

## How long the downloaded build gets to answer for itself. A single file build
## unpacks tens of megabytes before it runs at all, and does it slower on the
## machine where an antivirus is watching, which is the machine this matters on.
PROBE = 180

## CREATE_NO_WINDOW, so testing the console build does not flash one up
NO_WINDOW = 0x08000000

FILE_HIDDEN = 0x02
BAD_ATTRIBUTES = 0xFFFFFFFF


def as_numbers(tag):
    """A release tag as numbers to compare: `v3.1.0` and `3.1` both work.

    A part is read up to its first non-digit and no further, so `3.1.0-rc2` is
    three, one, nothing: a release candidate of a version is that version, not
    a later one. Taking every digit out of the part instead would read it as
    3.1.2 and offer everybody an update to a candidate of what they have.
    """
    digits = []
    for part in str(tag or "").lstrip("vV").split("."):
        kept = ""
        for character in part:
            if not character.isdigit():
                break
            kept += character
        if not kept:
            break
        digits.append(int(kept))
    return tuple(digits + [0, 0, 0])[:3]


def newer(tag, running=None):
    """Whether a release tag names a version after the one running."""
    running = as_numbers(running or version.read())
    return as_numbers(tag) > running


def running_file():
    """The executable to replace, or None when running from a checkout.

    A checkout has no single file to swap: the program is a folder of source
    and the thing on disk that would have to change is the interpreter.
    """
    return sys.executable if paths.frozen() else None


def keep_trying(call, patience=PATIENCE):
    """Run a file operation, retrying while something else holds the file.

    Raises whatever the operation raised once the patience is spent, so the
    caller still gets the real complaint rather than a timeout of its own.
    """
    deadline = time.monotonic() + patience
    while True:
        try:
            return call()
        except OSError:
            if time.monotonic() >= deadline:
                raise
            time.sleep(STEP)


def discard(path, patience=PATIENCE):
    """Remove a working file that is in the way, and say if it went."""
    if not os.path.exists(path):
        return True
    try:
        keep_trying(lambda: os.remove(path), patience)
        return True
    except OSError:
        return False


def hide(path):
    """Keep the displaced build out of the folder the person looks at.

    It has to stay beside the executable, because the swap is a rename and a
    rename only works within one volume, so the only way for it not to be in
    the way is for it not to be shown. The attribute travels with the file
    through a rename, so nothing that will be renamed back may wear it.
    """
    if not sys.platform.startswith("win"):
        return False
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        were = kernel32.GetFileAttributesW(str(path))
        if were == BAD_ATTRIBUTES:
            return False
        return bool(kernel32.SetFileAttributesW(str(path), were | FILE_HIDDEN))
    except (OSError, AttributeError, ValueError):
        return False


def clear_displaced(patience=0.0):
    """Delete the executable a previous update moved aside, if it is there.

    Called at launch, because the file cannot be deleted while the process that
    was running from it is alive. A build an update has just started races the
    build it replaced, which is still shutting down, so `patience` says how many
    seconds to keep asking. Failing is not a problem worth reporting: the file
    is a leftover, the next launch tries again, and while it is there it is what
    a broken update would be recovered from.
    """
    running = running_file()
    if not running:
        return False
    displaced = running + DISPLACED
    if not os.path.isfile(displaced):
        return False
    return discard(displaced, patience)


def _read(url):
    request = urllib.request.Request(url, headers={
        "User-Agent": AGENT, "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(request, timeout=TIMEOUT) as answer:
        return answer.read()


def latest():
    """The newest release, as (tag, {asset name: url}), or None.

    None for every way of failing: no network, a repository that is private or
    has no releases yet, a rate limit, an answer that is not what was expected.
    An update check is not a thing to interrupt anybody over.
    """
    try:
        body = json.loads(_read(LATEST).decode("utf-8"))
    except (urllib.error.URLError, http.client.HTTPException, ValueError,
            OSError, TimeoutError):
        return None
    tag = body.get("tag_name")
    if not tag:
        return None
    assets = {a.get("name"): a.get("browser_download_url")
              for a in body.get("assets", []) if a.get("name")}
    return tag, assets


def available():
    """The tag of a release worth taking, or None.

    Only a frozen build can replace itself, and only when the release carries a
    file named the way the running one is.
    """
    running = running_file()
    if not running:
        return None
    found = latest()
    if not found:
        return None
    tag, assets = found
    if not newer(tag):
        return None
    return tag if os.path.basename(running) in assets else None


def fingerprints(url):
    """The SHA-256 a release declares for each of its assets, by name.

    The file is what `sha256sum` itself writes, one `<digest>  <name>` to a
    line, with a `*` before the name when it was read in binary mode. Anything
    else in there is ignored rather than argued with.
    """
    try:
        body = _read(url).decode("utf-8", "replace")
    except (urllib.error.URLError, http.client.HTTPException, OSError,
            TimeoutError):
        return None
    found = {}
    for line in body.splitlines():
        parts = line.strip().split(None, 1)
        if len(parts) == 2 and len(parts[0]) == 64:
            found[parts[1].strip().lstrip("*")] = parts[0].lower()
    return found


def download(url, into):
    """Fetch a release asset beside the executable it will replace, and say
    what its SHA-256 is.

    Beside it on purpose: the swap is a rename, and a rename is only safe and
    quick within one volume. The digest is taken as the file goes past, because
    reading tens of megabytes back to hash them is work for nothing.

    What arrived is also measured against the length the server declared, since
    a connection that drops mid-file ends the read without an error of any kind
    and leaves a plausible-looking part of a build.
    """
    request = urllib.request.Request(url, headers={"User-Agent": AGENT})
    fingerprint = hashlib.sha256()
    with urllib.request.urlopen(request, timeout=TIMEOUT * 6) as answer:
        declared = answer.headers.get("Content-Length")
        arrived = 0
        with open(into, "wb") as file:
            while True:
                block = answer.read(65536)
                if not block:
                    break
                file.write(block)
                fingerprint.update(block)
                arrived += len(block)
    try:
        expected = int(declared)
    except (TypeError, ValueError):
        expected = None
    if expected is not None and arrived != expected:
        raise OSError("%d bytes of %d arrived" % (arrived, expected))
    return fingerprint.hexdigest()


## Below this a download is an error page rather than a build. A rate limit
## answers in a few hundred bytes and a Structura build is tens of megabytes, so
## the line can sit low and still never be argued with.
SMALLEST = 64 * 1024


def looks_like_a_program(path):
    """Whether what was downloaded is an executable at all.

    The cheap half of checking a download, and what catches the rate limit page
    without starting anything.
    """
    try:
        if os.path.getsize(path) < SMALLEST:
            return False
        with open(path, "rb") as file:
            start = file.read(4)
    except OSError:
        return False
    if sys.platform.startswith("win"):
        return start[:2] == b"MZ"
    return start[:4] == b"\x7fELF" or start[:2] == b"#!"


def answers_for_itself(path, timeout=PROBE):
    """Whether a downloaded build actually runs, by asking it for its help.

    Both builds answer `--help` and stop, the windowed one included, so this
    exercises the whole file: the loader reads the executable, the single file
    archive unpacks, Python starts, and the argument parser answers. What it
    prints does not matter. That it started and stopped saying nothing was
    wrong is the whole of the question.

    The path must be absolute. Windows searches for a bare name and appends
    `.exe` while doing so, which would never find a file named `.new`.
    """
    extra = {"creationflags": NO_WINDOW} if sys.platform.startswith("win") else {}
    try:
        done = subprocess.run([os.path.abspath(path), "--help"],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              timeout=timeout, **extra)
    except (OSError, subprocess.SubprocessError):
        return False
    return done.returncode == 0


def install_latest(restart=True, report=None):
    """Take the newest release, whatever it turns out to be called.

    One look at the release answers both questions the install has: which asset
    is the build this program replaces itself with, and what that asset is meant
    to hash to. Refusing a release that publishes no fingerprints is the point
    of having them.
    """
    running = running_file()
    if not running:
        return "update source", ""
    found = latest()
    if not found:
        return "update no release", ""

    name = os.path.basename(running)
    assets = found[1]
    if name not in assets:
        return "update no asset", ""
    if SUMS not in assets:
        return "update no fingerprint", SUMS
    declared = fingerprints(assets[SUMS]) or {}
    if name not in declared:
        return "update no fingerprint", SUMS
    return install(assets[name], declared[name], restart=restart, report=report)


def install(url, expected, restart=True, report=None):
    """Put a downloaded release in place of the running one.

    `expected` is the SHA-256 the release publishes for this asset, and is not
    optional: a build that cannot be checked is not installed.

    Returns None when it worked, and otherwise a (reason, detail) pair: the
    reason names one of the ways this goes wrong, for the caller to put in its
    own words, and the detail is whatever the system said, or an empty string.

    `report` is called with the name of each stage as it begins. Checking the
    download means starting it, which takes as long as starting Structura, so
    something has to be able to say that is what the wait is.
    """
    def say(stage):
        if report:
            report(stage)

    running = running_file()
    if not running:
        return "update source", ""

    incoming = running + INCOMING
    displaced = running + DISPLACED

    ## Nothing below here touches the running program until the swap, so every
    ## way of giving up before then leaves the person exactly where they were.
    say("update stage downloading")
    try:
        arrived = download(url, incoming)
    except (urllib.error.URLError, http.client.HTTPException, OSError,
            TimeoutError) as complaint:
        ## HTTPException is in there because http.client raises IncompleteRead
        ## rather than an OSError, and it is not a crash, it is a bad download
        discard(incoming)
        return "update download failed", str(complaint)
    ## the fingerprint first, because it is the strongest of the three checks
    ## and the cheapest, and failing it makes the other two beside the point
    if not hmac.compare_digest(arrived, str(expected).strip().lower()):
        discard(incoming)
        return "update wrong fingerprint", ""
    if not looks_like_a_program(incoming):
        discard(incoming)
        return "update not a build", ""
    say("update stage checking")
    if not answers_for_itself(incoming):
        discard(incoming)
        return "update does not run", ""

    say("update stage placing")
    try:
        ## the running file cannot be written over, but it can be moved
        if not discard(displaced):
            raise OSError("%s is in use" % os.path.basename(displaced))
        keep_trying(lambda: os.replace(running, displaced))
    except OSError as complaint:
        discard(incoming)
        return "update cannot move", str(complaint)

    try:
        keep_trying(lambda: os.replace(incoming, running))
    except OSError as complaint:
        try:
            ## put the old one back rather than leaving nothing to run
            keep_trying(lambda: os.replace(displaced, running))
        except OSError:
            return "update stranded", os.path.basename(displaced)
        discard(incoming)
        return "update cannot place", str(complaint)

    ## only now, because the attribute would have followed it back
    hide(displaced)

    if restart:
        try:
            subprocess.Popen([running], close_fds=True)
        except OSError:
            ## it is installed either way; the person can start it themselves
            pass
    return None
