"""Render a real local preview; never sends messages or modifies the production DB."""

import argparse
import os
import sys
import threading
from pathlib import Path
from wsgiref.simple_server import make_server

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ["DJANGO_SETTINGS_MODULE"] = "djangoBehawiorysta.test_settings"

import django  # noqa: E402
from django.contrib.staticfiles.handlers import StaticFilesHandler  # noqa: E402
from django.core.wsgi import get_wsgi_application  # noqa: E402
from django.test.utils import override_settings  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--channel", default=None, help="e.g. msedge; otherwise installed Chromium")
    args = parser.parse_args()
    django.setup()
    with override_settings(
        RECAPTCHA_ENABLED=False, CONTACT_PHONE="+48123456789", CONTACT_EMAIL="contact@example.com"
    ):
        server = make_server("127.0.0.1", 0, StaticFilesHandler(get_wsgi_application()))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True, channel=args.channel)
                page = browser.new_page(
                    viewport={"width": 1440, "height": 1000}, device_scale_factor=1
                )
                page.goto(f"http://127.0.0.1:{server.server_port}/", wait_until="networkidle")
                page.evaluate("document.fonts.ready")
                page.locator('img[loading="lazy"]').evaluate_all(
                    "images => images.forEach(img => img.loading = 'eager')"
                )
                page.wait_for_function(
                    "Array.from(document.images).every(img => img.complete && img.naturalWidth > 0)"
                )
                if page.locator(".cc-dismiss").is_visible():
                    page.locator(".cc-dismiss").click()
                # Acceptance starts a fade-out; wait before capturing the full page.
                page.locator(".cc-window").wait_for(state="hidden")
                assert page.locator("h1").count() == 1
                assert page.locator(".service-card").count() == 6
                assert page.locator("#contact").count() == 1
                assert page.locator("#id_message").get_attribute("maxlength") == "4000"
                destination = ROOT / "docs" / "screenshot.png"
                destination.parent.mkdir(exist_ok=True)
                page.screenshot(path=str(destination), full_page=True)
                page.set_viewport_size({"width": 390, "height": 844})
                page.locator(".cc-window").wait_for(state="hidden")
                page.screenshot(path=str(ROOT / "docs" / "mobile.png"), full_page=True)
                assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
                browser.close()
                print("Screenshot captured; desktop and mobile layout checks passed.")
        finally:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    main()
