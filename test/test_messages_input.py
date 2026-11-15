"""End-to-end Epic #8 messaging tests using file-based input and output."""

import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
PASSWORD = "Test123!"


def request(sender="alice", receiver="bob", status="ACCEPTED"):
    return f"{sender:<20}{receiver:<20}{status:<10}".rstrip() + "\n"


class MessageFileInputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.build = tempfile.TemporaryDirectory(prefix="incollege-message-build-")
        cls.addClassCleanup(cls.build.cleanup)
        cls.binary = Path(cls.build.name) / "InCollege"
        subprocess.run(
            ["make", f"TARGET={cls.binary}", f"COBC={os.environ.get('COBC', 'cobc')}"],
            cwd=ROOT, check=True, capture_output=True, text=True,
        )

    def setUp(self):
        self.work = tempfile.TemporaryDirectory(prefix="incollege-message-test-")
        self.addCleanup(self.work.cleanup)
        self.directory = Path(self.work.name)
        (self.directory / "InCollege-Accounts.txt").write_text(
            "".join(f"{name:<20}{PASSWORD:<12}\n" for name in ("alice", "bob", "carol"))
        )

    def run_input(self, lines, requests="", username="alice"):
        (self.directory / "InCollege-Requests.txt").write_text(requests)
        (self.directory / "InCollege-Input.txt").write_text(
            "\n".join(["1", username, PASSWORD, *lines]) + "\n"
        )
        result = subprocess.run(
            [str(self.binary)], cwd=self.directory, stdin=subprocess.DEVNULL,
            capture_output=True, text=True, timeout=5, check=True,
        )
        self.assertEqual(result.stderr, "")
        self.assertEqual(result.stdout, (self.directory / "InCollege-Output.txt").read_text())
        return result.stdout

    def test_connected_user_can_send_free_form_message_persistently(self):
        content = "Hi Bob! Want to study COBOL at 3:30?"
        output = self.run_input(["9", "1", "bob", content, "3", "6"], request())
        self.assertIn("Message sent to bob successfully!\n", output)
        record = (self.directory / "InCollege-Messages.txt").read_text().rstrip("\n")
        self.assertEqual(record[:20].strip(), "alice")
        self.assertEqual(record[20:40].strip(), "bob")
        self.assertEqual(len(record[40:61]), 21)
        self.assertEqual(record[61:].rstrip(), content)

    def test_connection_is_valid_in_either_request_direction(self):
        output = self.run_input(
            ["9", "1", "alice", "Reply from Bob", "3", "6"],
            request(), username="bob",
        )
        self.assertIn("Message sent to alice successfully!", output)

    def test_unconnected_pending_and_unknown_users_are_rejected(self):
        for recipient, requests in (
            ("carol", ""),
            ("bob", request(status="PENDING")),
            ("unknown", request()),
        ):
            with self.subTest(recipient=recipient):
                output = self.run_input(["9", "1", recipient, "3", "6"], requests)
                self.assertIn("You can only message users you are connected with.", output)
                self.assertFalse((self.directory / "InCollege-Messages.txt").exists())

    def test_view_messages_placeholder_and_back(self):
        output = self.run_input(["9", "2", "3", "6"])
        self.assertIn("View My Messages is under construction.\n", output)

    def test_message_over_200_characters_is_rejected(self):
        output = self.run_input(["9", "1", "bob", "x" * 201, "3", "6"], request())
        self.assertIn("Message must be 200 characters or fewer.\n", output)
        self.assertFalse((self.directory / "InCollege-Messages.txt").exists())

    def test_empty_message_is_rejected(self):
        output = self.run_input(["9", "1", "bob", "", "3", "6"], request())
        self.assertIn("Message cannot be empty.\n", output)
        self.assertNotIn("Message sent to bob successfully!", output)
        self.assertFalse((self.directory / "InCollege-Messages.txt").exists())

    def test_padded_recipient_is_stored_trimmed(self):
        output = self.run_input(["9", "1", "   bob   ", "Padded", "3", "6"], request())
        self.assertIn("Message sent to bob successfully!\n", output)
        record = (self.directory / "InCollege-Messages.txt").read_text()
        self.assertEqual(record[20:40], f"{'bob':<20}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
