"""Downloads a lookup-table drop from the update server and unpacks it.

The archive is written over a live installation, so extraction is restricted to
the two data directories an update is allowed to replace. Anything else in the
archive is reported and skipped rather than trusted.
"""
import os
import posixpath
from zipfile import ZipFile

import requests

## The only directories an update may write into, relative to the working
## directory. Keep this in step with DATA_DIRS in build.py, which is what
## produces the archive.
UPDATABLE_DIRS = ("lookups", "Vanilla_Resource_Pack")

TEMP_ARCHIVE = "lookup_temp.zip"


def _permitted(archive):
    """Members that land inside one of UPDATABLE_DIRS, with the rest reported."""
    allowed = []
    for member in archive.infolist():
        if member.is_dir():
            continue
        name = member.filename.replace("\\", "/")
        target = posixpath.normpath(name)
        if posixpath.isabs(target) or target.startswith("../") or target == "..":
            print("update: skipping {}, it points outside the install".format(name))
            continue
        if target.split("/")[0] not in UPDATABLE_DIRS:
            print("update: skipping {}, not in {}".format(name, " or ".join(UPDATABLE_DIRS)))
            continue
        allowed.append(member)
    return allowed


def update(url, structura_version, lookup_verison):
    initial_check = requests.get(
        url,
        headers={"structuraVersion": structura_version, "lookupVersion": lookup_verison},
    ).json()
    updated = False
    if initial_check["info"] != 'Update Availible':
        print("up to date")
        return updated

    response = requests.get(initial_check["url"], allow_redirects=True, stream=True)
    if response.headers.get('content-type') == "application/xml":
        ## the bucket answers with an XML error document rather than a 4xx
        print(response.content)
        return updated

    with open(TEMP_ARCHIVE, "wb") as file:
        file.write(response.content)
    try:
        with ZipFile(TEMP_ARCHIVE, 'r') as archive:
            members = _permitted(archive)
            if not members:
                print("update: the archive held nothing this program may replace")
                return updated
            archive.extractall(path=".", members=members)
        updated = True
    finally:
        os.remove(TEMP_ARCHIVE)
    return updated


if __name__ == "__main__":
    update("https://update.structuralab.com/structuraUpdate",
           "Structura1-7",
           "none")
