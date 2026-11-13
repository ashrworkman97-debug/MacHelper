from __future__ import print_function
import os
import shutil
import tempfile
import unittest

from machelperlib import files


class FileWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.old_home = os.environ.get("HOME")
        self.home = tempfile.mkdtemp(prefix="machelper-test-")
        os.environ["HOME"] = self.home
        self.root = os.path.join(self.home, "Downloads")
        os.mkdir(self.root)

    def tearDown(self):
        if self.old_home is None:
            os.environ.pop("HOME", None)
        else:
            os.environ["HOME"] = self.old_home
        shutil.rmtree(self.home)

    def make_file(self, name, body="test data"):
        path = os.path.join(self.root, name)
        handle = open(path, "w")
        try:
            handle.write(body)
        finally:
            handle.close()
        return path

    def test_plan_is_preview_then_apply_and_undo(self):
        source = self.make_file("photo.jpg")
        plan = files.make_rule_plan(self.root)
        self.assertEqual(plan["status"], "pending")
        self.assertTrue(os.path.isfile(source), "planning must not move files")
        self.assertEqual(len(plan["operations"]), 1)
        journal = files.apply_plan(plan["id"])
        moved = os.path.join(self.root, "Images", "photo.jpg")
        self.assertTrue(os.path.isfile(moved))
        self.assertFalse(os.path.exists(source))
        restored = files.undo_journal(journal["id"])
        self.assertEqual(restored, 1)
        self.assertTrue(os.path.isfile(source))
        self.assertFalse(os.path.exists(moved))

    def test_ai_cannot_escape_selected_folder(self):
        source = self.make_file("notes.txt")
        outside = os.path.join(self.home, "outside.txt")
        handle = open(outside, "w")
        handle.write("outside")
        handle.close()
        operation = {"action": "trash", "source": outside, "reason": "test"}
        self.assertRaises(ValueError, files.validate_ai_operations, self.root, [operation])
        self.assertTrue(os.path.isfile(source))
        self.assertTrue(os.path.isfile(outside))

    def test_existing_destination_is_never_overwritten(self):
        source = self.make_file("photo.jpg", "original")
        target_folder = os.path.join(self.root, "Images")
        os.mkdir(target_folder)
        target = os.path.join(target_folder, "photo.jpg")
        handle = open(target, "w")
        handle.write("keep this")
        handle.close()
        plan = files.make_rule_plan(self.root)
        self.assertRaises(ValueError, files.apply_plan, plan["id"])
        self.assertTrue(os.path.isfile(source))
        handle = open(target, "r")
        try:
            self.assertEqual(handle.read(), "keep this")
        finally:
            handle.close()

    def test_trash_action_can_be_undone(self):
        source = self.make_file("old-temp.tmp")
        plan = files.save_plan(self.root, [{
            "action": "trash", "source": source, "reason": "approved test"
        }], "test")
        journal = files.apply_plan(plan["id"])
        self.assertFalse(os.path.exists(source))
        self.assertTrue(os.path.isfile(journal["entries"][0]["destination"]))
        self.assertEqual(files.undo_journal(journal["id"]), 1)
        self.assertTrue(os.path.isfile(source))

    def test_partial_apply_records_undo_journal(self):
        first = self.make_file("a.jpg", "first")
        second = self.make_file("b.jpg", "second")
        target_folder = os.path.join(self.root, "Images")
        os.mkdir(target_folder)
        conflict = os.path.join(target_folder, "b.jpg")
        handle = open(conflict, "w")
        handle.write("keep this")
        handle.close()

        plan = files.make_rule_plan(self.root)
        try:
            files.apply_plan(plan["id"])
            self.fail("The conflicting destination should stop the apply.")
        except RuntimeError as error:
            marker = "machelper files undo "
            self.assertIn(marker, str(error))
            journal_id = str(error).split(marker, 1)[1].strip()

        self.assertFalse(os.path.exists(first))
        self.assertTrue(os.path.isfile(second))
        self.assertEqual(files.undo_journal(journal_id), 1)
        self.assertTrue(os.path.isfile(first))
        handle = open(conflict, "r")
        try:
            self.assertEqual(handle.read(), "keep this")
        finally:
            handle.close()


if __name__ == "__main__":
    unittest.main()
