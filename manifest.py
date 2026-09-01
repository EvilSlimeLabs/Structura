import json
import os
import uuid

import version

## Fixed namespace for uuid5. The header UUID is a pack's identity to Minecraft:
## a random one on every build makes each regenerated pack a brand new pack, so
## the old copy stays in the player's list and any world already using it keeps
## the stale content. Deriving the UUID from the pack name instead means a
## rebuild replaces the pack in place. The trade-off is that two people who both
## name a pack the same thing produce the same UUID and cannot hold both at
## once, which is the accepted cost of an updatable pack.
STRUCTURA_NAMESPACE = uuid.UUID("a833ff26-366d-4a32-91b4-3b307ff291e4")

## Shown in front of the pack's own name in the player's pack list, so every
## pack this program builds groups together there.
NAME_PREFIX = "Structura: "

## What Structura is, in the one line the pack list gives us.
TAGLINE = "block overlay pack"

## Minecraft formatting codes. The pack list renders these, so the credits keep
## the colours each author has carried since they were added.
GREEN = "§a"          # slime green, for EvilSlimeLabs
ITALIC_PURPLE = "§o§5"
ITALIC_BLUE = "§o§9"
RESET = "§r"

MAINTAINER = "EvilSlimeLabs"
PAST_AUTHORS = ((ITALIC_PURPLE, "DrAv0011"),
                (ITALIC_BLUE, "FondUnicycle"),
                (ITALIC_PURPLE, "RavinMaddHatter"))

## A pack description is one field, and Minecraft wraps it; newlines are what
## separate the parts a reader wants to pick out at a glance.
DESCRIPTION_LIMIT = 25


def pack_uuids(pack_name):
    """The header and module UUIDs for a pack, stable across rebuilds.

    Derived from the name the user typed, never from the displayed name. The
    prefix is presentation, and folding it into the UUID would have made every
    pack built by an older Structura look like a different pack to the game.
    """
    return (str(uuid.uuid5(STRUCTURA_NAMESPACE, pack_name)),
            str(uuid.uuid5(STRUCTURA_NAMESPACE, pack_name + "/resources")))


def display_name(pack_name):
    """What the player sees in the pack list."""
    if pack_name.startswith(NAME_PREFIX):
        return pack_name
    return NAME_PREFIX + pack_name


def credits_line():
    """Who built the program, in the colours each author is known by."""
    names = [GREEN + MAINTAINER + RESET]
    names += [colour + name + RESET for colour, name in PAST_AUTHORS]
    return "Structura {}, {}, by {}".format(version.read(), TAGLINE, ", ".join(names))


def build_description(nameTags=(), user_text="", tech_pack_version=None):
    """The pack description, one part per line.

    Ordered by how much it belongs to the person who built the pack: their own
    note first, then what is in the pack, then what made it.
    """
    lines = []
    if user_text:
        lines.append(user_text.strip()[:DESCRIPTION_LIMIT])
    if nameTags:
        lines.append("Nametags: {}".format(", ".join(nameTags)))
    if tech_pack_version:
        lines.append("TechPack {} included".format(tech_pack_version))
    lines.append(credits_line())
    return "\n".join(lines)


def export(work_dir, pack_name, nameTags=(), user_text="", tech_pack_version=None):
    ## pack_name is what the UUID is derived from; work_dir is wherever the tree
    ## happens to be assembled
    tempname = pack_name.split("/")[-1]
    header_uuid, module_uuid = pack_uuids(tempname)
    ## the generated pack carries the version of the Structura that built it, so
    ## a rebuild after an upgrade reads as an update rather than a sidegrade
    pack_version = version.as_tuple()
    manifest = {
        "format_version": 2,
        "header": {
            "name": display_name(tempname),
            "description": build_description(nameTags, user_text, tech_pack_version),
            "uuid": header_uuid,
            "version": pack_version,
            "min_engine_version": [
                1,
                16,
                0
            ]
        },
        "modules": [
            {
                "type": "resources",
                "uuid": module_uuid,
                "version": pack_version
            }
        ]
    }

    path_to_ani = "{}/manifest.json".format(work_dir)
    os.makedirs(os.path.dirname(path_to_ani), exist_ok=True)

    with open(path_to_ani, "w+", encoding="utf-8") as json_file:
        json.dump(manifest, json_file, indent=2, ensure_ascii=False)
