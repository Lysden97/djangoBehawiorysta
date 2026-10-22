from datetime import UTC, date, datetime, timedelta
from smtplib import SMTPException
from unittest.mock import Mock, patch

import requests
from django.core import mail
from django.core.management import call_command
from django.db import OperationalError
from django.test import Client, RequestFactory, TestCase, override_settings
from django.utils import timezone

from .forms import ContactForm
from .models import RateLimitBucket
from .rate_limit import client_identity, reserve
from .services import verify_recaptcha


def valid_data(**changes):
    return {
        "name": "Jan",
        "last_name": "Kowalski",
        "email": "jan@example.com",
        "phone": "+48 507 246 814",
        "address": "",
        "preferred_date": (timezone.localdate() + timedelta(days=1)).isoformat(),
        "animal_info": "Burek, 3 lata",
        "animal_breed": "Pies",
        "gender": "Samiec - niekastrowany",
        "appointment_type": "first",
        "message": "Proszę o pomoc w treningu psa.",
        "terms": "on",
        "privacy_policy": "on",
        "g-recaptcha-response": "test-token",
        **changes,
    }


class FormTests(TestCase):
    def test_valid_data_and_optional_address(self):
        self.assertTrue(ContactForm(valid_data()).is_valid())

    @patch("website.forms.timezone.localdate", return_value=date(2026, 10, 22))
    def test_preferred_date_includes_today_and_ninetieth_day(self, localdate):
        for days in (0, 90):
            with self.subTest(days=days):
                preferred = localdate.return_value + timedelta(days=days)
                form = ContactForm(valid_data(preferred_date=preferred.isoformat()))
                self.assertTrue(form.is_valid(), form.errors)
                self.assertEqual(form.cleaned_data["preferred_date"], preferred)

    @patch("website.forms.timezone.localdate", return_value=date(2026, 10, 22))
    def test_preferred_date_rejects_days_outside_inclusive_window(self, localdate):
        for days in (-1, 91):
            with self.subTest(days=days):
                preferred = localdate.return_value + timedelta(days=days)
                form = ContactForm(valid_data(preferred_date=preferred.isoformat()))
                self.assertFalse(form.is_valid())
                self.assertIn("preferred_date", form.errors)

    def test_invalid_fields(self):
        cases = {
            "name": [" ", "a" * 81],
            "last_name": ["b" * 101],
            "email": ["invalid", "jan@example.com\r\nBcc: other@example.com"],
            "phone": ["---------", "123", "abc123456789"],
            "message": ["short", "x" * 4001],
            "address": ["x" * 201],
            "animal_info": ["x" * 151],
            "animal_breed": ["x" * 151],
            "terms": ["", False],
            "privacy_policy": ["", False],
            "appointment_type": ["forged-price", ""],
            "gender": ["unknown"],
            "preferred_date": [
                "invalid",
                (timezone.localdate() - timedelta(days=1)).isoformat(),
                (timezone.localdate() + timedelta(days=91)).isoformat(),
            ],
        }
        for field, values in cases.items():
            for value in values:
                with self.subTest(field=field, value=str(value)[:25]):
                    form = ContactForm(valid_data(**{field: value}))
                    self.assertFalse(form.is_valid())
                    self.assertIn(field, form.errors)


