import os
import re
import unittest

from structura import settings
from structura import lang_parse
def open_window():
    """A fresh App, or a skip when there is no display to put one on.

    The drawn glyphs and the fonts are cached at module level and belong to the
    Tk root that was alive when they were made, so a second window in the same
    process finds the first one's images and cannot use them. Tests get a clean
    slate rather than the leftovers of whichever test ran first.
    """
    from structura.ui import structura_gui

    structura_gui._image_cache.clear()
    del structura_gui._fonts[:]
    try:
        return structura_gui.App()
    except Exception as complaint:
        raise unittest.SkipTest("no window: %s" % complaint)

def settle(app, passes=6):
    """Let the window actually lay itself out.

    update_idletasks alone leaves some widgets at their unplaced size, which
    reads as a zero height rather than as an error.
    """
    for _ in range(passes):
        app.update()

class TransparencyTests(unittest.TestCase):
    """The slider is transparency; everything downstream wants alpha."""

    def test_the_ends_of_the_slider(self):
        self.assertEqual(settings.transparency_to_alpha(0), 1.0)
        self.assertAlmostEqual(settings.transparency_to_alpha(100), 0.0)

    def test_the_default_is_the_same_number_everywhere(self):
        # the window, the CLI's --opacity and the core's own default all have to
        # land on the same ghost block, or a pack built one way looks different
        # from the same pack built another
        from structura.pack import armor_stand_geo_class as asgc

        alpha = settings.transparency_to_alpha(settings.DEFAULT_TRANSPARENCY)
        self.assertAlmostEqual(alpha, asgc.DEFAULT_ALPHA)
        self.assertAlmostEqual(settings.DEFAULT_OPACITY / 100, alpha)

    def test_the_slider_never_reaches_fully_invisible(self):
        self.assertLess(settings.MAX_TRANSPARENCY, 100)


class LanguageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        settings.langs = settings.read_languages()

    def test_every_language_has_a_code_for_its_badge(self):
        # the picker labels languages by code, not by flag: a flag is a country,
        # and several countries share a language. Two letters where ISO 639-1
        # has one, three where it does not: Cebuano, and the constructed
        # languages, which are not real languages and have no code at all.
        for name in settings.langs:
            code = lang_parse.code(name)
            self.assertRegex(code, r"^[a-z]{2,3}$", "%s has no usable code" % name)

    def test_every_language_has_colours_and_they_differ_by_language(self):
        from structura.ui import lang_icons

        seen = {}
        for name in settings.choices():
            code = lang_parse.code(name)
            palette = lang_icons.colour(code)
            self.assertTrue(1 <= len(palette) <= 3,
                            "%s has %d colours" % (name, len(palette)))
            for rgb in palette:
                self.assertEqual(len(rgb), 3)
            seen[name] = palette
        # a badge that looks like every other badge is not identifying anything
        self.assertGreater(len(set(map(str, seen.values()))), len(seen) // 2)

    def test_the_constructed_languages_are_listed_and_come_last(self):
        offered = settings.choices()
        fake = [n for n in offered if lang_parse.constructed(n)]
        self.assertTrue(fake)
        # they sit together at the end, so nobody hunting a real language has
        # to scroll past them
        self.assertEqual(offered[-len(fake):], fake)
        from structura.ui import lang_icons

        for name in fake:
            self.assertIn(lang_parse.code(name), lang_icons.colours(),
                          "%s has no entry in the colour table" % name)

    def test_an_unlisted_language_falls_back_to_the_default_colour(self):
        from structura.ui import lang_icons

        table = lang_icons.colours()
        self.assertIn(lang_icons.DEFAULT_KEY, table)
        expected = [tuple(int(c.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
                    for c in table[lang_icons.DEFAULT_KEY][:3]]
        self.assertEqual(lang_icons.colour("zzz"), expected)

    def test_english_fills_gaps_in_another_language(self):
        strings = settings.language("Español")
        english = settings.langs["English"]
        self.assertEqual(set(strings), set(english))
        self.assertTrue(all(strings.values()))

    def test_the_placeholder_column_is_not_offered(self):
        self.assertNotIn("Test", settings.choices())
        self.assertIn("English", settings.choices())

    def test_an_unknown_language_falls_back_rather_than_raising(self):
        strings = settings.language("Klingon")
        self.assertEqual(strings, settings.langs["English"])


class StringCoverageTests(unittest.TestCase):
    """Every label the window asks for has to exist in the table.

    A missing key would put the raw lookup name on screen rather than a word,
    and nothing else would complain about it.
    """

    def test_every_key_the_window_uses_is_in_langs_csv(self):
        with open(os.path.join("structura", "ui", "structura_gui.py"),
                  encoding="utf-8") as f:
            source = f.read()
        keys = set(re.findall(r'(?:self\.)?text\(\s*"([^"]+)"', source))
        keys |= set(re.findall(r'app\.text\(\s*"([^"]+)"', source))
        english = lang_parse.parse()["English"]
        # themes are looked up by their stored name
        keys |= set(settings.THEMES)
        # a key built by interpolation cannot be read out of the source; the
        # concrete forms are asserted separately below
        keys = {k for k in keys if "%" not in k}
        missing = sorted(k for k in keys if k not in english)
        self.assertEqual(missing, [], "strings used by the window but not translated")

    def test_the_interpolated_keys_exist_in_every_form(self):
        english = lang_parse.parse()["English"]
        for axis in "xyz":
            self.assertIn("axis %s" % axis, english)

    def test_no_language_column_is_missing_rows(self):
        table = lang_parse.parse()
        english = set(table["English"])
        for name, strings in table.items():
            self.assertEqual(set(strings), english,
                             "%s has a different set of rows" % name)


class ThemeTests(unittest.TestCase):
    def test_system_is_the_default_and_dark_is_the_fallback(self):
        self.assertEqual(settings.DEFAULT_THEME, "system")
        self.assertEqual(settings.FALLBACK_THEME, "dark")
        self.assertIn(settings.FALLBACK_THEME, settings.THEMES)

    def test_an_undetectable_desktop_resolves_to_dark(self):
        from structura.ui import structura_gui

        real = structura_gui.darkdetect
        try:
            structura_gui.darkdetect = None
            self.assertEqual(structura_gui.resolve_theme("system"), "dark")
            self.assertEqual(structura_gui.resolve_theme("light"), "light")
        finally:
            structura_gui.darkdetect = real




class FontTests(unittest.TestCase):
    """The typeface ships with the program, and follows the language."""

    def test_the_bundled_files_are_present_with_their_licences(self):
        import os
        from structura.ui import ui_fonts

        for name in ui_fonts.FILES:
            self.assertTrue(os.path.isfile(ui_fonts.path(name)), name)
        for licence in ("LICENSE.txt", "NotoSansSC-LICENSE.txt"):
            self.assertTrue(os.path.isfile(ui_fonts.path(licence)),
                            "%s must travel with the fonts" % licence)

    def test_a_language_whose_script_is_not_covered_gets_its_own_face(self):
        from structura.ui import ui_fonts
        # Source Sans Pro has no CJK glyphs and is not the enchanting alphabet,
        # and Tk will not fall back to a privately registered font by itself
        self.assertNotEqual(ui_fonts.family("简体中文"), ui_fonts.family("English"))
        self.assertNotEqual(ui_fonts.family("Enchanting"), ui_fonts.family("English"))
        self.assertEqual(ui_fonts.family("Pirate Speak"), ui_fonts.family("English"))


class IconControlTests(unittest.TestCase):
    """The pack icon control: what it draws, and what answers the pointer."""

    def test_nothing_is_drawn_outside_the_frame(self):
        # the background and the preview are masked to the frame's own outline,
        # and the outline is cut out of that same mask, so no part of the
        # control may have any opacity where the mask has none
        from structura.ui import ui_icons
        from PIL import Image
        size, radius, width = 128, 14, 2
        art = Image.new("RGBA", (64, 64), (255, 255, 255, 255))
        mask = ui_icons.frame_mask(size, radius, width)
        for cut in (False, True):
            control = ui_icons.icon_control(size, radius=radius, art=art,
                                            width=width, cut=cut)
            alpha = control.split()[3]
            for x, y in ((0, 0), (size - 1, 0), (0, size - 1), (size - 1, size - 1)):
                self.assertEqual(
                    mask.getpixel((x, y)), 0,
                    "the mask should not reach the very corner")
                self.assertEqual(
                    alpha.getpixel((x, y)), 0,
                    "cut=%s leaves the control painted outside its frame at "
                    "%d,%d" % (cut, x, y))

    def test_the_clickable_corner_covers_the_drawn_one(self):
        # the cut is drawn small on purpose, which makes it a small target, so
        # the clickable corner is pushed out past it. Whatever else it does, it
        # has to accept every point the wedge is actually drawn over.
        from structura.ui import ui_icons

        size = 128
        top, side = ui_icons.WEDGE_TOP, ui_icons.WEDGE_SIDE
        for i in range(1, 10):
            for j in range(1, 10):
                fx, fy = top + (1 - top) * i / 10.0, side * j / 10.0
                if fy * (1 - top) < (fx - top) * side:      # inside the drawing
                    self.assertTrue(
                        ui_icons.in_wedge(fx * size, fy * size, size),
                        "the drawn wedge is not clickable at %.2f,%.2f" % (fx, fy))

    def test_the_clickable_corner_stays_in_its_corner(self):
        from structura.ui import ui_icons

        size = 128
        for x, y in ((size // 2, size // 2), (4, 4), (4, size - 4),
                     (size - 4, size - 4), (size // 2, size - 4)):
            self.assertFalse(ui_icons.in_wedge(x, y, size),
                             "%d,%d is not the corner" % (x, y))

    def test_the_pointer_reaches_every_part_of_the_control(self):
        # a CTkButton is a canvas with a label over it, and the label is not
        # made until an image is configured. Binding while the button is being
        # built therefore reaches only the canvas, and the label then covers all
        # but a one pixel rim, leaving the whole control unclickable.
        app = open_window()
        try:
            app.update_idletasks()
            app.refresh_icon_preview()
            app.update_idletasks()
            parts = [part for part in
                     (app.icon_button._canvas,
                      getattr(app.icon_button, "_image_label", None),
                      getattr(app.icon_button, "_text_label", None))
                     if part is not None]
            self.assertGreaterEqual(len(parts), 2,
                                    "the button should have a label over its canvas")
            for part in parts:
                for sequence in ("<Button-1>", "<Motion>", "<Leave>"):
                    self.assertTrue(
                        part.bind(sequence),
                        "%s on %s is not bound" % (sequence, part.winfo_class()))
        finally:
            app.destroy()


class RuneFaceTests(unittest.TestCase):
    """The Enchanting face has to fit the same controls the others do."""

    def face(self):
        from fontTools.ttLib import TTFont
        from structura import paths
        path = paths.data("fonts", "StructuraEnchanting.ttf")
        if not os.path.isfile(path):
            raise unittest.SkipTest("the rune face is not built")
        return TTFont(path)

    def test_the_runes_are_not_a_full_em_apart(self):
        # every glyph is drawn in a cell eight pixels across and no rune fills
        # more than five of them. An advance of one cell, which is what a
        # cell-sized em works out to, spaces them almost twice as far apart as
        # the letters of any other language, and the window's labels overflow.
        font = self.face()
        upem = font["head"].unitsPerEm
        widths = [font["hmtx"][name][0] for name in font.getGlyphOrder()
                  if font["hmtx"][name][0] > 0]
        self.assertTrue(widths, "the face has no advancing glyphs")
        average = sum(widths) / float(len(widths))
        self.assertLess(average, upem * 0.7,
                        "the runes average %.2f em apart" % (average / upem))

    def test_the_advances_vary_with_the_ink(self):
        # a single advance for every glyph is the mark of the cell width being
        # used instead of the glyph width
        font = self.face()
        widths = {font["hmtx"][name][0] for name in font.getGlyphOrder()}
        self.assertGreater(len(widths), 1, "every glyph has the same advance")

    def test_the_face_is_asked_for_smaller_than_the_interface_face(self):
        from structura.ui import ui_fonts

        self.assertLess(ui_fonts.scale("Enchanting"), 1.0)
        self.assertEqual(ui_fonts.scale("English"), 1.0)


class LanguageMenuTests(unittest.TestCase):
    def test_the_box_and_its_list_are_the_same_width(self):
        # a list narrower than the box it drops from, or wider, reads as two
        # controls rather than one
        app = open_window()
        try:
            app.update_idletasks()
            menu = app.language_menu
            menu.open()
            app.update_idletasks()
            # the size the list was placed at, not the size it reports: an
            # unmapped toplevel answers with Tk's default 200x200, which is what
            # hid half this list before it was given a size of its own. Reading
            # the mapped window instead would need the program to be the one in
            # use, which a test cannot ask for.
            wide, tall, _x, _y = menu.placed
            self.assertAlmostEqual(menu.winfo_width(), wide, delta=2)
            self.assertGreaterEqual(tall, menu.popup.winfo_reqheight() - 2)
            menu.close()
        finally:
            app.destroy()

    def test_both_selectors_are_the_same_kind_of_control(self):
        # the theme selector was a CTkOptionMenu: it lit only the strip its
        # arrow was in, drew its list with a border of its own, used a larger
        # font and dropped downward off the bottom of the window
        app = open_window()
        try:
            self.assertIs(type(app.theme_menu), type(app.language_menu))
            self.assertEqual(app.theme_menu.label.cget("font").cget("size"),
                             app.language_menu.label.cget("font").cget("size"))
            for menu in (app.theme_menu, app.language_menu):
                for part in menu.parts():
                    self.assertEqual(part.cget("cursor"), "hand2")
        finally:
            app.destroy()

    def test_the_list_is_placed_where_the_box_is(self):
        # not clamped to zero: a monitor left of or above the main one starts at
        # a negative coordinate, and clamping put the list on the other screen
        app = open_window()
        try:
            app.update_idletasks()
            menu = app.language_menu
            menu.open()
            app.update_idletasks()
            _wide, tall, x, y = menu.placed
            self.assertEqual(x, menu.winfo_rootx())
            self.assertEqual(y, menu.winfo_rooty() - tall - 4)
            menu.close()
        finally:
            app.destroy()

    def test_the_window_is_drawn_at_one_scale(self):
        # CustomTkinter otherwise makes the process per-monitor DPI aware and
        # rebuilds every widget at a new scale when a window changes monitor,
        # fading it out and back while it does, which does not survive a drag
        # between monitors intact
        import customtkinter
        from structura.ui import structura_gui                            # noqa: F401
        self.assertTrue(
            customtkinter.ScalingTracker.deactivate_automatic_dpi_awareness,
            "importing the window should have turned off automatic rescaling")

    def test_the_selectors_draw_their_whole_border(self):
        # CustomTkinter floors a frame's width and height to an even number
        # before drawing its rounded border, so a box that comes out an odd
        # number of pixels, which a scaled display will produce, loses its
        # bottom row and the outline looks broken along that edge
        app = open_window()
        try:
            for menu in (app.theme_menu, app.language_menu):
                engine = menu._draw_engine
                self.assertFalse(engine._round_width_to_even_numbers)
                self.assertFalse(engine._round_height_to_even_numbers)
        finally:
            app.destroy()

    def test_nothing_in_a_selector_covers_its_border(self):
        # a CTkLabel's "transparent" fills its rectangle with the colour behind
        # it rather than leaving those pixels alone, so a label as tall as the
        # box paints over the outline along the top and the bottom
        app = open_window()
        try:
            app.update_idletasks()
            for menu in (app.theme_menu, app.language_menu):
                edge = menu.winfo_height()
                border = menu.cget("border_width")
                for part in menu.parts():
                    if part is menu:
                        continue
                    self.assertGreaterEqual(part.winfo_y(), border)
                    self.assertLessEqual(part.winfo_y() + part.winfo_height(),
                                         edge - border)
        finally:
            app.destroy()

    def test_the_selectors_are_wide_enough_for_every_language(self):
        # the boxes are a fixed width now, so nothing measures whether the
        # longest label still fits inside one
        from structura.ui import structura_gui

        app = open_window()
        try:
            app.update_idletasks()
            for language in settings.choices():
                app.on_language(language)
                app.update_idletasks()
                for menu in (app.theme_menu, app.language_menu):
                    measure = menu.label.cget("font")
                    widest = max(measure.measure(menu.labels(value))
                                 for value in menu.values)
                    # measure() answers in real pixels and a width is in the
                    # window's own units, which are not the same on a scaled
                    # display
                    widest /= menu._get_widget_scaling() or 1.0
                    room = menu.cget("width") - (
                        structura_gui.BOX_PAD
                        + (structura_gui.BADGE + 7 if menu.badges else 0)
                        + 4 + structura_gui.CHEVRON + structura_gui.BOX_PAD)
                    self.assertLessEqual(
                        widest, room,
                        "%s clips in %s: %d into %d" % (
                            menu.labels(menu.values[0]), language, widest, room))
        finally:
            app.destroy()

    def test_the_pack_name_hint_moves_nothing_when_it_appears(self):
        # the hint holds its row whether or not it has anything to say: taken
        # out of the layout when silent, everything below it jumped up and down
        # as the pack name was typed and cleared
        app = open_window()
        try:
            app.update_idletasks()
            app.pack_name_var.set("a pack")
            app.update_idletasks()
            quiet = [w.winfo_rooty() for w in
                     (app.desc_label, app.trans_label, app.make_button)]
            app.pack_name_var.set("")
            app.update_idletasks()
            complaining = [w.winfo_rooty() for w in
                           (app.desc_label, app.trans_label, app.make_button)]
            self.assertEqual(quiet, complaining)
            self.assertTrue(app.name_hint.cget("text"))
        finally:
            app.destroy()

    def test_the_hint_row_is_tall_enough_for_its_own_text(self):
        app = open_window()
        try:
            app.update_idletasks()
            hint = app.name_hint
            self.assertGreaterEqual(hint.winfo_height(),
                                    hint.cget("font").metrics("linespace"))
        finally:
            app.destroy()

    def test_a_list_is_inset_the_same_at_both_ends(self):
        app = open_window()
        try:
            app.update_idletasks()
            menu = app.theme_menu
            menu.open()
            app.update_idletasks()
            # read from how the rows were packed rather than from where they
            # landed: an unmapped toplevel has not laid its children out, and
            # mapping one needs the program to be the one in use
            from structura.ui import structura_gui

            rows = menu.popup.winfo_children()[0].winfo_children()
            first = rows[0].pack_info()["pady"]
            last = rows[-1].pack_info()["pady"]
            self.assertEqual(int(first[0]), int(last[1]),
                             "the list is inset %s at the top and %s at the "
                             "bottom" % (first, last))
            # pack padding is scaled on the way in, so compare with the
            # constant put through the same scaling
            self.assertEqual(
                int(first[0]),
                menu._apply_widget_scaling(structura_gui.LIST_PAD))
            menu.close()
        finally:
            app.destroy()

    def test_the_window_does_not_resize(self):
        # CustomTkinter repaints every widget's own canvas when its size
        # changes, about a millisecond each, so a single step of a resize cost
        # a quarter of a second with the widgets this window has, against six
        # milliseconds for an empty window of the same kind
        app = open_window()
        try:
            self.assertEqual(app.resizable(), (0, 0))
        finally:
            app.destroy()

    def test_everything_fits_the_window_it_cannot_grow(self):
        # nothing may be laid out past the bottom of a window that can no
        # longer be dragged bigger
        import glob
        app = open_window()
        try:
            app.update_idletasks()
            for path in sorted(glob.glob("test_structures/*.mcstructure"))[:8]:
                app.add_structure_row(path)
            app.update_idletasks()
            floor = app.winfo_rooty() + app.winfo_height()
            for name in ("make_button", "list_frame", "language_menu"):
                widget = getattr(app, name)
                bottom = widget.winfo_rooty() + widget.winfo_height()
                self.assertLessEqual(bottom, floor,
                                     "%s runs past the bottom" % name)
        finally:
            app.destroy()

    def test_the_border_around_a_list_is_even_on_all_four_sides(self):
        # the window behind the list is the border colour, and the list is
        # inset from it by the same amount all round. A frame whose height
        # comes out odd goes unpainted along its last row, and the
        # colour behind shows through as an extra pixel at the bottom
        from structura.ui import structura_gui

        app = open_window()
        try:
            app.update_idletasks()
            for menu in (app.theme_menu, app.language_menu):
                menu.open()
                app.update_idletasks()
                inner = menu.popup.winfo_children()[0]
                self.assertFalse(inner._draw_engine._round_height_to_even_numbers)
                self.assertFalse(inner._draw_engine._round_width_to_even_numbers)
                ring = inner.pack_info()
                self.assertEqual(int(ring["padx"]), int(ring["pady"]))
                self.assertEqual(
                    int(ring["padx"]),
                    menu._apply_widget_scaling(structura_gui.LIST_RING))
                menu.close()
        finally:
            app.destroy()


class ConstructedLanguageTests(unittest.TestCase):
    """The joke languages have to actually say something different."""

    ## a proper name and the three axis letters, which stay as they are
    ## two proper names and the three axis letters, which stay as they are
    LEFT_ALONE = {"title", "techpack", "axis x", "axis y", "axis z"}

    def test_every_label_is_transformed(self):
        from structura import lang_fun
        settings.langs = settings.read_languages()
        english = settings.langs["English"]
        for name, transform in (("pirate", lang_fun.pirate),
                                ("lolcat", lang_fun.lolcat),
                                ("shakespeare", lang_fun.shakespeare)):
            untouched = sorted(key for key, value in english.items()
                               if value and transform(value) == value
                               and key not in self.LEFT_ALONE)
            self.assertEqual(untouched, [],
                             "%s leaves these in plain English: %s"
                             % (name, untouched))

    def test_a_placeholder_survives_every_transform(self):
        # the transforms run only between the {} markers; a mangled placeholder
        # raises on the next .format()
        from structura import lang_fun
        sample = {"line": "Added {} to the pack"}
        for name in lang_fun.names():
            spoken = lang_fun.translate(name, sample)["line"]
            self.assertIn("{}", spoken, "%s lost its placeholder" % name)
            spoken.format("a thing")


class CoordinatesButtonTests(unittest.TestCase):
    def test_it_is_wide_enough_in_every_language(self):
        # Ukrainian needs seventy per cent more room than English, and the
        # button sat in a column a third of the panel wide
        app = open_window()
        try:
            app.big_build.set(1)
            app.on_big_build()
            app.update_idletasks()
            button = app.cords_button
            for language in settings.choices():
                app.on_language(language)
                app.update_idletasks()
                self.assertGreaterEqual(
                    button.winfo_width(), button.winfo_reqwidth(),
                    "the coordinates button clips in %s: %d into %d"
                    % (language, button.winfo_reqwidth(), button.winfo_width()))
        finally:
            app.destroy()


class FieldTests(unittest.TestCase):
    def test_a_field_shows_the_same_margin_above_and_below_its_text(self):
        # a CTkEntry paints the colour behind it across its whole rectangle, so
        # one centred in a taller row splits the leftover unevenly, leaving a
        # pixel of field above the text and two below it
        app = open_window()
        try:
            app.update_idletasks()
            settle(app)
            fields = [("pack name", app.pack_name_field),
                      ("description", app.desc_field)]
            fields += [("offset %d" % i, f)
                       for i, f in enumerate(app.offset_fields)]
            for state in ("", "a pack"):
                app.pack_name_var.set(state)
                settle(app)
                for name, field in fields:
                    above = field.entry.winfo_y()
                    below = field.winfo_height() - (
                        field.entry.winfo_y() + field.entry.winfo_height())
                    self.assertEqual(
                        above, below,
                        "%s shows %d above and %d below" % (name, above, below))
        finally:
            app.destroy()

    def test_the_text_clears_the_thickest_border_a_field_can_have(self):
        # the border grows from one to two while a field is showing an error,
        # and the text must not shift or be painted over when it does
        from structura.ui import structura_gui

        app = open_window()
        try:
            app.update_idletasks()
            app.pack_name_var.set("")
            settle(app)
            field = app.pack_name_field
            self.assertEqual(field.cget("border_width"), 2)
            self.assertGreaterEqual(
                field.entry.winfo_y(),
                field._apply_widget_scaling(structura_gui.FIELD_INSET))
        finally:
            app.destroy()


class SettingsFileTests(unittest.TestCase):
    """Everything the settings file holds is written back when it changes.

    A setting that is remembered in memory and not on disk looks like it worked
    until the program is next opened, which is the kind of bug nobody reports
    because it is easy to believe you imagined it.
    """

    ## every key in the file, with a value different from the default and the
    ## call that is supposed to persist it. A key with no entry here fails the
    ## first test rather than being quietly untested.
    def changes(self):
        return {
            "lang": ("Español", settings.set_language),
            "theme": ("dark", settings.set_theme),
            "tech_pack": ("compatibility", settings.set_tech_pack),
            "output_dir": (os.path.join(os.path.expanduser("~"), "Somewhere"),
                           settings.set_output_dir),
        }

    def setUp(self):
        import json
        import shutil
        import tempfile

        self.folder = tempfile.mkdtemp()
        self.path = os.path.join(self.folder, ".structura")
        self._real = settings.settings_file
        settings.settings_file = lambda: self.path
        self.addCleanup(setattr, settings, "settings_file", self._real)
        self.addCleanup(shutil.rmtree, self.folder, True)
        self._stored = dict(settings.settings)
        self.addCleanup(settings.settings.update, self._stored)
        settings.load()
        self.json = json

    def on_disk(self):
        if not os.path.isfile(self.path):
            return {}
        with open(self.path, encoding="utf-8-sig") as handle:
            return self.json.load(handle)

    def test_every_key_in_the_file_has_a_setter_that_is_checked(self):
        self.assertEqual(sorted(self.changes()), sorted(settings.DEFAULTS))

    def test_changing_a_setting_writes_it_back(self):
        for key, (value, setter) in sorted(self.changes().items()):
            with self.subTest(setting=key):
                setter(value)
                self.assertEqual(self.on_disk().get(key), settings.settings[key],
                                 "%s was not written to the file" % key)

    def test_the_file_is_never_inside_the_package(self):
        # paths.beside_executable() means the package when not frozen, which is
        # right for reading data and wrong for the user's own settings:
        # site-packages is shared and not theirs to write to
        from structura import paths

        settings.settings_file = self._real
        self.assertNotIn(os.path.dirname(os.path.abspath(paths.__file__)),
                         settings.settings_file())



class HelpMarkTests(unittest.TestCase):
    """The ? beside a setting, and the tip it shows."""

    def marks(self, app):
        found = [(sw.key, sw.label, sw.mark) for sw in app.switches if sw.mark]
        found.append(("techpack", app.tech_label, app.tech_mark))
        return found

    def test_the_mark_sits_against_its_label_not_the_control(self):
        # the ? belongs to the words, so its column must not be the stretchy
        # one: a stretchy column carries it across the row to the switch
        app = open_window()
        try:
            settle(app)
            for key, label, mark in self.marks(app):
                gap = mark.winfo_x() - (label.winfo_x() + label.winfo_width())
                self.assertGreaterEqual(gap, 0, "%s: the ? overlaps its label" % key)
                self.assertLess(gap, 20,
                                "%s: the ? is %d px from its label" % (key, gap))
        finally:
            app.destroy()

    def test_the_tip_survives_the_window_merely_laying_itself_out(self):
        # Configure fires throughout a layout, so binding it directly made the
        # tip vanish the instant it appeared
        app = open_window()
        try:
            settle(app)
            tip = app.tech_mark.tip
            tip.show()
            settle(app)
            self.assertIsNotNone(tip.window, "the tip dismissed itself")
            tip.hide()
        finally:
            app.destroy()

    def test_every_way_out_puts_the_tip_away(self):
        app = open_window()
        try:
            settle(app)
            tip = app.tech_mark.tip

            class Elsewhere(object):
                widget = app.make_button

            for name, dismiss in (("a click elsewhere",
                                   lambda: tip.elsewhere(Elsewhere())),
                                  ("leaving the mark", tip.leave),
                                  ("the window moving", tip.moved)):
                tip.show()
                settle(app, 2)
                self.assertIsNotNone(tip.window)
                if name == "the window moving":
                    tip._anchor = (-1, -1, -1, -1)
                dismiss()
                self.assertIsNone(tip.window, "%s left it up" % name)
                self.assertEqual(tip._watching, [],
                                 "%s left handlers bound" % name)
        finally:
            app.destroy()

    def test_a_click_on_the_mark_itself_keeps_it(self):
        app = open_window()
        try:
            settle(app)
            tip = app.tech_mark.tip
            tip.show()
            settle(app, 2)

            class OnTheMark(object):
                widget = app.tech_mark

            tip.elsewhere(OnTheMark())
            self.assertIsNotNone(tip.window)
            tip.hide()
        finally:
            app.destroy()

    def test_showing_twice_does_not_stack_handlers(self):
        app = open_window()
        try:
            settle(app)
            tip = app.tech_mark.tip
            tip.show()
            tip.show()
            settle(app, 2)
            self.assertEqual(len(tip._watching), 3)
            tip.hide()
            self.assertEqual(tip._watching, [])
        finally:
            app.destroy()

if __name__ == "__main__":
    unittest.main()
