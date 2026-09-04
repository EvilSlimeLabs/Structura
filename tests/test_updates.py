import hashlib
import os
import pathlib
import shutil
import sys
import tempfile
import threading
import unittest

from structura import updates


class VersionTests(unittest.TestCase):
    """Which release counts as newer than the one running."""

    def test_a_tag_is_read_with_or_without_its_v(self):
        self.assertEqual(updates.as_numbers("v3.1.0"), (3, 1, 0))
        self.assertEqual(updates.as_numbers("3.1"), (3, 1, 0))
        self.assertEqual(updates.as_numbers("3.1.0-rc2"), (3, 1, 0))

    def test_a_release_candidate_is_not_newer_than_its_release(self):
        # read the other way round, 3.0.0-rc2 comes out as 3.0.2 and everybody
        # running 3.0.0 is offered a candidate of what they already have
        self.assertFalse(updates.newer("3.0.0-rc2", "3.0.0"))
        self.assertTrue(updates.newer("3.1.0-rc1", "3.0.0"))

    def test_only_a_later_release_counts(self):
        self.assertTrue(updates.newer("3.0.1", "3.0.0"))
        self.assertTrue(updates.newer("v10.0.0", "3.0.0"))
        self.assertFalse(updates.newer("3.0.0", "3.0.0"))
        self.assertFalse(updates.newer("2.9.9", "3.0.0"))

    def test_a_tag_that_is_not_a_version_is_never_newer(self):
        # a repository can tag anything at all, and an unreadable tag must not
        # send everybody an update
        for tag in ("rubbish", "", None, "latest"):
            self.assertFalse(updates.newer(tag, "3.0.0"), tag)


