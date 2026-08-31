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


def pack_uuids(pack_name):
    """The header and module UUIDs for a pack, stable across rebuilds."""
    return (str(uuid.uuid5(STRUCTURA_NAMESPACE, pack_name)),
            str(uuid.uuid5(STRUCTURA_NAMESPACE, pack_name + "/resources")))


def export(work_dir, pack_name, nameTags=()):
    description = "Structura block overlay pack, created by  §o§5DrAv0011§r, §o§9 FondUnicycle§r and§o§5 RavinMaddHatter§r"
    if len(nameTags) > 0:
        description = f"Nametags: {', '.join(nameTags)}. {description}"
    ## pack_name is what the player sees and what the UUID is derived from;
    ## work_dir is wherever the tree happens to be assembled
    tempname = pack_name.split("/")[-1]
    header_uuid, module_uuid = pack_uuids(tempname)
    ## the generated pack carries the version of the Structura that built it, so
    ## a rebuild after an upgrade reads as an update rather than a sidegrade
    pack_version = version.as_tuple()
    manifest = {
        "format_version": 2,
        "header": {
            "name": tempname,
            "description": description,
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

    with open(path_to_ani, "w+") as json_file:
        json.dump(manifest, json_file, indent=2)