class ContactTests(TestCase):
    def setUp(self):
        verifier = patch("website.views.verify_recaptcha", return_value=True)
        self.verify = verifier.start()
        self.addCleanup(verifier.stop)

    def test_delivery_headers_and_service_price(self):
        response = self.client.post("/contact/", valid_data())
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.from_email, "noreply@example.com")
        self.assertEqual(message.reply_to, ["jan@example.com"])
        self.assertEqual(message.to, ["owner@example.com"])
        self.assertIn("300 zł", message.body)

    def test_text_email_contains_complete_request_without_template_css(self):
        submitted = valid_data(address="Warszawa, Mokotów")
        self.assertEqual(self.client.post("/contact/", submitted).status_code, 302)
        body = mail.outbox[0].body
        self.assertNotIn("font-family:", body)
        self.assertNotIn(".container {", body)
        for field in (
            "name",
            "last_name",
            "email",
            "phone",
            "address",
            "preferred_date",
            "animal_info",
            "animal_breed",
            "gender",
            "message",
        ):
            with self.subTest(field=field):
                self.assertIn(submitted[field], body)
        self.assertIn("Pierwsza konsultacja behawioralna (300 zł)", body)

    def test_text_email_preserves_literal_input_while_html_escapes_it(self):
        content = "Zażółć gęślą jaźń: a < b, c > d & \"cytat\" oraz 'apostrof'.\n<b>Łatka</b> &lt;"
        self.assertEqual(
            self.client.post("/contact/", valid_data(message=content)).status_code, 302
        )
        message = mail.outbox[0]
        self.assertIn(content, message.body)
        self.assertEqual(len(message.alternatives), 1)
        html = message.alternatives[0]
        self.assertEqual(html.mimetype, "text/html")
        self.assertIn("a &lt; b, c &gt; d &amp; &quot;cytat&quot;", html.content)
        self.assertIn("&#x27;apostrof&#x27;", html.content)
        self.assertIn("&lt;b&gt;Łatka&lt;/b&gt; &amp;lt;", html.content)
        self.assertNotIn("<b>Łatka</b>", html.content)
        parts = message.message().get_payload()
        self.assertEqual([part.get_content_type() for part in parts], ["text/plain", "text/html"])

    def test_text_email_labels_missing_optional_address(self):
        self.assertEqual(self.client.post("/contact/", valid_data(address="")).status_code, 302)
        self.assertIn("Dzielnica / miejscowość: Nie podano", mail.outbox[0].body)

    def test_invalid_form_preserves_values_without_external_call(self):
        response = self.client.post("/contact/", valid_data(terms=""))
        self.assertContains(response, 'value="Jan"', status_code=400)
        self.verify.assert_not_called()
        self.assertFalse(mail.outbox)

    def test_captcha_failure_does_not_send(self):
        self.verify.return_value = False
        self.assertEqual(self.client.post("/contact/", valid_data()).status_code, 400)
        self.assertFalse(mail.outbox)

    def test_smtp_failure_retains_input_and_releases_send_quota(self):
        for error in [SMTPException("secret smtp details"), TimeoutError("timeout")]:
            with (
                self.subTest(error=type(error)),
                patch("website.views.send_contact_email", side_effect=error),
            ):
                response = self.client.post("/contact/", valid_data())
                self.assertContains(response, 'value="Jan"', status_code=503)
                self.assertNotContains(response, "secret smtp details", status_code=503)
                self.assertEqual(response["Cache-Control"], "no-store")
                self.assertEqual(RateLimitBucket.objects.get(key__startswith="send:").count, 0)

    def test_zero_messages_is_failure(self):
        with patch("website.views.send_contact_email", return_value=0):
            self.assertEqual(self.client.post("/contact/", valid_data()).status_code, 503)

    @override_settings(CONTACT_ATTEMPT_LIMIT=2)
    def test_attempt_limit_counts_invalid_forms(self):
        self.client.post("/contact/", {})
        self.client.post("/contact/", {})
        response = Client().post("/contact/", {})
        self.assertEqual(response.status_code, 429)
        self.assertIn("Retry-After", response)

    @override_settings(CONTACT_SEND_LIMIT=1)
    def test_send_limit_shared_between_clients(self):
        self.assertEqual(self.client.post("/contact/", valid_data()).status_code, 302)
        self.assertEqual(Client().post("/contact/", valid_data()).status_code, 429)
        self.assertEqual(len(mail.outbox), 1)

    @override_settings(CONTACT_ATTEMPT_LIMIT=1)
    def test_attempt_retry_after_tracks_window_and_expires(self):
        start = datetime(2026, 10, 22, 12, tzinfo=UTC)
        with patch("website.rate_limit.now", return_value=start) as clock:
            self.assertEqual(self.client.post("/contact/", {}).status_code, 400)
            for seconds, remaining in ((0, 900), (120, 780), (899.5, 1)):
                with self.subTest(seconds=seconds):
                    clock.return_value = start + timedelta(seconds=seconds)
                    response = self.client.post("/contact/", {})
                    self.assertEqual(response.status_code, 429)
                    self.assertEqual(response["Retry-After"], str(remaining))
            clock.return_value = start + timedelta(seconds=900)
            response = self.client.post("/contact/", {})
            self.assertEqual(response.status_code, 400)
            self.assertNotIn("Retry-After", response)
        self.verify.assert_not_called()

    @override_settings(CONTACT_SEND_LIMIT=1)
    def test_send_retry_after_tracks_window_and_expires(self):
        start = datetime(2026, 10, 22, 12, tzinfo=UTC)
        with patch("website.rate_limit.now", return_value=start) as clock:
            self.assertEqual(self.client.post("/contact/", valid_data()).status_code, 302)
            for seconds, remaining in ((0, 3600), (120, 3480), (3599.5, 1)):
                with self.subTest(seconds=seconds):
                    clock.return_value = start + timedelta(seconds=seconds)
                    response = self.client.post("/contact/", valid_data())
                    self.assertEqual(response.status_code, 429)
                    self.assertEqual(response["Retry-After"], str(remaining))
            clock.return_value = start + timedelta(seconds=3600)
            response = self.client.post("/contact/", valid_data())
            self.assertEqual(response.status_code, 302)
            self.assertNotIn("Retry-After", response)
        self.assertEqual(len(mail.outbox), 2)

    def test_csrf_required(self):
        self.assertEqual(
            Client(enforce_csrf_checks=True).post("/contact/", valid_data()).status_code, 403
        )

    def test_database_failure_fails_closed(self):
        with patch("website.views.reserve", side_effect=OperationalError):
            self.assertEqual(self.client.post("/contact/", valid_data()).status_code, 503)
        self.verify.assert_not_called()


