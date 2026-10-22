import logging
from smtplib import SMTPException

from django.conf import settings
from django.contrib import messages
from django.db import DatabaseError
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils.html import escape
from django.views import View
from django.views.generic import TemplateView

from .catalog import SERVICES
from .forms import ContactForm
from .rate_limit import client_identity, release, reserve
from .seo import homepage_structured_data
from .services import send_contact_email, verify_recaptcha

logger = logging.getLogger(__name__)


def homepage_context(form=None):
    structured = homepage_structured_data()
    return {
        "form": form if form is not None else ContactForm(),
        "services": SERVICES,
        "structured_data": structured,
    }


class IndexView(TemplateView):
    template_name = "index.html"

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), **homepage_context()}


class PrivacyPolicyView(TemplateView):
    template_name = "privacy-policy.html"


class ContactView(View):
    def get(self, request):
        return redirect("/#contact", permanent=True)

    def post(self, request):
        form = ContactForm(request.POST)

        def failure(message, status, retry_after=None):
            form.is_valid()
            form.add_error(None, message)
            response = render(request, "index.html", homepage_context(form), status=status)
            response["Cache-Control"] = "no-store"
            response["X-Robots-Tag"] = "noindex"
            if retry_after is not None:
                response["Retry-After"] = str(retry_after)
            return response

        try:
            identity = client_identity(request)
            attempt = reserve(identity, "attempt", settings.CONTACT_ATTEMPT_LIMIT, 900)
            if attempt.key is None:
                return failure(
                    "Zbyt wiele prób. Spróbuj ponownie później.", 429, attempt.retry_after
                )
            if not form.is_valid():
                return failure("Popraw zaznaczone pola.", 400)
            if not verify_recaptcha(request.POST.get("g-recaptcha-response", "")):
                return failure(
                    "Nie udało się potwierdzić reCAPTCHA. Wykonaj weryfikację ponownie.", 400
                )
            delivery = reserve(identity, "send", settings.CONTACT_SEND_LIMIT, 3600)
            if delivery.key is None:
                return failure(
                    "Osiągnięto limit wiadomości. Spróbuj ponownie później.",
                    429,
                    delivery.retry_after,
                )
        except DatabaseError:
            logger.error("contact_rate_limit_unavailable")
            return failure("Formularz jest chwilowo niedostępny. Spróbuj ponownie później.", 503)

        try:
            if send_contact_email(form.cleaned_data) != 1:
                raise SMTPException("No message accepted")
        except (SMTPException, OSError):
            logger.error("contact_delivery_failed")
            try:
                release(delivery.key)
            except DatabaseError:
                logger.error("contact_rate_limit_release_failed")
            return failure(
                "Nie udało się wysłać wiadomości. Spróbuj ponownie później lub skontaktuj się telefonicznie.",
                503,
            )
        messages.success(
            request, "Twoje zgłoszenie zostało wysłane. Termin potwierdzimy w odpowiedzi."
        )
        return redirect("/#contact")


def robots_txt(request):
    return HttpResponse(
        f"User-agent: *\nAllow: /\nSitemap: {settings.SITE_URL}/sitemap.xml\n",
        content_type="text/plain; charset=utf-8",
    )


def sitemap_xml(request):
    content = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>{escape(settings.SITE_URL)}/</loc></url>
</urlset>"""
    return HttpResponse(content, content_type="application/xml; charset=utf-8")
