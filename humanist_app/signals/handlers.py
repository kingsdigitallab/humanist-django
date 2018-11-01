from django.db.models.signals import pre_save, post_save
from django.contrib.auth.models import User
from django.conf import settings
from humanist_app.models import Subscriber


def build_user_list(sender, instance, signal, *args, **kwargs):
    if sender is User or sender is Subscriber:
        user_list = '\n'.join(Subscriber.objects.filter(
            user__is_active=True).filter(
            digest=False).values_list(
            'user__email', flat=True))
        try:
            with open(settings.EMAIL_ALLOW_LIST, 'w') as f:
                f.write(user_list)
        except IOError:
            pass


post_save.connect(build_user_list, sender=User)


def user_save(sender, instance, signal, *args, **kwargs):
    if sender is User:
        email = instance.email.lower()
        instance.email = email
        instance.username = email


pre_save.connect(user_save, sender=User)
