import json
import os
import runpy
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.conf import settings
from django.contrib.staticfiles.storage import staticfiles_storage
from django.core.management import call_command
from django.test import SimpleTestCase, override_settings


def application_settings(debug):
    """Load the actual config with synthetic credentials and no developer dotenv file."""
    environment = {
        "DJANGO_ENV_FILE": ".env.test-does-not-exist",
        "DEBUG": str(debug),
        "SECRET_KEY": "staticfiles-test-only",
        "SITE_URL": "https://example.test",
        "ALLOWED_HOSTS": "example.test",
        "CSRF_TRUSTED_ORIGINS": "https://example.test",
        "DEFAULT_FROM_EMAIL": "sender@example.test",
        "CONTACT_RECIPIENTS": "owner@example.test",
        "CONTACT_EMAIL": "owner@example.test",
        "EMAIL_HOST": "smtp.example.test",
        "RECAPTCHA_PUBLIC_KEY": "test-public-key",
        "RECAPTCHA_PRIVATE_KEY": "test-private-key",
    }
    with patch.dict(os.environ, environment, clear=True):
        return runpy.run_path(str(settings.BASE_DIR / "djangoBehawiorysta/settings.py"))


class StaticFilesTests(SimpleTestCase):
    def test_storage_selection(self):
        self.assertEqual(
            application_settings(False)["STORAGES"]["staticfiles"]["BACKEND"],
            "django.contrib.staticfiles.storage.ManifestStaticFilesStorage",
        )
        self.assertEqual(
            application_settings(True)["STORAGES"]["staticfiles"]["BACKEND"],
            "django.contrib.staticfiles.storage.StaticFilesStorage",
        )
        self.assertEqual(
            settings.STORAGES["staticfiles"]["BACKEND"],
            "django.contrib.staticfiles.storage.StaticFilesStorage",
        )

    def test_manifest_versions_assets_and_preserves_previous_files(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source, collected = root / "source", root / "collected"
            shutil.copytree(settings.BASE_DIR / "static", source)
            with override_settings(
                DEBUG=False,
                STORAGES=application_settings(False)["STORAGES"],
                STATICFILES_DIRS=[source],
                STATIC_ROOT=collected,
            ):
                call_command("collectstatic", interactive=False, verbosity=0)
                manifest = json.loads((collected / "staticfiles.json").read_text())
                assets = ("website/css/site.css", "website/js/site.js")
                urls = {name: staticfiles_storage.url(name) for name in assets}
                response = self.client.get("/")
                self.assertEqual(response.status_code, 200)
                for name, url in urls.items():
                    self.assertRegex(url, r"\.[0-9a-f]{12}\.(css|js)$")
                    self.assertContains(response, url)
                    self.assertTrue((collected / manifest["paths"][name]).is_file())

                font = "website/webfonts/fa-solid-900.woff2"
                css = collected / manifest["paths"]["website/css/fontawesome-all.min.css"]
                self.assertIn(Path(manifest["paths"][font]).name, css.read_text())
                self.assertTrue((collected / manifest["paths"][font]).is_file())
                with self.assertRaisesMessage(ValueError, "Missing staticfiles manifest entry"):
                    staticfiles_storage.url("website/missing.js")

                for name in assets:
                    path = source / name
                    path.write_bytes(path.read_bytes() + b"\n/* next deployment */\n")
                    # collectstatic compares mtimes at whole-second precision.
                    newer = (collected / name).stat().st_mtime + 2
                    os.utime(path, (newer, newer))
                call_command("collectstatic", interactive=False, verbosity=0)
                for name, old_url in urls.items():
                    new_url = staticfiles_storage.url(name)
                    self.assertNotEqual(new_url, old_url)
                    self.assertTrue(
                        (collected / old_url.removeprefix(settings.STATIC_URL)).is_file()
                    )
                    self.assertTrue(
                        (collected / new_url.removeprefix(settings.STATIC_URL)).is_file()
                    )
