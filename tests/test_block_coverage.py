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


class MountingTests(unittest.TestCase):
    """A block held up four different ways is four different shapes."""

    def setUp(self):
        self.geo = asgc.ArmorStandGeo("test", offsets=[0, 0, 0])

    def cubes(self, name, **kwargs):
        """Every cube one block produces, wherever it ended up."""
        self.geo.blocks = {}
        self.geo.make_block(0, 0, 0, name, **kwargs)
        found = []
        for group in self.geo.blocks.values():
            for cube in group.get("cubes", []):
                found.append((tuple(cube["origin"]), tuple(cube["size"])))
        return found

    def forms(self, name, variants, **kwargs):
        return {variant: self.cubes(name, data=variant, **kwargs)
                for variant in variants}

    def test_a_bell_is_carried_differently_by_each_mounting(self):
        # standing has two posts and a beam, between two walls only the beam,
        # on one wall half of it, and under a block none of it
        forms = self.forms("bell", ("standing", "multiple", "side", "hanging"))
        self.assertEqual([len(form) for form in forms.values()], [5, 3, 3, 3])
        for one, other in (("standing", "multiple"), ("multiple", "side"),
                           ("side", "hanging")):
            self.assertNotEqual(forms[one], forms[other],
                                "a bell %s looks like one %s" % (one, other))

    def test_a_grindstone_puts_its_legs_where_it_is_fixed(self):
        forms = self.forms("grindstone",
                           ("standing", "hanging", "side", "multiple"))
        for one, other in (("standing", "hanging"), ("hanging", "side"),
                           ("side", "multiple")):
            self.assertNotEqual(forms[one], forms[other],
                                "a grindstone %s looks like one %s" % (one, other))

    def test_a_hanging_sign_shows_how_it_is_hung(self):
        # named by attached_bit and hanging: chains under a block, a bar when
        # attached to it, and a bar with an arm when mounted on a wall
        forms = self.forms("oak_hanging_sign", ("0-1", "1-1", "0-0"))
        self.assertEqual([len(form) for form in forms.values()], [3, 4, 5])
        self.assertNotEqual(forms["0-1"], forms["1-1"])
        self.assertNotEqual(forms["1-1"], forms["0-0"])

    def test_a_hanging_sign_reads_the_state_its_mounting_turns_with(self):
        # Bedrock gives it both, and only one applies: a sign fixed to the
        # block above turns in sixteen steps with ground_sign_direction, and
        # every other mounting turns with facing_direction, which is why the
        # two numberings cannot share a rotation entry.
        from structura import core

        wall = {"states": {"attached_bit": 0, "hanging": 0,
                           "facing_direction": 4, "ground_sign_direction": 0}}
        fixed = {"states": {"attached_bit": 1, "hanging": 1,
                            "facing_direction": 0, "ground_sign_direction": 10}}
        self.assertEqual(core.Structura._process_block(None, wall)[0], 4)
        self.assertEqual(core.Structura._process_block(None, fixed)[0], 10)

    def test_each_mounting_turns_by_its_own_numbering(self):
        def angle(variant, rot):
            self.geo.blocks = {}
            self.geo.make_block(0, 0, 0, "oak_hanging_sign", rot=rot,
                                data=variant)
            group = list(self.geo.blocks.values())[0]
            return group["cubes"][0]["rotation"]

        # 4 is west to a wall sign and 90 degrees round to an attached one
        self.assertEqual(angle("0-0", 4), [0, 90, 0])
        self.assertEqual(angle("1-1", 4), [0, 90.0, 0])
        self.assertEqual(angle("1-1", 10), [0, 225.0, 0])

    def test_a_lit_campfire_is_the_one_with_a_fire_on_it(self):
        # the logs barely differ between lit and out, so the flame is what
        # tells them apart, and which flame tells a soul campfire from the rest
        lit = self.cubes("campfire", data="0")
        out = self.cubes("campfire", data="1")
        self.assertEqual(len(lit) - len(out), 2, "the flame is two quads")
        self.assertEqual(len(self.cubes("soul_campfire", data="0")), len(lit))

    def test_a_sheet_texture_is_read_a_window_at_a_time(self):
        # A hanging sign's texture is an entity sized sheet carrying the bar,
        # the chains and the board one under the other, and only the top left
        # 16x16 of a texture becomes a tile. Each part names the window it
        # needs, and each window is a tile of its own.
        self.assertEqual(asgc.split_window("blocks/oak"), ("blocks/oak", (0, 0)))
        self.assertEqual(asgc.split_window("blocks/oak#4,12"),
                         ("blocks/oak", (4, 12)))

        self.cubes("oak_hanging_sign", data="0-0")
        self.cubes("oak_hanging_sign", data="0-1")
        windows = [name for name in self.geo.uv_map if "#" in name]
        self.assertEqual(len(set(windows)), 3,
                         "the board, the bar and the chains are three windows")
        self.assertEqual(len(set(self.geo.uv_map[name] for name in windows)), 3,
                         "each window should be a tile of its own")

    def test_a_shelf_shows_a_different_face_on_each_side(self):
        # its texture is a sheet: the front with three compartments painted in,
        # the solid back beside it, and planks for the ends. Taking the whole
        # tile puts the compartments on all six faces.
        self.geo.blocks = {}
        self.geo.make_block(0, 0, 0, "oak_shelf", rot="south")
        cube = list(self.geo.blocks.values())[0]["cubes"][0]
        # a face's v runs from the top of the tile it reads, so the whole part
        # of it names the tile and the fraction is the window within it
        tiles = {face: int(cube["uv"][face]["uv"][1])
                 for face in ("north", "south", "east", "west", "up", "down")}
        self.assertNotEqual(tiles["north"], tiles["south"],
                            "the back of a shelf is not its front")
        self.assertEqual(len(set(tiles.values())), 4,
                         "front, back, planks along the top and bottom, ends")
        self.assertEqual(tiles["up"], tiles["down"], "both planks, one tile")
        self.assertEqual(tiles["east"], tiles["west"], "both ends, one tile")
        self.assertEqual(cube["size"], [1.0, 1.0, 0.5],
                         "a shelf is a full block wide and tall, half deep")

    def test_a_window_larger_than_its_texture_is_ignored(self):
        # every wood has its own sheet, and a block whose texture is a plain
        # terrain tile must not end up reading blank space past the bottom of it
        self.geo.blocks = {}
        self.geo.make_block(0, 0, 0, "hanging_sign", data="0-1")
        self.assertTrue(self.geo.blocks)

    def test_a_cube_that_turns_on_its_own_is_drawn_once(self):
        # a cube carrying its own rotation goes into a nested bone, and leaving
        # it in the slice as well draws every campfire and statue twice
        for name, variant in (("campfire", "0"), ("copper_golem_statue", "1")):
            plain = self.cubes(name, data=variant)
            turned = self.cubes(name, data=variant, rot="east")
            self.assertEqual(len(plain), len(turned),
                             "%s gains cubes when it is turned" % name)




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