class CaptchaTests(TestCase):
    @patch("website.services.requests.post")
    def test_success_requires_expected_hostname(self, post):
        post.return_value = Mock(
            **{"json.return_value": {"success": True, "hostname": "behawiorysta.warszawa.pl"}}
        )
        self.assertTrue(verify_recaptcha("token"))
        self.assertEqual(post.call_args.kwargs["timeout"], (3, 5))
        for result in [
            {"success": True, "hostname": "attacker.example"},
            {"success": False},
            [],
            None,
            {"success": "true"},
        ]:
            post.return_value.json.return_value = result
            self.assertFalse(verify_recaptcha("token"))

    @patch("website.services.requests.post")
    def test_network_errors(self, post):
        for error in [requests.Timeout, requests.ConnectionError, requests.HTTPError]:
            post.side_effect = error
            self.assertFalse(verify_recaptcha("token"))

    @patch("website.services.requests.post")
    def test_malformed_json_and_http_status(self, post):
        post.return_value.json.side_effect = ValueError
        self.assertFalse(verify_recaptcha("token"))
        post.return_value.raise_for_status.side_effect = requests.HTTPError
        self.assertFalse(verify_recaptcha("token"))

    @patch("website.services.requests.post")
    def test_missing_or_oversized_token(self, post):
        self.assertFalse(verify_recaptcha(""))
        self.assertFalse(verify_recaptcha("a" * 4097))
        post.assert_not_called()


class RateLimitTests(TestCase):
    def test_ip_headers_ignored_by_default(self):
        factory = RequestFactory()
        first = factory.get("/", REMOTE_ADDR="192.0.2.1", HTTP_X_REAL_IP="192.0.2.2")
        second = factory.get("/", REMOTE_ADDR="192.0.2.1", HTTP_X_FORWARDED_FOR="192.0.2.3")
        self.assertEqual(client_identity(first), client_identity(second))

    @override_settings(TRUST_PROXY_IP=True)
    def test_nginx_header_used_when_explicitly_enabled(self):
        factory = RequestFactory()
        self.assertNotEqual(
            client_identity(factory.get("/", HTTP_X_REAL_IP="192.0.2.1")),
            client_identity(factory.get("/", HTTP_X_REAL_IP="192.0.2.2")),
        )

    def test_window_expiry_and_cleanup(self):
        start = timezone.now().replace(minute=0, second=0, microsecond=0)
        with patch("website.rate_limit.now", return_value=start):
            self.assertIsNotNone(reserve("identity", "test", 1, 900).key)
            self.assertIsNone(reserve("identity", "test", 1, 900).key)
        with patch("website.rate_limit.now", return_value=start + timedelta(minutes=16)):
            self.assertIsNotNone(reserve("identity", "test", 1, 900).key)
        RateLimitBucket.objects.update(expires_at=timezone.now() - timedelta(days=1))
        call_command("cleanup_rate_limits")
        self.assertEqual(RateLimitBucket.objects.count(), 0)

    def test_retry_after_at_window_boundaries(self):
        start = datetime(2026, 10, 22, 12, tzinfo=UTC)
        for seconds in (900, 3600):
            for offset, remaining in ((0, seconds), (0.5, seconds), (seconds - 0.001, 1)):
                with self.subTest(seconds=seconds, offset=offset):
                    identity = f"{seconds}:{offset}"
                    instant = start + timedelta(seconds=offset)
                    with patch("website.rate_limit.now", return_value=instant) as clock:
                        accepted = reserve(identity, "test", 1, seconds)
                        self.assertIsNotNone(accepted.key)
                        self.assertEqual(accepted.retry_after, 0)
                        rejected = reserve(identity, "test", 1, seconds)
                        self.assertIsNone(rejected.key)
                        self.assertEqual(rejected.retry_after, remaining)
                        self.assertEqual(RateLimitBucket.objects.get(key=accepted.key).count, 1)
                        clock.return_value = start + timedelta(seconds=seconds)
                        renewed = reserve(identity, "test", 1, seconds)
                        self.assertIsNotNone(renewed.key)
                        self.assertNotEqual(renewed.key, accepted.key)
