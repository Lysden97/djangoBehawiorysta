import sqlite3
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase


class BackupTests(SimpleTestCase):
    def test_snapshot_and_overwrite_protection(self):
        with TemporaryDirectory() as directory:
            source = Path(directory) / "source.sqlite3"
            target = Path(directory) / "backup.sqlite3"
            with closing(sqlite3.connect(source)) as connection:
                connection.execute("CREATE TABLE example (value TEXT)")
                connection.execute("INSERT INTO example VALUES ('preserved')")
                connection.commit()
            with patch(
                "website.management.commands.backup_database.settings.DATABASES",
                {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": str(source)}},
            ):
                call_command("backup_database", str(target))
                with closing(sqlite3.connect(target)) as connection:
                    self.assertEqual(
                        connection.execute("SELECT value FROM example").fetchone(), ("preserved",)
                    )
                    self.assertEqual(
                        connection.execute("PRAGMA integrity_check").fetchone(), ("ok",)
                    )
                with self.assertRaises(CommandError):
                    call_command("backup_database", str(target))
                with self.assertRaises(CommandError):
                    call_command("backup_database", str(source))
