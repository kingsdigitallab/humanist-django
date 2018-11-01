from django.core.management.base import BaseCommand
from ...models import Subscriber, Edition
from ...helpers import UserEmail
from datetime import timedelta
from django.utils import timezone
from django.template.loader import render_to_string


class Command(BaseCommand):
    help = 'Sends an email digest!'

    def handle(self, *args, **options):
        # Fetch last 7 days worth of editions:
        last_week = timezone.now().date() - timedelta(days=7)

        recipients = Subscriber.objects.filter(
            user__is_active=True).filter(
            digest=True)

        editions = Edition.objects.filter(date_sent__gte=last_week)
        body = render_to_string('includes/digest_template.html',
                                {'editions': editions})

        subject = '[Humanist] Digest'

        for sub in recipients:
            email = UserEmail(sub.user)
            email.subject = subject
            email.body = body
            email.send()
