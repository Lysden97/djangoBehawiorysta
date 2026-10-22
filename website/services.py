import logging

import requests
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from .catalog import SERVICES, service_label

logger = logging.getLogger(__name__)


def verify_recaptcha(token):
    if not settings.RECAPTCHA_ENABLED:
        return True
    if not token or len(token) > 4096:
        return False
    try:
        response = requests.post(
            settings.RECAPTCHA_VERIFY_URL,
            data={"secret": settings.RECAPTCHA_PRIVATE_KEY, "response": token},
            timeout=(3, settings.RECAPTCHA_TIMEOUT),
        )
        response.raise_for_status()
        result = response.json()
    except (requests.RequestException, ValueError):
        logger.warning("recaptcha_unavailable")
        return False
    return (
        isinstance(result, dict)
        and result.get("success") is True
        and result.get("hostname") in settings.RECAPTCHA_HOSTNAMES
    )


def send_contact_email(data):
    context = dict(data)
    service = next(s for s in SERVICES if s["id"] == data["appointment_type"])
    context["appointment_type"] = service_label(service)
    html = render_to_string("emails/appointment_notification.html", context)
    text = render_to_string("emails/appointment_notification.txt", context)
    mail = EmailMultiAlternatives(
        subject="Nowe zgłoszenie konsultacji",
        body=text,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=settings.CONTACT_RECIPIENTS,
        reply_to=[data["email"]],
    )
    mail.attach_alternative(html, "text/html")
    return mail.send(fail_silently=False)
