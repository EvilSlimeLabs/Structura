"""Command line entry point, with no window in it at all.

`structura.py` opens the window when it is given no arguments, which means the
frozen build has to carry CustomTkinter, the drop target library and the fonts
whether or not anybody opens a window. This entry point exists so a second,
much smaller executable can be built for scripts, servers and batch jobs: it
imports the pipeline and the argument parser and nothing else, and the spec that
freezes it excludes the interface outright.

Everything it accepts is what `structura.py --help` lists; the only difference is
that a run with no structure is an error here rather than an invitation to open
a window.
"""
import sys

import structura


def main(argv=None):
    args = structura.parse_args(argv)
    if not (args.structure and args.pack_name):
        if args.update:
            structura.update()
            return 0
        sys.stderr.write(
            "This is the command line build of Structura; it has no window.\n"
            "Give it something to build:\n\n"
            "  Structura-cli --structure build.mcstructure --pack_name \"My Pack\"\n\n"
            "Run with --help for everything it accepts.\n")
        return 2

    if args.debug:
        import structura_core
        import armor_stand_geo_class
        structura_core.debug = True
        armor_stand_geo_class.debug = True
    if args.update:
        structura.update()
    structura.run_cli(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
