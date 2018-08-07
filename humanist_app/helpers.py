from django.core.mail import send_mail  # noqa
from django.contrib.auth.models import User

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
            except: # noqa
                return False


# Send an email to all admins
class AdminEmail(Email):
    def __init__(self):
        admins = User.objects.filter(is_staff=True)
        self.to = list(admins.values_list('email', flat=True))
        self.sender = 'Humanist Admin <noreply@kcl.ac.uk>'


# Send an email to all active users
class ActiveUserEmail(Email):
    def __init__(self):
        users = User.objects.filter(is_actve=True)
        self.to = list(users.values_list('email', flat=True))
        # TODO change email to proper one.
        self.sender = 'Humanist <noreply@kcl.ac.uk>'
