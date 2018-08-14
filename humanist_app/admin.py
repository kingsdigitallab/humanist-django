from django.contrib import admin  # noqa

# Register your models here.
from .models import IncomingEmail, EditedEmail, Edition, Subscriber


@admin.register(IncomingEmail)
class IncomingEmailAdmin(admin.ModelAdmin):
    list_display = ['date', 'sender', 'subject', 'used']


@admin.register(EditedEmail)
class EditedEmailAdmin(admin.ModelAdmin):
    list_display = ['edition', 'sender', 'subject']


@admin.register(Edition)
class EditionAdmin(admin.ModelAdmin):
    list_display = ['date_created', 'subject', 'sent', 'date_sent']


@admin.register(Subscriber)
class SubscriberAdmin(admin.ModelAdmin):
    list_display = ['user', 'bio']
