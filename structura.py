"""Structura's entry point: the command line interface and the window.

Importing this module has no side effects. Everything -- reading settings,
parsing arguments, building the window -- happens inside main(). The window
itself lives in structura_gui; everything here is either the command line or the
handoff to it.
"""
import argparse
import json
import os
import sys

import app_settings
import paths
import structura_core
import updater
import version
from structura_core import structura

structura_update_version = "Structura1-7"

## This fork does not publish to the upstream update server, so the button is
## hidden. The updater, the update() handler and the --update flag all still
## work; set this to True once the fork has an update source of its own.
SHOW_UPDATE_BUTTON = False


def update():
    """Pull a fresh lookup drop from the update server."""
    updated = updater.update("https://update.structuralab.com/structuraUpdate",
                             structura_update_version, "")
    if updated and os.path.isfile(paths.lookup("lookup_version.json")):
        with open(paths.lookup("lookup_version.json"), encoding="utf-8-sig") as file:
            print(json.load(file).get("notes", ""))
    else:
        print("You are currently up to date.")


# --- command line --------------------------------------------------------

def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Structura turns .mcstructure files into Bedrock resource packs.")
    parser.add_argument("--structure", type=str, help=".mcstructure file")
    parser.add_argument("--pack_name", type=str, help="Name of pack")
    parser.add_argument("--opacity", type=int,
                        help="Opacity of the ghost blocks, 1-100 (default %d)"
                             % app_settings.DEFAULT_OPACITY)
    parser.add_argument("--description", type=str,
                        help="Short note shown in the pack list, up to %d characters"
                             % 25)
    parser.add_argument("--icon", type=str, help="Icon for pack")
    parser.add_argument("--output", type=str,
                        help="Folder to write the pack into (default: the "
                             "Structura Builds folder in your documents)")
    parser.add_argument("--offset", type=str, help="X, Y, Z")
    parser.add_argument("--overwrite", action="store_true",
                        help="Overwrite the output file.")
    parser.add_argument("--debug", "-db", action="store_true",
                        help="Enable debug mode")
    parser.add_argument("--update", action="store_true", help="Run updater")
    parser.add_argument("--tech_pack", action="store_true",
                        help="Bundle TechPack into the generated pack, so one pack "
                             "carries both. Both projects replace the armor stand "
                             "entity, so applying them separately loses one of them.")
    args = parser.parse_args(argv)
    ## half a command line used to fall through to the window, which on a
    ## headless machine fails somewhere much less obvious
    if bool(args.structure) != bool(args.pack_name):
        parser.error("--structure and --pack_name go together; give both to build "
                     "from the command line, or neither to open the window")
    return args


def run_cli(args):
    opacity = app_settings.DEFAULT_OPACITY if args.opacity is None else args.opacity
    offset = [0, 0, 0]
    if args.offset:
        offset = [int(val) for val in args.offset.split(",")]

    ## an explicit --output wins; otherwise the same folder the window uses, so
    ## a pack built either way lands in the same place
    folder = args.output or app_settings.output_dir()
    os.makedirs(folder, exist_ok=True)
    target = os.path.join(folder, args.pack_name)

    pack_file = "{}.mcpack".format(target)
    if args.overwrite and os.path.isfile(pack_file):
        os.remove(pack_file)

    structura_base = structura(target)
    structura_base.set_opacity(min(max(opacity, 1), 100) / 100)

    if args.description:
        structura_base.set_description(args.description)
    if args.tech_pack:
        structura_base.set_tech_pack(True)
    if icon := args.icon:
        structura_base.set_icon(icon)

    structura_base.add_model("", args.structure)
    structura_base.set_model_offset("", offset)
    structura_base.generate_with_nametags()
    print(structura_base.compile_pack(overwrite=args.overwrite))


def main(argv=None):
    args = parse_args(argv)
    app_settings.load()
    if args.debug:
        ## let an unsupported block raise instead of being collected into
        ## the skipped list, and turn on the lookup tracing
        structura_core.debug = True
        import armor_stand_geo_class
        armor_stand_geo_class.debug = True
    if args.update:
        update()
    if args.structure and args.pack_name:
        run_cli(args)
        return
    import structura_gui
    structura_gui.run()


if __name__ == "__main__":
    sys.exit(main())
