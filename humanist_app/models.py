from django.db import models
from django.contrib.auth.models import User


class Edition(models.Model):
    subject = models.CharField(blank=True, null=True, max_length=2048)
    date_created = models.DateTimeField(
        blank=False, null=False, auto_now_add=True)
    date_modified = models.DateTimeField(
        blank=False, null=False, auto_now=True)
    date_sent = models.DateTimeField(blank=True, null=True)
    sent = models.booleanField(blank=False, default=False)

    class Meta:
        ordering = ['-date_created']

    @classmethod
    def get_drafts(cls):
        return cls.objects.filter(sent=False)

    @classmethod
    def get_sent(cls):
        return cls.objects.filter(sent=True)


class IncomingEmail(models.Model):
    body = models.TextField(blank=True, null=True)
    body_html = models.TextField(blank=True, null=True)
    date = models.DateTimeField(blank=False, null=False)
    raw = models.TextField(blank=True, null=True)
    sender = models.CharField(blank=False, null=False, max_length=256)
    subject = models.CharField(blank=True, null=True, max_length=2048)

    used = models.BooleanField(null=False, default=False)
    deleted = models.BooleanField(null=False, default=False)

    class Meta:
        ordering = ['-date']

    @classmethod
    def get_available(cls):
        return cls.objects.filter(deleted=False).filter(used=False)

    @classmethod
    def get_deleted(cls):
        return cls.objects.filter(deleted=True)

    @classmethod
    def get_unused(cls):
        return cls.objects.filter(used=False)

    @classmethod
    def get_used(cls):
        return cls.objects.filter(used=False)

    @property
    def user(self):
        return User.objects.get(email=self.sender)


class EditedEmail(models.Model):
    edition = models.ForeignKey(Edition)
    body = models.TextField(blank=True, null=True)
    date_created = models.DateTimeField(
        blank=False, null=False, auto_now_add=True)
    date_modified = models.DateTimeField(
        blank=False, null=False, auto_now=True)
    subject = models.CharField(blank=True, null=True, max_length=2048)
    sender = models.CharField(blank=False, null=False, max_length=256)
    incoming = models.ForeignKey(IncomingEmail)

    class Meta:
        ordering = ['-date_created']

    def __init__(self):
        self.body = self.incoming.body
        self.subject = self.incoming.subject
        self.sender = self.incoming.sender

    @property
    def user(self):
        return self.incoming.user
