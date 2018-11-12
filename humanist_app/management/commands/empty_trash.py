from django.core.management.base import BaseCommand
from ...models import IncomingEmail
from datetime import timedelta
from django.utils import timezone


class Command(BaseCommand):
    help = 'Sends an email digest!'

    def handle(self, *args, **options):
        # Fetch last 7 days worth of editions:
        last_week = timezone.now().date() - timedelta(days=7)

        emails = IncomingEmail.get_deleted().filter(
            date__gte=last_week)
        for e in emails:
            e.purged = True
            e.save()
