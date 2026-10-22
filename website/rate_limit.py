import ipaddress
from dataclasses import dataclass
from datetime import datetime, timezone

from django.conf import settings
from django.db.models import F
from django.utils.crypto import salted_hmac
from django.utils.timezone import now

from .models import RateLimitBucket


@dataclass(frozen=True)
class Reservation:
    key: str | None
    retry_after: int = 0


def client_identity(request):
    # Only enable this behind our Nginx: it overwrites X-Real-IP and the app
    # port is NOT published. Arbitrary X-Forwarded-For is never trusted.
    raw = (
        request.META.get("HTTP_X_REAL_IP", "")
        if settings.TRUST_PROXY_IP
        else request.META.get("REMOTE_ADDR", "")
    )
    try:
        raw = str(ipaddress.ip_address(raw))
    except ValueError:
        raw = "unknown"
    return salted_hmac("contact-rate-limit", raw).hexdigest()


def reserve(identity, scope, limit, seconds):
    timestamp = int(now().timestamp())
    window = timestamp // seconds
    key = f"{scope}:{identity}:{window}"
    window_end = (window + 1) * seconds
    expires = datetime.fromtimestamp(window_end, tz=timezone.utc)
    RateLimitBucket.objects.get_or_create(key=key, defaults={"expires_at": expires})
    accepted = RateLimitBucket.objects.filter(key=key, count__lt=limit).update(count=F("count") + 1)
    if accepted:
        return Reservation(key=key)
    # timestamp is rounded down, so even a fractional last second waits 1s.
    return Reservation(key=None, retry_after=window_end - timestamp)


def release(key):
    RateLimitBucket.objects.filter(key=key, count__gt=0).update(count=F("count") - 1)
