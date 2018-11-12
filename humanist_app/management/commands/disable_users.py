from django.core.management.base import BaseCommand
from ...models import Subscriber
from django.conf import settings


class Command(BaseCommand):
    help = 'Disabled unnecessary users'

    def handle(self, *args, **options):
        list_to_disable = Subscriber.objects.filter(
            user__is_active=True).filter(
            bounce_count__gte=10).filter(
            bounce_disabled=False)

        for u in list_to_disable.all():
            u.bounce_disabled = True
            u.save()

        user_list = '\n'.join(Subscriber.objects.filter(
            user__is_active=True).filter(
            bounce_disabled=False).filter(
            digest=False).values_list(
            'user__email', flat=True))
        try:
            with open(settings.EMAIL_ALLOW_LIST, 'w') as f:
                f.write(user_list)
        except IOError:
            pass
