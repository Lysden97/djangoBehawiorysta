from django.db import models


class RateLimitBucket(models.Model):
    """Short-lived counters; keys contain an HMAC, never the raw IP address."""

    key = models.CharField(max_length=100, primary_key=True)
    count = models.PositiveIntegerField(default=0)
    expires_at = models.DateTimeField(db_index=True)