class ReplacementTests(unittest.TestCase):
    """Putting a new build in the place of the running one."""

    def setUp(self):
        self.folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.folder, True)
        self.exe = os.path.join(self.folder, "Structura.exe")
        shutil.copy(sys.executable, self.exe)
        self.real_frozen = updates.paths.frozen
        self.real_exe = sys.executable
        updates.paths.frozen = lambda: True
        sys.executable = self.exe
        self.addCleanup(setattr, sys, "executable", self.real_exe)
        self.addCleanup(setattr, updates.paths, "frozen", self.real_frozen)

    def test_only_a_built_program_has_something_to_replace(self):
        updates.paths.frozen = lambda: False
        self.assertIsNone(updates.running_file())
        self.assertIsNone(updates.available())

    def test_what_is_not_a_program_is_refused(self):
        # a rate limit answers with a page, not a build, and installing it
        # would leave nothing to run
        junk = os.path.join(self.folder, "junk")
        with open(junk, "w") as file:
            file.write("rate limit exceeded")
        self.assertFalse(updates.looks_like_a_program(junk))
        self.assertTrue(updates.looks_like_a_program(self.exe))

    def test_the_displaced_build_is_cleared_by_a_later_launch(self):
        # the file a process is running from cannot delete itself, so the
        # update leaves it and the next launch takes it away
        displaced = self.exe + updates.DISPLACED
        shutil.copy(sys.executable if os.path.isfile(sys.executable)
                    else self.exe, displaced)
        self.assertTrue(os.path.isfile(displaced))
        self.assertTrue(updates.clear_displaced())
        self.assertFalse(os.path.isfile(displaced))

    def test_clearing_is_quiet_when_there_is_nothing_to_clear(self):
        self.assertFalse(updates.clear_displaced())

    def test_a_build_that_will_not_start_is_refused(self):
        # the size and the first two bytes are right and the file is still not
        # a program, which is what a half-written or emptied download looks like
        stub = os.path.join(self.folder, "stub.exe")
        with open(stub, "wb") as file:
            file.write(b"MZ" + b"\0" * (updates.SMALLEST * 2))
        self.assertTrue(updates.looks_like_a_program(stub))
        self.assertFalse(updates.answers_for_itself(stub, timeout=30))

    def test_a_program_that_runs_answers_for_itself(self):
        # the interpreter is the one program certainly on this machine
        self.assertTrue(updates.answers_for_itself(self.real_exe, timeout=60))

    def release(self, name="release.exe", content=None):
        """A file standing in for a release asset, and what it hashes to."""
        where = os.path.join(self.folder, name)
        if content is None:
            shutil.copy(self.real_exe, where)
        else:
            with open(where, "wb") as file:
                file.write(content)
        with open(where, "rb") as file:
            return pathlib.Path(where).as_uri(), hashlib.sha256(
                file.read()).hexdigest()

    def untouched(self, was):
        self.assertEqual(os.path.getsize(self.exe), was)
        self.assertFalse(os.path.exists(self.exe + updates.INCOMING))
        self.assertFalse(os.path.exists(self.exe + updates.DISPLACED))

    def test_nothing_is_touched_when_the_download_will_not_run(self):
        # every refusal before the swap has to leave the folder as it was
        url, digest = self.release(
            content=b"MZ" + b"\0" * (updates.SMALLEST * 2))
        was = os.path.getsize(self.exe)
        answer = updates.install(url, digest, restart=False)
        self.assertEqual(answer[0], "update does not run")
        self.untouched(was)

    def test_a_download_that_does_not_match_its_fingerprint_is_refused(self):
        # the check that catches a build altered between the release and here
        url, digest = self.release()
        was = os.path.getsize(self.exe)
        answer = updates.install(url, digest.replace(digest[0], "f", 1),
                                 restart=False)
        self.assertEqual(answer[0], "update wrong fingerprint")
        self.untouched(was)

    def test_the_swap_leaves_the_old_build_to_fall_back_to(self):
        # the interpreter stands in for a release: it is a real program, so it
        # answers --help and the install runs the whole way through
        url, digest = self.release()
        self.assertIsNone(updates.install(url, digest, restart=False))
        self.assertTrue(os.path.isfile(self.exe))
        self.assertTrue(os.path.isfile(self.exe + updates.DISPLACED))
        self.assertFalse(os.path.exists(self.exe + updates.INCOMING))

    def test_fingerprints_are_read_the_way_sha256sum_writes_them(self):
        sums = os.path.join(self.folder, updates.SUMS)
        with open(sums, "w", encoding="utf-8") as file:
            file.write("# a comment nobody has to argue with\n"
                       "%s  Structura.exe\n"
                       "%s *Structura-cli.exe\n" % ("a" * 64, "B" * 64))
        found = updates.fingerprints(pathlib.Path(sums).as_uri())
        self.assertEqual(found, {"Structura.exe": "a" * 64,
                                 "Structura-cli.exe": "b" * 64})

    @unittest.skipUnless(sys.platform.startswith("win"),
                         "only Windows has a hidden attribute")
    def test_the_displaced_build_is_hidden_and_still_clears(self):
        displaced = self.exe + updates.DISPLACED
        shutil.copy(self.exe, displaced)
        self.assertTrue(updates.hide(displaced))
        self.assertTrue(updates.clear_displaced())
        self.assertFalse(os.path.exists(displaced))

    @unittest.skipUnless(sys.platform.startswith("win"),
                         "only Windows refuses to delete a file in use")
    def test_a_held_build_is_waited_for_rather_than_left(self):
        # the launch an update starts races the build it replaced, which is
        # still shutting down; patience is what wins that race
        displaced = self.exe + updates.DISPLACED
        shutil.copy(self.exe, displaced)
        holding = open(displaced, "rb")
        try:
            self.assertFalse(updates.clear_displaced())
            threading.Timer(0.5, holding.close).start()
            self.assertTrue(updates.clear_displaced(updates.PATIENCE))
        finally:
            holding.close()
        self.assertFalse(os.path.isfile(displaced))


class ReleaseTests(unittest.TestCase):
    """The two ends of the fingerprint file, which have to agree.

    build.py writes it and updates.py reads it, and nothing else would notice
    the day one of them changed the name or the format.
    """

    def test_the_build_writes_the_file_the_updater_looks_for(self):
        import build
        self.assertEqual(build.SUMS_NAME, updates.SUMS)

    def test_what_the_build_writes_is_what_the_updater_reads(self):
        import build
        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder, True)
        asset = os.path.join(folder, "Structura.exe")
        with open(asset, "wb") as file:
            file.write(b"MZ, near enough for a fingerprint")

        was, build.DIST = build.DIST, folder
        try:
            sums = build.write_sums([asset])
        finally:
            build.DIST = was
        self.assertEqual(updates.fingerprints(pathlib.Path(sums).as_uri()),
                         {"Structura.exe": build.digest_of(asset)})


if __name__ == "__main__":
    unittest.main()
