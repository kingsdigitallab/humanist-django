from django.db import models
from django.contrib.auth.models import User
from datetime import datetime, timezone
import os
import random
import string
from .helpers import UserEmail
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
# This class handles any non-standard user operations


class Subscriber(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    bio = models.TextField(blank=True, null=True)
    pw_reset_key = models.CharField(null=True, blank=True, max_length=128)
    pw_reset_date = models.DateTimeField(blank=True, null=True)

    def generate_password_reset_key(self):
        self.pw_reset_key = ''.join(
            random.choice(string.ascii_uppercase +
                          string.ascii_lowercase +
                          string.digits) for _ in range(128))
        self.pw_reset_date = datetime.now(timezone.utc)
        self.save()

        email = UserEmail(self.user)
        email.subject = "Humanist Password Reset"
        email.body = (
            "Dear {},\n\n"
            "We have received a request to reset your Humanist password. "
            "To reset your password, please click the following link, or "
            "copy it into your browser:\n\n"
            "{}/user/reset?email={}&key={} \n\n"
            "Kind Regards,\n Humanist").format(self.user.first_name,
                                               settings.BASE_URL,
                                               self.user.email,
                                               self.pw_reset_key)
        email.send()

        return self.pw_reset_key

    def validate_password_reset_key(self, key):
        if self.pw_reset_key and self.pw_reset_date:
            timedelta = datetime.now(timezone.utc) - self.pw_reset_date

            if timedelta.days == 0:
                return True
                if self.pw_reset_key == key:
                    return True
                else:
                    return False
            else:
                self.pw_reset_key = None
                self.pw_reset_date = None
                self.save()
                return False
        else:
            return False

    def __str__(self):
        return self.user


class Edition(models.Model):
    subject = models.CharField(blank=True, null=True, max_length=2048)
    date_created = models.DateTimeField(
        blank=False, null=False, auto_now_add=True)
    date_modified = models.DateTimeField(
        blank=False, null=False, auto_now=True)
    date_sent = models.DateTimeField(blank=True, null=True)
    sent = models.BooleanField(blank=False, default=False)

    class Meta:
        ordering = ['-date_created']

    @classmethod
    def get_drafts(cls):
        return cls.objects.filter(sent=False)

    @classmethod
    def get_sent(cls):
        return cls.objects.filter(sent=True)

    def __str__(self):
        return self.subject


class IncomingEmail(models.Model):
    body = models.TextField(blank=True, null=True)
    body_html = models.TextField(blank=True, null=True)
    date = models.DateTimeField(blank=True, null=True)
    raw = models.TextField(blank=True, null=True)
    sender = models.CharField(blank=True, null=True, max_length=256)
    subject = models.CharField(blank=True, null=True, max_length=2048)

    used = models.BooleanField(null=False, default=False)
    deleted = models.BooleanField(null=False, default=False)
    processed = models.BooleanField(null=False, default=False)
    log = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-date']

    @classmethod
    def get_available(cls):
        # users = list(
        #    User.objects.filter(is_active=True).values_list(
        #    'email', flat=True))
        # return cls.objects.annotate(sender_lower=Lower('sender')).filter(
        #    deleted=False).filter(
        #    used=False).filter(
        #    processed=True).filter(
        #    sender_lower__in=users)
        return cls.objects.filter(
            deleted=False).filter(
            processed=True).filter(
            used=False)

    def __str__(self):
        return '{} - {}'.format(self.sender, self.subject)

    @classmethod
    def get_deleted(cls):
        return cls.objects.filter(deleted=True)

    @classmethod
    def get_unused(cls):
        return cls.objects.filterc(used=False)

    @classmethod
    def get_used(cls):
        return cls.objects.filter(
            used=True).filter(
            processed=True).filter(
            deleted=False)

    @property
    def attachments(self):
        return self.attachment_set.all()

    @property
    def user(self):
        try:
            return User.objects.get(email=self.sender)
        except ObjectDoesNotExist:
            return 'Unknown Sender'


class EditedEmail(models.Model):
    edition = models.ForeignKey(Edition, on_delete=models.CASCADE)
    body = models.TextField(blank=True, null=True)
    date_created = models.DateTimeField(
        blank=False, null=False, auto_now_add=True)
    date_modified = models.DateTimeField(
        blank=False, null=False, auto_now=True)
    subject = models.CharField(blank=True, null=True, max_length=2048)
    sender = models.CharField(blank=False, null=False, max_length=256)
    incoming = models.ForeignKey(IncomingEmail, on_delete=models.CASCADE)

    class Meta:
        ordering = ['-date_created']

    @property
    def attachments(self):
        return self.incoming.attachments

    @property
    def user(self):
        return self.incoming.user

    def __str__(self):
        return '{} - {}'.format(self.sender, self.subject)


class Attachment(models.Model):
    email = models.ForeignKey(IncomingEmail, on_delete=models.CASCADE)
    original_filename = models.CharField(max_length=255,
                                         blank=False,
                                         null=False)
    stored_filename = models.CharField(max_length=255,
                                       blank=False,
                                       null=False)
    mimetype = models.CharField(max_length=128,
                                blank=False,
                                null=False)

    class Meta:
        ordering = ['id']

    @property
    def date(self):
        return self.email.date

    @property
    def path(self):
        return os.path.join(settings.EMAIL_ATTACHMENT_PATH,
                            str(self.email.id),
                            str(self.stored_filename))

    def __str__(self):
        return '{} ({})'.format(self.original_filename, self.email)
