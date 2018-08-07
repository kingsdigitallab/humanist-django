from django.core.mail import send_mail  # noqa
from django.contrib.auth.models import User
from django.conf import settings
# Send a single email


class Email():
    to = None
    sender = None
    subject = None
    body = None

    def send(self):
        if self.to and self.sender and self.subject and self.body:
            try:
                if not type(self.to) == 'list':
                    self.to = [self.to]
                return send_mail(self.subject, self.body, self.sender, self.to)
            except:  # noqa
                return False


# Send an email to all admins
class AdminEmail(Email):
    def __init__(self):
        admins = User.objects.filter(is_staff=True)
        self.to = list(admins.values_list('email', flat=True))
        self.sender = 'Humanist Admin <{}>'.format(settings.DEFAULT_FROM_EMAIL)


# Send an email to all active users
class ActiveUserEmail(Email):
    def __init__(self):
        users = User.objects.filter(is_actve=True)
        self.to = list(users.values_list('email', flat=True))
        if 'PROJECT_FROM_EMAIL' in settings:
            self.sender = 'Humanist <{}>'.format(settings.PROJECT_FROM_EMAIL)
        else:
            self.sender = 'Humanist <{}>'.format(settings.DEFAULT_FROM_EMAIL)


# Send an email to a specific user
class UserEmail(Email):
    def __init__(self, user):
        self.to = user.email
        self.sender = 'Humanist Admin <{}>'.format(settings.DEFAULT_FROM_EMAIL)
