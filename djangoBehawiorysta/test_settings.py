"""Isolated tests: no developer secrets, external SMTP or Google calls."""

import os

os.environ["DJANGO_ENV_FILE"] = ".env.test-does-not-exist"
os.environ["DEBUG"] = "True"
os.environ["SECRET_KEY"] = "test-only-not-for-deployment"

from .settings import *  # noqa: E402,F403

SECRET_KEY = "test-only-not-for-deployment"
DEBUG = False
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
SECURE_SSL_REDIRECT = False
ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
SITE_URL = "https://behawiorysta.warszawa.pl"
CONTACT_RECIPIENTS = ["owner@example.com"]
DEFAULT_FROM_EMAIL = "noreply@example.com"
RECAPTCHA_ENABLED = True
RECAPTCHA_PRIVATE_KEY = "test-private-key"
RECAPTCHA_HOSTNAMES = ["behawiorysta.warszawa.pl"]
TRUST_PROXY_IP = False
CONTACT_ATTEMPT_LIMIT = 5
CONTACT_SEND_LIMIT = 3
