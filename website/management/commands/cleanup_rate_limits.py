from django.core.management.base import BaseCommand
from django.utils.timezone import now

from website.models import RateLimitBucket


class Command(BaseCommand):
    help = "Delete expired anonymous rate-limit counters."

    def handle(self, *args, **options):
        count, _ = RateLimitBucket.objects.filter(expires_at__lte=now()).delete()
        self.stdout.write(f"Deleted {count} expired counters.")
