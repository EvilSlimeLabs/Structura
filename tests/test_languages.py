import unittest

import lang_fun
import lang_parse


class ConstructedLanguageTests(unittest.TestCase):
    """The joke languages are generated from English, not stored.

    That is what keeps them covering every string the window has: nobody has to
    remember to add three hundred more cells when a label is added.
    """

    @classmethod
    def setUpClass(cls):
        cls.english = lang_parse.parse()["English"]

    def test_each_one_covers_every_string(self):
        for name in lang_fun.names():
            table = lang_fun.translate(name, self.english)
            self.assertEqual(set(table), set(self.english), name)
            self.assertTrue(all(v for v in table.values()), name)

    def test_format_placeholders_survive_and_still_format(self):
        # reversing "Built {}" without protecting the placeholder would produce
        # "}{ tliuB", and .format() would raise on the next build that finished
        for name in lang_fun.names():
            table = lang_fun.translate(name, self.english)
            for key, english in self.english.items():
                if "{}" not in english:
                    continue
                self.assertIn("{}", table[key], "%s/%s" % (name, key))
                table[key].format("something")

    def test_each_one_actually_changes_the_text(self):
        plain = self.english["makepack"]
        for name in lang_fun.names():
            self.assertNotEqual(lang_fun.translate(name, self.english)["makepack"],
                                plain, "%s left the text alone" % name)

    def test_an_unknown_language_comes_back_unchanged(self):
        self.assertEqual(lang_fun.translate("Klingon", self.english), self.english)

    def test_upside_down_reverses_the_line(self):
        # the whole line turns over, so the pieces swap ends as well as the
        # letters -- otherwise it reads as flipped letters in English order
        self.assertEqual(lang_fun.upside_down("ab"), "qɐ")

    def test_every_constructed_language_has_a_badge_code(self):
        for name in lang_fun.names():
            self.assertRegex(lang_fun.code(name), r"^[a-z]{3}$")
            self.assertTrue(lang_parse.constructed(name))


class RealLanguageTests(unittest.TestCase):
    def test_tagalog_and_cebuano_are_complete(self):
        table = lang_parse.parse()
        english = set(table["English"])
        for name in ("Tagalog", "Cebuano"):
            self.assertIn(name, table)
            self.assertEqual(set(table[name]), english)
            blank = [k for k, v in table[name].items() if not v]
            self.assertEqual(blank, [], "%s has untranslated rows" % name)


if __name__ == "__main__":
    unittest.main()
