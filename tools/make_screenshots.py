"""Regenerate the window screenshots used by the README.

Screenshots of a program's own interface go stale the moment the interface
changes, and a stale screenshot is worse than none -- it teaches a layout that
is not there any more. These are taken from the running window instead of by
hand, so a UI change plus one command brings the documentation back in step.

    python tools/make_screenshots.py

Writes into docs/. Needs a desktop session: the window is really opened, raised
and photographed, so this cannot run headless. The in-game screenshots beside
these are the ones only a person in a world can take.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import customtkinter as ctk
from PIL import ImageGrab

import app_settings
import structura_gui

DOCS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs")

## a populated window says far more than an empty one
SAMPLE = [("north wing", "test_structures/stoneSlabs.mcstructure"),
          ("rail deck", "test_structures/rails.mcstructure"),
          ("canopy", "test_structures/tree.mcstructure")]


def settle(window, seconds=1.0):
    """Pump the event loop so Tk finishes drawing before the grab."""
    end = time.time() + seconds
    while time.time() < end:
        window.update_idletasks()
        window.update()
        time.sleep(0.02)


def shoot(window, name, chrome=36):
    """Grab a window, including the title bar above it."""
    window.deiconify()
    window.lift()
    window.attributes("-topmost", True)
    settle(window)
    x, y = window.winfo_rootx(), window.winfo_rooty()
    w, h = window.winfo_width(), window.winfo_height()
    image = ImageGrab.grab((x, y - chrome, x + w, y + h))
    path = os.path.join(DOCS, name)
    image.save(path)
    print("   %-28s %dx%d" % (name, *image.size))
    return path


def populate(app):
    ## the window opens empty now, so every row here is one this adds
    for tag, path in SAMPLE:
        app.add_structure_row(path).tag_var.set(tag)
    app.pack_name_var.set("Sorter Hall")
    app.desc_var.set("floor 3 sorter")
    app.revalidate()


def main():
    os.makedirs(DOCS, exist_ok=True)
    print("writing screenshots into docs/")
    app = structura_gui.App()
    ## the documentation is in English whatever the machine taking it is set to,
    ## and the setting is put back afterwards
    was = app_settings.settings["lang"]
    app.on_language("English")
    populate(app)
    settle(app, 0.8)

    for mode, name in (("dark", "window_dark.png"), ("light", "window_light.png")):
        ctk.set_appearance_mode(mode)
        settle(app, 0.8)
        shoot(app, name)

    ctk.set_appearance_mode("dark")
    app.big_build.set(1)
    app.on_big_build()
    settle(app, 0.5)
    shoot(app, "window_big_build.png")

    app.big_build.set(0)
    app.on_big_build()
    app.rows[-1].tag_var.set("")
    app.revalidate()
    settle(app, 0.5)
    shoot(app, "window_validation.png")

    dialog = structura_gui.ResultDialog(
        app, app.text("pack built"),
        [os.path.abspath("Sorter Hall.mcpack")], ".")
    dialog.attributes("-topmost", True)
    settle(app, 1.2)
    shoot(dialog, "pack_built.png")
    dialog.destroy()

    about = structura_gui.AboutDialog(app)
    about.attributes("-topmost", True)
    settle(app, 1.2)
    shoot(about, "about.png")
    about.destroy()

    ## one of the joke languages, so the picker's point is visible
    app.on_language("Pirate Speak")
    settle(app, 0.8)
    shoot(app, "window_pirate.png")
    app.on_language(was)

    app.destroy()
    print("done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
