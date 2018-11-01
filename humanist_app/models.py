from django.db import models
from django.contrib.auth.models import User
from datetime import datetime, timezone
import os
import random
import string
from .helpers import UserEmail
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from dateutil.relativedelta import relativedelta


class Subscriber(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    bio = models.TextField(blank=True, null=True)
    pw_reset_key = models.CharField(null=True, blank=True, max_length=128)
    pw_reset_date = models.DateTimeField(blank=True, null=True)
    digest = models.BooleanField(default=False, verbose_name="Receive Digest?")
    bounce_count = models.IntegerField(default=0)
    bounce_disabled = models.BooleanField(default=False)

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

    class Meta:
        ordering = ['user__last_name', 'user__first_name']

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
        return '{} {}'.format(self.user.first_name,
                              self.user.last_name)


class Edition(models.Model):
    subject = models.CharField(blank=True, null=True, max_length=2048)
    date_created = models.DateTimeField(
        blank=False, null=False, auto_now_add=True)
    date_modified = models.DateTimeField(
        blank=False, null=False, auto_now=True)
    date_sent = models.DateTimeField(blank=True, null=True)
    sent = models.BooleanField(blank=False, default=False)
    volume = models.IntegerField(blank=True, null=True)
    issue = models.IntegerField(blank=True, null=True)

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

    # Note: whilst unconventional, this allows us to add extra
    # data into the final script
    def data(self):
        data = {}
        data['emails'] = []
        number = 1
        for e in self.editedemail_set.order_by('subject').all():
            email = {}
            email['number'] = number
            number += 1
            email['line_count'] = len(e.body.split('\n'))
            email['message'] = e
            email['incoming'] = e.incoming

            # Get user (if we can)
            if User.objects.filter(email__iexact=e.sender).count():
                user = User.objects.get(email__iexact=e.sender)
                email['sender'] = "{} {} <{}>".format(
                    user.first_name,
                    user.last_name,
                    user.email)
            else:
                email['sender'] = e.sender

            if 're:' in e.subject.lower():
                email['is_reply'] = True
            else:
                email['is_reply'] = False

            # Add it to the list
            data['emails'].append(email)

        return data

    # Helper functions to get the current Volume and Issue numbers
    @classmethod
    def get_current_volume(cls):
        start_date = datetime(1988, 5, 7, 0, 0)
        current_date = datetime.now()
        difference_in_years = relativedelta(current_date, start_date).years
        return (difference_in_years + 2)

    @classmethod
    def get_current_issue(cls):
        editions_in_volume = cls.objects.filter(
            volume=cls.get_current_volume()).count()

        if cls.get_current_volume() == 32:
            return (editions_in_volume + 144)
        else:
            return (editions_in_volume + 1)


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

    purged = models.BooleanField(null=False, default=False)

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
        return cls.objects.filter(
            deleted=True).filter(
            purged=False)

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
    incoming = models.ForeignKey(IncomingEmail, on_delete=models.CASCADE,
                                 blank=True, null=True)

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
    def url(self):
        return '/att/{}/{}/'.format(self.email.id, self.stored_filename)

    @property
    def path(self):
        return os.path.join(settings.EMAIL_ATTACHMENT_PATH,
                            str(self.email.id),
                            str(self.stored_filename))

    def __str__(self):
        return '{} ({})'.format(self.original_filename, self.email)
