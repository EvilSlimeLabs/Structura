import json
import re
import unittest

from structura import paths
from structura.pack import armor_stand_geo_class as asgc

## Education Edition and other blocks no vanilla pack ships textures for. They
## are declared so a structure containing one is named rather than mysterious,
## and they will never resolve. tools/audit_blocks.py holds the same list.
UNRESOLVABLE = re.compile(r"^(element_\d+|chemistry_table|chemical_heat"
                          r"|hard_(stained_)?glass(_pane)?"
                          r"|colored_torch_\w+|underwater_torch"
                          r"|coral_(fan_)?pink_dead)$")


def load(name):
    # through paths, so the suite does not depend on where it was run from
    with open(paths.lookup(name + ".json"), encoding="utf-8") as f:
        return json.load(f)


class LookupTableTests(unittest.TestCase):
    """The three tables that describe a block have to agree with each other.

    A block_definition entry naming a shape family that block_shapes does not
    describe raises inside make_block, which _add_blocks_to_geo catches, so a
    disagreement here does not fail a build. It quietly empties one out of it.
    """

    @classmethod
    def setUpClass(cls):
        cls.defs = load("block_definition")
        cls.shapes = load("block_shapes")
        cls.uv = load("block_uv")

    def test_every_shape_family_is_described_by_both_tables(self):
        families = {v for v in self.defs.values() if v != "ignore"}
        self.assertFalse(families - set(self.shapes),
                         "shape families with no block_shapes entry")
        self.assertFalse(families - set(self.uv),
                         "shape families with no block_uv entry")

    def test_every_shape_variant_has_a_usable_uv_window(self):
        # a variant missing from block_uv silently falls back to "default",
        # which is right only when its cubes are the same size as the default's
        families = {v for v in self.defs.values() if v != "ignore"}
        for family, variants in self.shapes.items():
            if family not in families:
                continue
            for variant, shape in variants.items():
                window = self.uv[family].get(variant, self.uv[family]["default"])
                for face in ("up", "down", "north", "south", "east", "west"):
                    self.assertGreaterEqual(
                        len(window["uv_sizes"][face]), 1,
                        "%s/%s has no %s uv size" % (family, variant, face))
                    self.assertEqual(
                        len(window["uv_sizes"][face]), len(window["offset"][face]),
                        "%s/%s: %s sizes and offsets disagree" % (family, variant, face))


class BlockBuildTests(unittest.TestCase):
    """Blocks that are easy to drop, built in the states that drop them."""

    def setUp(self):
        self.geo = asgc.ArmorStandGeo("test", offsets=[0, 0, 0])

    def build(self, name, **kwargs):
        self.geo.blocks = {}
        self.geo.make_block(0, 0, 0, name, **kwargs)

    def test_every_defined_block_builds(self):
        defs = load("block_definition")
        broken = []
        for name in defs:
            if UNRESOLVABLE.match(name):
                continue
            try:
                self.build(name)
            except Exception as exc:
                broken.append("%s (%s)" % (name, type(exc).__name__))
        self.assertEqual(broken, [], "blocks that raise in make_block")

    def test_an_unknown_rotation_state_does_not_drop_the_block(self):
        # soul_campfire reads direction 0 against a table that only listed 1,
        # and the block vanished every time it faced that way. A rotation the
        # table cannot describe should leave the block unrotated, not remove it.
        self.build("soul_campfire", rot=0)
        self.build("soul_campfire", rot="nonsense")
        self.assertTrue(self.geo.blocks)

    def test_legacy_slab_ids_build_in_both_halves(self):
        for name in ("stone_slab", "stone_slab2", "stone_slab3", "stone_slab4",
                     "petrified_oak_slab"):
            for top in (False, True):
                self.build(name, top=top)

    def test_the_new_shape_families_build(self):
        for name in ("oak_shelf", "sulfur_spike", "copper_golem_statue",
                     "heavy_core"):
            self.build(name)




