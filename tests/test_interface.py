import os
import re
import unittest

import app_settings
import lang_parse


class TransparencyTests(unittest.TestCase):
    """The slider is transparency; everything downstream wants alpha."""

    def test_the_ends_of_the_slider(self):
        self.assertEqual(app_settings.transparency_to_alpha(0), 1.0)
        self.assertAlmostEqual(app_settings.transparency_to_alpha(100), 0.0)

    def test_the_default_is_the_same_number_everywhere(self):
        # the window, the CLI's --opacity and the core's own default all have to
        # land on the same ghost block, or a pack built one way looks different
        # from the same pack built another
        import armor_stand_geo_class as asgc
        alpha = app_settings.transparency_to_alpha(app_settings.DEFAULT_TRANSPARENCY)
        self.assertAlmostEqual(alpha, asgc.DEFAULT_ALPHA)
        self.assertAlmostEqual(app_settings.DEFAULT_OPACITY / 100, alpha)

    def test_the_slider_never_reaches_fully_invisible(self):
        self.assertLess(app_settings.MAX_TRANSPARENCY, 100)


class LanguageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app_settings.langs = app_settings.read_languages()

    def test_every_language_has_a_code_for_its_badge(self):
        # the picker labels languages by code, not by flag: a flag is a country,
        # and several countries share a language. Two letters where ISO 639-1
        # has one, three where it does not -- Cebuano, and the constructed
        # languages, which are not real languages and have no code at all.
        for name in app_settings.langs:
            code = lang_parse.code(name)
            self.assertRegex(code, r"^[a-z]{2,3}$", "%s has no usable code" % name)

    def test_the_constructed_languages_are_marked_and_coloured_apart(self):
        import lang_icons
        real = [n for n in app_settings.choices() if not lang_parse.constructed(n)]
        fake = [n for n in app_settings.choices() if lang_parse.constructed(n)]
        self.assertTrue(real and fake)
        for name in real:
            self.assertEqual(lang_icons.colour(lang_parse.code(name)),
                             lang_icons.DEFAULT_COLOUR)
        for name in fake:
            self.assertNotEqual(lang_icons.colour(lang_parse.code(name)),
                                lang_icons.DEFAULT_COLOUR,
                                "%s should not wear the real-language colour" % name)

    def test_english_fills_gaps_in_another_language(self):
        strings = app_settings.language("Español")
        english = app_settings.langs["English"]
        self.assertEqual(set(strings), set(english))
        self.assertTrue(all(strings.values()))

    def test_the_placeholder_column_is_not_offered(self):
        self.assertNotIn("Test", app_settings.choices())
        self.assertIn("English", app_settings.choices())

    def test_an_unknown_language_falls_back_rather_than_raising(self):
        strings = app_settings.language("Klingon")
        self.assertEqual(strings, app_settings.langs["English"])


class StringCoverageTests(unittest.TestCase):
    """Every label the window asks for has to exist in the table.

    A missing key would put the raw lookup name on screen rather than a word,
    and nothing else would complain about it.
    """

    def test_every_key_the_window_uses_is_in_langs_csv(self):
        with open("structura_gui.py", encoding="utf-8") as f:
            source = f.read()
        keys = set(re.findall(r'(?:self\.)?text\(\s*"([^"]+)"', source))
        keys |= set(re.findall(r'app\.text\(\s*"([^"]+)"', source))
        english = lang_parse.parse()["English"]
        # themes are looked up by their stored name
        keys |= set(app_settings.THEMES)
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
        self.assertEqual(app_settings.DEFAULT_THEME, "system")
        self.assertEqual(app_settings.FALLBACK_THEME, "dark")
        self.assertIn(app_settings.FALLBACK_THEME, app_settings.THEMES)

    def test_an_undetectable_desktop_resolves_to_dark(self):
        import structura_gui
        real = structura_gui.darkdetect
        try:
            structura_gui.darkdetect = None
            self.assertEqual(structura_gui.resolve_theme("system"), "dark")
            self.assertEqual(structura_gui.resolve_theme("light"), "light")
        finally:
            structura_gui.darkdetect = real


if __name__ == "__main__":
    unittest.main()
