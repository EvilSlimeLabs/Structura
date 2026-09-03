"""Structura's command line, with no window in the build at all.

`structura/__main__.py` opens the window when it is given nothing to do, which
means the build made from it has to carry CustomTkinter, the drop target library
and the bundled fonts whether or not anybody opens a window. This entry point
exists so a second, much smaller executable can be built for scripts, servers
and batch jobs: the spec that freezes it excludes the interface outright.

It accepts exactly what `structura --help` lists. The only difference is what
happens when there is nothing to do: this one says so and stops.

    python -m structura.cli --structure build.mcstructure --pack_name "My Pack"

Installed with pip, the same thing is the `structura-cli` command.
"""
import sys

from structura.cli import console_entry

if __name__ == "__main__":
    sys.exit(console_entry())
