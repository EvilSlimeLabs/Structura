"""Dye the banner sheet, once per colour, so a banner is drawn in its own.

    python tools/make_banner_textures.py

A banner's colour is not in its block states. It is in the block entity beside
the block, as `Base`, a number from 0 to 15 in the same order as wool, and the
game draws it by tinting one white sheet at run time. A ghost block cannot tint
anything, so the tinting is done here instead: sixteen copies of
`banner_base.tga`, each multiplied by its dye, written into the vanilla pack as
`textures/entity/banner/banner_<colour>.png`.

The dyes are read out of the pack's own wool textures rather than written down
here, so they are the colours this pack actually uses.

**Patterns are not drawn.** A banner may carry six of them, each with a colour
of its own, which is more combinations than could ever be written to disk: they
would have to be composited while a pack is built, and the texture atlas takes
files rather than pictures. What is here is the base colour.

Re-run `tools/make_container_forms.py` after this if the list of colours
changes. Nothing here is needed at run time.
"""
import os
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

PACK = os.path.join(ROOT, "structura", "Vanilla_Resource_Pack")
BLOCKS = os.path.join(PACK, "textures", "blocks")
BANNERS = os.path.join(PACK, "textures", "entity", "banner")
BASE = os.path.join(BANNERS, "banner_base.tga")

## Bedrock's dye order, which `Base` counts in and which `variants.json` already
## keys wool and every other dyed block by
COLOURS = ["white", "orange", "magenta", "light_blue", "yellow", "lime", "pink",
           "gray", "silver", "cyan", "purple", "blue", "brown", "green", "red",
           "black"]


def dye(colour):
    """The colour this pack paints that wool, as the average of its texture."""
    wool = Image.open(
        os.path.join(BLOCKS, "wool_colored_%s.png" % colour)).convert("RGB")
    bands = wool.split()
    return tuple(int(round(band.resize((1, 1), Image.BOX).getpixel((0, 0))))
                 for band in bands)


def tint(sheet, colour):
    """The sheet multiplied by a dye, the way the game tints it."""
    out = sheet.copy()
    red, green, blue, alpha = out.split()
    scale = dye(colour)
    red = red.point(lambda v: v * scale[0] // 255)
    green = green.point(lambda v: v * scale[1] // 255)
    blue = blue.point(lambda v: v * scale[2] // 255)
    return Image.merge("RGBA", (red, green, blue, alpha))


def main():
    if not os.path.isfile(BASE):
        raise SystemExit(
            "No %s. Copy it out of the community submodule first." % BASE)
    sheet = Image.open(BASE).convert("RGBA")
    print("dyeing %s, %dx%d" % (os.path.basename(BASE), *sheet.size))
    for index, colour in enumerate(COLOURS):
        made = tint(sheet, colour)
        path = os.path.join(BANNERS, "banner_%s.png" % colour)
        made.save(path)
        print("   %2d %-12s %s" % (index, colour, os.path.basename(path)))


if __name__ == "__main__":
    main()
