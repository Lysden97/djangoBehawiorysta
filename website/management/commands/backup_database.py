"""Consistent SQLite snapshot using SQLite's online backup API."""

import sqlite3
from contextlib import closing
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Create a consistent SQLite backup at a NEW destination path."

    def add_arguments(self, parser):
        parser.add_argument("destination")

    def handle(self, *args, **options):
        destination = Path(options["destination"]).resolve()
        source = Path(settings.DATABASES["default"]["NAME"]).resolve()
        if not source.is_file():
            raise CommandError("Source database does not exist.")
        try:
            with destination.open("xb"):
                pass
        except FileExistsError as error:
            raise CommandError("Destination already exists; choose a new path.") from error
        destination.chmod(0o600)
        with closing(sqlite3.connect(f"{source.as_uri()}?mode=ro", uri=True)) as src:
            with closing(sqlite3.connect(destination)) as dst:
                src.backup(dst)
        self.stdout.write("SQLite snapshot created.")
