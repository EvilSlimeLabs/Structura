"""Small interface glyphs, drawn rather than shipped.

Two reasons they are drawn here. They follow the accent colour, so changing the
palette changes them; and they come out at whatever size the window is running
at rather than being a fixed-size PNG that goes soft on a scaled display.

Everything is drawn at several times the requested size and reduced, because a
diagonal or a rounded corner rasterised straight to 16 px has visibly stepped
edges.
"""
from PIL import Image, ImageDraw

SCALE = 4


def _canvas(size):
    big = size * SCALE
    image = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    return image, ImageDraw.Draw(image), big


def folder(size=16, colour=(200, 137, 28)):
    """A folder, for the controls that open a file or directory chooser."""
    image, draw, big = _canvas(size)
    fill = tuple(colour) + (255,)
    unit = big / 16.0

    ## the raised tab along the back edge
    draw.rounded_rectangle((unit * 1, unit * 3, unit * 7, unit * 6),
                           radius=unit * 0.9, fill=fill)
    ## the body
    draw.rounded_rectangle((unit * 1, unit * 4.6, unit * 15, unit * 13),
                           radius=unit * 1.4, fill=fill)
    ## a lighter front flap, so the shape reads as a folder and not a box
    lighter = tuple(min(255, int(c * 1.25)) for c in colour) + (255,)
    draw.rounded_rectangle((unit * 1, unit * 6.6, unit * 15, unit * 13),
                           radius=unit * 1.4, fill=lighter)
    return image.resize((size, size), Image.LANCZOS)


def cross(size=16, colour=(139, 148, 163), weight=1.6):
    """A plain ✕, for clearing a choice."""
    image, draw, big = _canvas(size)
    fill = tuple(colour) + (255,)
    unit = big / 16.0
    pad = unit * 4
    width = int(unit * weight)
    draw.line((pad, pad, big - pad, big - pad), fill=fill, width=width)
    draw.line((big - pad, pad, pad, big - pad), fill=fill, width=width)
    return image.resize((size, size), Image.LANCZOS)


def corner(size=16, colour=(200, 137, 28), weight=1.6):
    """Two edges meeting: the corner a big build is measured from."""
    image, draw, big = _canvas(size)
    fill = tuple(colour) + (255,)
    unit = big / 16.0
    width = int(unit * weight)
    draw.line((unit * 3, unit * 3, unit * 3, unit * 13), fill=fill, width=width)
    draw.line((unit * 3, unit * 13, unit * 13, unit * 13), fill=fill, width=width)
    draw.ellipse((unit * 1.6, unit * 1.6, unit * 4.4, unit * 4.4), fill=fill)
    return image.resize((size, size), Image.LANCZOS)


if __name__ == "__main__":
    sheet = Image.new("RGBA", (3 * 56, 56), (48, 50, 56, 255))
    for i, glyph in enumerate((folder(40), cross(40), corner(40))):
        sheet.alpha_composite(glyph, (i * 56 + 8, 8))
    sheet.resize((sheet.width * 2, sheet.height * 2), Image.NEAREST).save("ui_icons_preview.png")
    print("wrote ui_icons_preview.png")