class GeometryDetailTests(unittest.TestCase):
    """The low geometry setting, and the simplified shapes it reaches for."""

    def tables(self):
        import json
        from structura import paths
        with open(paths.lookup("block_shapes.json")) as handle:
            shapes = json.load(handle)
        with open(paths.lookup("block_uv.json")) as handle:
            uv = json.load(handle)
        return shapes, uv

    def test_every_simplified_shape_is_in_both_tables(self):
        # a family described in one table and not the other silently falls back
        # to default, which is how a half-height cube ends up wearing a
        # full-height texture
        from structura.pack import armor_stand_geo_class as asgc

        shapes, uv = self.tables()
        for name in shapes:
            if name.endswith(asgc.LOW_SUFFIX):
                self.assertIn(name, uv, "%s has a shape but no UV" % name)
        for name in uv:
            if name.endswith(asgc.LOW_SUFFIX):
                self.assertIn(name, shapes, "%s has a UV but no shape" % name)

    def test_a_simplified_shape_is_simpler(self):
        from structura.pack import armor_stand_geo_class as asgc

        shapes, _uv = self.tables()
        found = 0
        for name, body in shapes.items():
            if not name.endswith(asgc.LOW_SUFFIX):
                continue
            found += 1
            detailed = shapes[name[:-len(asgc.LOW_SUFFIX)]]["default"]["size"]
            self.assertLess(len(body["default"]["size"]), len(detailed),
                            "%s is no simpler than what it replaces" % name)
        self.assertGreater(found, 0, "no simplified shapes at all")

    def test_the_setting_reaches_the_geometry(self):
        from structura.pack import armor_stand_geo_class as asgc

        plain = asgc.ArmorStandGeo("t", low_geometry=True)
        full = asgc.ArmorStandGeo("t", low_geometry=False)
        # a family with a simpler form is swapped, one without is left alone
        self.assertEqual(plain.simplify("bell"), "bell" + asgc.LOW_SUFFIX)
        self.assertEqual(full.simplify("bell"), "bell")
        self.assertEqual(plain.simplify("cube"), "cube")
        self.assertEqual(plain.simplify("ignore"), "ignore")


class ChiseledBookshelfTests(unittest.TestCase):
    def test_every_arrangement_of_books_is_described(self):
        # books_stored is a six bit number, so there are sixty-four of them
        import json
        from structura import paths
        with open(paths.lookup("block_shapes.json")) as handle:
            shapes = json.load(handle)["chiseled_bookshelf"]
        with open(paths.lookup("block_uv.json")) as handle:
            uv = json.load(handle)["chiseled_bookshelf"]
        for mask in range(64):
            self.assertIn(str(mask), shapes)
            self.assertIn(str(mask), uv)
            # the shelf itself, plus one panel for each book it holds
            self.assertEqual(len(shapes[str(mask)]["size"]),
                             1 + bin(mask).count("1"))

    def test_the_front_texture_is_one_that_exists(self):
        # blocks.json names chiseled_bookshelf_front, which no vanilla pack
        # ships and terrain_texture.json has no entry for
        import json
        import os
        from structura import paths
        with open(paths.lookup("block_uv.json")) as handle:
            uv = json.load(handle)["chiseled_bookshelf"]
        for mask in ("0", "63"):
            for texture in uv[mask]["overwrite"]["north"]:
                self.assertTrue(
                    os.path.isfile(os.path.join(paths.vanilla_pack(),
                                                texture + ".png")),
                    "%s is not in the vanilla pack" % texture)


class LayeringTests(unittest.TestCase):
    """The command line build has no interface in it, and must not grow one."""

    def reachable(self, start):
        """Every module in this tree that `start` can reach, directly or not."""
        import ast
        import io
        import os

        def imports_of(path):
            tree = ast.parse(io.open(path, encoding="utf-8").read())
            names = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names |= {a.name for a in node.names}
                elif isinstance(node, ast.ImportFrom) and node.module:
                    names.add(node.module)
                    names |= {node.module + "." + a.name for a in node.names}
            return names

        def resolve(name):
            base = name.replace(".", os.sep)
            for candidate in (base + ".py", os.path.join(base, "__init__.py")):
                if os.path.isfile(candidate):
                    return candidate
            return None

        seen, queue = set(), [start]
        while queue:
            path = queue.pop()
            if path in seen:
                continue
            seen.add(path)
            for name in imports_of(path):
                found = resolve(name)
                if found and found not in seen:
                    queue.append(found)
        return seen

    def test_the_command_line_never_reaches_the_window(self):
        import os
        reached = self.reachable(os.path.join("structura", "cli", "__main__.py"))
        inside = os.path.join("structura", "ui") + os.sep
        window = sorted(p for p in reached if p.startswith(inside))
        self.assertEqual(window, [],
                         "the command line build pulls in %s" % window)

    def test_the_command_line_package_imports_no_interface(self):
        import io
        import os
        folder = os.path.join("structura", "cli")
        for name in sorted(os.listdir(folder)):
            if not name.endswith(".py"):
                continue
            body = io.open(os.path.join(folder, name), encoding="utf-8").read()
            where = "structura/cli/%s" % name
            self.assertNotIn("from structura.ui import", body, where)
            for line in body.split("\n"):
                self.assertNotEqual(line.strip(), "from structura import ui", where)

    def test_both_entry_points_share_one_argument_parser(self):
        # a script written against one build has to run against the other
        from structura import cli
        first = cli.arguments.parse(["--structure", "a", "--pack_name", "b"])
        self.assertEqual(first.tech_pack, "none")
        self.assertFalse(first.low_geometry)
        self.assertEqual(first.structure, "a")

    def test_nothing_to_do_is_reported_rather_than_guessed(self):
        # the entry points answer it differently, so cli.main must not decide
        from structura import cli
        self.assertEqual(cli.main([]), cli.NOTHING_ASKED)


if __name__ == "__main__":
    unittest.main()
