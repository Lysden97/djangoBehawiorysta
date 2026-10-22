from django.conf import settings


def site_config(request):
    return {
        "site_url": settings.SITE_URL,
        "contact_email": settings.CONTACT_EMAIL,
        "contact_phone": settings.CONTACT_PHONE,
        "business_address": settings.BUSINESS_ADDRESS,
        "recaptcha_enabled": settings.RECAPTCHA_ENABLED,
        "recaptcha_public_key": settings.RECAPTCHA_PUBLIC_KEY,
    }
