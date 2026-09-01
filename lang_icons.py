"""Round language badges carrying an ISO 639-1 code.

A flag is a country, and a country is not a language: Spanish is not Spain,
English is not England, and picking one flag per language tells a good part of
the world their language belongs to somebody else. The picker therefore labels
each language with its ISO 639-1 code on a plain disc, in the language's own
name alongside.

Drawn here rather than shipped as art so the badge follows the accent colour and
comes out at whatever size and scaling the window is running at.
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

## tried in order; the first that loads wins. Any sans-serif with a bold weight
## reads well at badge size, and the PIL default is the last resort.
FONT_CANDIDATES = (
    "seguisb.ttf",      # Segoe UI Semibold, Windows
    "segoeuib.ttf",     # Segoe UI Bold
    "arialbd.ttf",
    "DejaVuSans-Bold.ttf",
    "/System/Library/Fonts/SFNSDisplay.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
)

## Real languages share the app's amber. The constructed ones each get their
## own hue, so the picker shows at a glance which entries are a joke.
COLOURS = {
    "sga": (150, 108, 214),      # Enchanting: arcane violet
    "arr": (176, 58, 46),        # Pirate: deep sea-dog red
    "cat": (226, 92, 158),       # LOLCAT: hot pink
    "wil": (62, 108, 190),       # Shakespearean: royal blue
    "uen": (46, 168, 158),       # upside-down: teal
}
DEFAULT_COLOUR = (226, 168, 52)  # the app's amber, for real languages


def colour(code):
    return COLOURS.get(code, DEFAULT_COLOUR)


_font_cache = {}


def _font(size):
    if size in _font_cache:
        return _font_cache[size]
    font = None
    for name in FONT_CANDIDATES:
        try:
            font = ImageFont.truetype(name, size)
            break
        except (OSError, IOError):
            continue
    if font is None:
        font = ImageFont.load_default()
    _font_cache[size] = font
    return font


def badge(code, size=22, fill=None, text=(20, 24, 30), scale=4):
    """A filled disc with `code` on it, as an RGBA image `size` px square.

    Drawn at `scale` times the requested size and reduced, because a circle
    rasterised straight to 22 px has visibly stepped edges. Codes can be two or
    three characters -- Cebuano has no two letter code, and the constructed
    languages use three letter tags -- so the type shrinks to fit rather than
    the label being cut short.
    """
    if fill is None:
        fill = colour(code)
    big = size * scale
    img = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse((0, 0, big - 1, big - 1), fill=tuple(fill) + (255,))

    label = (code or "?").upper()[:3]
    font = _font(int(big * (0.52 if len(label) < 3 else 0.38)))
    left, top, right, bottom = draw.textbbox((0, 0), label, font=font)
    draw.text(((big - (right + left)) / 2, (big - (bottom + top)) / 2),
              label, font=font, fill=tuple(text) + (255,))
    return img.resize((size, size), Image.LANCZOS)


def pair(code, size=22, light=None, dark=None,
         light_text=(255, 255, 255), dark_text=(20, 24, 30)):
    """(light mode image, dark mode image) for one language code."""
    base = colour(code)
    return (badge(code, size, light or base, light_text),
            badge(code, size, dark or base, dark_text))


if __name__ == "__main__":
    import lang_parse
    out = os.path.dirname(os.path.abspath(__file__))
    sheet = Image.new("RGBA", (5 * 48, 48), (60, 60, 60, 255))
    for i, name in enumerate(lang_parse.CODES):
        sheet.alpha_composite(badge(lang_parse.code(name), 40), (i * 48 + 4, 4))
    path = os.path.join(out, "lang_badges_preview.png")
    sheet.save(path)
    print("wrote", path)
    sys.exit(0)
