from django.views.generic import (TemplateView)
from django.shortcuts import render, redirect
from django.views import View
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from .helpers import AdminEmail, UserEmail, ActiveUserEmail
from django.conf import settings
from .models import (Edition, IncomingEmail, EditedEmail,
                     Attachment, Subscriber)
from .decorators import require_user, require_editor
from django.utils.decorators import method_decorator
from wsgiref.util import FileWrapper
from django.http import HttpResponse
from django.core.exceptions import ObjectDoesNotExist
import os
from django.core.paginator import Paginator
from django.db.models import Q

from django.template.loader import render_to_string
from datetime import datetime
import textwrap


class AttachmentDownloadView(View):
    template_name = 'humanist_app/attachment_deleted.html'

    def get(self, request, *args, **kwargs):
        try:
            attachment = Attachment.objects.get(
                email__id=kwargs['email_id'],
                stored_filename=kwargs['filename'])
            wrapper = FileWrapper(open(os.path.abspath(attachment.path), 'rb'))
            response = HttpResponse(wrapper, content_type=attachment.mimetype)
            response['Content-Disposition'] = 'attachment; filename={}'.format(
                attachment.original_filename)
            response['Content-Length'] = os.path.getsize(attachment.path)
            return response
        # This handles both missing DB entries and missing
        # files.
        except (ObjectDoesNotExist, IOError):
            return render(request, self.template_name, {})


class EditorView(View):
    template_name = 'humanist_app/editor.html'

    @method_decorator(require_editor)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get(self, request, *args, **kwargs):
        if 'page' in request.GET:
            page = request.GET['page']
        else:
            page = 1

        user_counts = {}
        user_counts['active'] = User.objects.filter(is_active=True).count()
        user_counts['inactive'] = User.objects.filter(is_active=False).count()
        user_counts['admin'] = User.objects.filter(is_staff=True).count()

        users_inactive = User.objects.filter(is_active=False)

        editions = {}
        editions['drafts'] = Edition.get_drafts()
        editions['sent'] = Edition.get_sent()[:3]

        emails = {}
        emails['inbox'] = IncomingEmail.get_available()
        emails['used'] = IncomingEmail.get_used()
        emails['deleted'] = IncomingEmail.get_deleted()

        p = Paginator(emails['inbox'], 50)
        email_display = p.get_page(page)

        context = {}
        context['emails'] = emails
        context['email_display'] = email_display
        context['editions'] = editions
        context['user_counts'] = user_counts
        context['users_inactive'] = users_inactive

        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        if 'action' in request.POST:
            if request.POST['action'] == 'Delete':
                # Delete selected emails
                if 'email_id' in request.POST:
                    email_ids = request.POST.getlist('email_id')
                    for eid in email_ids:
                        email = IncomingEmail.objects.get(id=eid)
                        email.deleted = True
                        email.save()

            elif request.POST['action'] == 'Mark as Used':
                # Delete selected emails
                if 'email_id' in request.POST:
                    email_ids = request.POST.getlist('email_id')
                    for eid in email_ids:
                        email = IncomingEmail.objects.get(id=eid)
                        email.used = True
                        email.save()

            elif request.POST['action'] == 'Create Edition':
                # Create a new edition
                if 'email_id' in request.POST:
                    email_ids = request.POST.getlist('email_id')
                    if len(email_ids) > 0:

                        edition = Edition()
                        edition.save()

                        for eid in email_ids:
                            email = IncomingEmail.objects.get(id=eid)

                            edited_email = EditedEmail()
                            edited_email.edition = edition
                            edited_email.body = textwrap.fill(email.body, 80)
                            edited_email.subject = email.subject
                            edited_email.sender = email.sender
                            edited_email.incoming = email
                            edited_email.save()

                            email.used = True
                            email.save()
                    return redirect('/editor/editions/{}/'.format(edition.id))

            elif request.POST['action'] == 'Add':
                # Create a new edition
                if 'email_id' in request.POST and 'edition_id' in request.POST:
                    email_ids = request.POST.getlist('email_id')
                    if len(email_ids) > 0:

                        edition = Edition.objects.get(
                            id=request.POST['edition_id'])

                        for eid in email_ids:
                            email = IncomingEmail.objects.get(id=eid)

                            edited_email = EditedEmail()
                            edited_email.edition = edition
                            edited_email.body = email.body
                            edited_email.subject = email.subject
                            edited_email.sender = email.sender
                            edited_email.incoming = email
                            edited_email.save()

                            email.used = True
                            email.save()

                        return redirect('/editor/editions/{}/'.format(
                            edition.id))
            else:
                # Unknown method
                pass

        return self.get(request, args, kwargs)


class EditorEditionsView(View):
    template_name = 'humanist_app/editor_editions.html'

    @method_decorator(require_editor)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get(self, request, *args, **kwargs):

        context = {}

        editions = {}
        editions['drafts'] = Edition.get_drafts()
        editions['sent'] = Edition.get_sent()

        context['editions'] = editions

        return render(request, self.template_name, context)


class EditorEditionsSingleView(View):
    template_name = 'humanist_app/editor_editions_single.html'

    @method_decorator(require_editor)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get(self, request, *args, **kwargs):

        context = {}
        edition = Edition.objects.get(id=kwargs['edition_id'])
        context['edition'] = edition
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        edition = Edition.objects.get(id=kwargs['edition_id'])
        if 'action' in request.POST:
            if request.POST['action'] == 'Save':
                # Save and do nothing
                edition.subject = request.POST['subject']
                edition.save()
                for email in edition.editedemail_set.all():
                    email.sender = request.POST['sender_{}'.format(email.id)]
                    email.subject = request.POST['subject_{}'.format(email.id)]
                    email.body = request.POST['body_{}'.format(email.id)]
                    email.save()

                return redirect('/editor/editions/')

            if request.POST['action'] == 'Preview and Send':
                # Save and do nothing
                edition.subject = request.POST['subject']
                edition.save()
                for email in edition.editedemail_set.all():
                    email.sender = request.POST['sender_{}'.format(email.id)]
                    email.subject = request.POST['subject_{}'.format(email.id)]
                    email.body = request.POST['body_{}'.format(email.id)]
                    email.save()

                return redirect('/editor/editions/{}/preview/'.format(
                    edition.id))

            elif request.POST['action'] == 'Delete Selected':
                # Delete selected emails from this edition
                if 'email_id' in request.POST:
                    email_ids = request.POST.getlist('email_id')
                    for eid in email_ids:
                        email = EditedEmail.objects.get(id=eid)
                        email.delete()

            elif request.POST['action'] == 'Delete Edition':
                # Delete selected emails from this edition
                edition.delete()
                return redirect('/editor/editions/')
            else:
                # Unknown method
                pass
        return self.get(request, *args, **kwargs)


class EditorEditionPreviewView(View):
    template_name = 'humanist_app/editor_editions_preview.html'

    @method_decorator(require_editor)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get(self, request, *args, **kwargs):

        context = {}
        edition = Edition.objects.get(id=kwargs['edition_id'])
        context['edition'] = edition
        context['current_volume'] = Edition.get_current_volume()
        context['current_issue'] = Edition.get_current_issue()

        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        edition = Edition.objects.get(id=kwargs['edition_id'])
        if 'action' in request.POST:
            if request.POST['action'] == 'Back':
                return redirect('/editor/editions/{}/'.format(
                    edition.id))

            if request.POST['action'] == 'Send':
                # Do the magic!

                if edition.subject == '' or edition.subject is None:
                    context = {}
                    context['edition'] = edition
                    context['current_volume'] = Edition.get_current_volume()
                    context['current_issue'] = Edition.get_current_issue()
                    context['error'] = "Subject can not be blank!\
                        Please fix this."
                    return render(request, self.template_name, context)
                else:
                    # Remember to set volume and issue vars!
                    edition.volume = Edition.get_current_volume()
                    edition.issue = Edition.get_current_issue()
                    edition.save()

                    body = render_to_string('includes/outgoing_template.html',
                                            {'edition': edition})

                    subject = '[Humanist] {}.{}: {}'.format(
                        edition.volume, edition.issue, edition.subject)

                    email = ActiveUserEmail()
                    email.subject = subject
                    email.body = body
                    email.send()

                    edition.sent = True
                    edition.date_sent = datetime.now()
                    edition.save()

                    return redirect('/editor/editions/')


class EditorTrashView(View):
    template_name = 'humanist_app/editor_trash.html'

    @method_decorator(require_editor)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get(self, request, *args, **kwargs):
        if 'page' in request.GET:
            page = request.GET['page']
        else:
            page = 1

        emails = {}
        emails['inbox'] = IncomingEmail.get_available()
        emails['used'] = IncomingEmail.get_used()
        emails['deleted'] = IncomingEmail.get_deleted()

        p = Paginator(emails['deleted'], 50)
        email_display = p.get_page(page)

        context = {}
        context['emails'] = emails
        context['email_display'] = email_display

        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        if 'action' in request.POST:
            if request.POST['action'] == 'Restore':
                # Restore selected emails
                if 'email_id' in request.POST:
                    email_ids = request.POST.getlist('email_id')
                    for eid in email_ids:
                        email = IncomingEmail.objects.get(id=eid)
                        email.deleted = False
                        email.save()

            elif request.POST['action'] == 'Empty Trash':
                # Empty the trash
                emails = IncomingEmail.get_deleted()
                for email in emails:
                    email.purged = True
                    email.save()

            else:
                # Unknown method
                pass
        return self.get(request, args, kwargs)


class EditorUsedView(View):
    template_name = 'humanist_app/editor_used.html'

    @method_decorator(require_editor)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get(self, request, *args, **kwargs):
        if 'page' in request.GET:
            page = request.GET['page']
        else:
            page = 1

        emails = {}
        emails['inbox'] = IncomingEmail.get_available()
        emails['used'] = IncomingEmail.get_used()
        emails['deleted'] = IncomingEmail.get_deleted()

        p = Paginator(emails['used'], 50)
        email_display = p.get_page(page)

        context = {}
        context['emails'] = emails
        context['email_display'] = email_display
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        if 'action' in request.POST:
            if request.POST['action'] == 'Mark as Not Used':
                # Restore selected emails
                if 'email_id' in request.POST:
                    email_ids = request.POST.getlist('email_id')
                    for eid in email_ids:
                        email = IncomingEmail.objects.get(id=eid)
                        email.used = False
                        email.save()

            elif request.POST['action'] == 'Delete':
                # Restore selected emails
                if 'email_id' in request.POST:
                    email_ids = request.POST.getlist('email_id')
                    for eid in email_ids:
                        email = IncomingEmail.objects.get(id=eid)
                        email.deleted = True
                        email.save()

            elif request.POST['action'] == 'Delete All':
                # Restore selected emails
                for email in IncomingEmail.get_used():
                    email.deleted = True
                    email.save()
            else:
                # Unknown method
                pass

        return self.get(request, args, kwargs)


class EditorUsersView(View):
    template_name = 'humanist_app/editor_users.html'

    @method_decorator(require_editor)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get(self, request, *args, **kwargs):

        context = {}

        if 'q' in request.GET:
            q = request.GET.get('q')
            context['q'] = q
            users = Subscriber.objects.filter(
                Q(user__first_name__icontains=q) |
                Q(user__last_name__icontains=q) |
                Q(user__email__icontains=q) |
                Q(bio__icontains=q))
        else:
            users = Subscriber.objects.all()

        paginator = Paginator(users, 25)

        if 'page' in request.GET:
            page = request.GET.get('page')
        else:
            page = 1

        context['users'] = paginator.get_page(page)

        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        required_fields = ['id', 'action']
        context = {}

        for field in required_fields:
            if field not in request.POST:
                context['error'] = "There was an error with the form"
                return render(request, self.template_name, context)

        for field in required_fields:
            if not request.POST[field]:
                context['error'] = "A field was missing"
                return render(request, self.template_name, context)

        user = User.objects.get(pk=request.POST['id'])
        action = request.POST['action']

        if action == "Promote to Admin":
            user.is_staff = True
            user.save()
            context['success'] = "{} Promoted".format(user.email)

        elif action == "Remove":
            user.delete()
            context['success'] = "Deleted: {}".format(user.email)

        if 'q' in request.GET:
            q = request.GET.get('q')
            context['q'] = q
            users = Subscriber.objects.filter(
                Q(user__first_name__icontains=q) |
                Q(user__last_name__icontains=q) |
                Q(user__email__icontains=q) |
                Q(bio__icontains=q))
        else:
            users = Subscriber.objects.all()

        paginator = Paginator(users, 25)

        if 'page' in request.GET:
            page = request.GET.get('page')
        else:
            page = 1

        context['users'] = paginator.get_page(page)
        return render(request, self.template_name, context)


class EditorUsersAdminsView(View):
    template_name = 'humanist_app/editor_users_admins.html'

    @method_decorator(require_editor)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get(self, request, *args, **kwargs):

        context = {}

        users = Subscriber.objects.filter(user__is_staff=True)
        paginator = Paginator(users, 25)

        if 'page' in request.GET:
            page = request.GET.get('page')
        else:
            page = 1

        context['users'] = paginator.get_page(page)

        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        required_fields = ['id', 'action']
        context = {}

        for field in required_fields:
            if field not in request.POST:
                context['error'] = "There was an error with the form"
                return render(request, self.template_name, context)

        for field in required_fields:
            if not request.POST[field]:
                context['error'] = "A field was missing"
                return render(request, self.template_name, context)

        user = User.objects.get(pk=request.POST['id'])
        action = request.POST['action']

        if action == "Demote":
            if not user.is_superuser:
                user.is_staff = False
                user.save()
                context['success'] = "{} Demoted".format(user.email)
            else:
                context['error'] = "Cannot demote a superuser."

        users = Subscriber.objects.filter(user__is_staff=True)

        paginator = Paginator(users, 25)

        if 'page' in request.GET:
            page = request.GET.get('page')
        else:
            page = 1

        context['users'] = paginator.get_page(page)
        return render(request, self.template_name, context)


class EditorUsersUnapprovedView(View):
    template_name = 'humanist_app/editor_users_unapproved.html'

    @method_decorator(require_editor)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get(self, request, *args, **kwargs):
        context = {}
        unapproved_users = Subscriber.objects.filter(user__is_active=False)
        context['users'] = unapproved_users
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        required_fields = ['id', 'action']
        context = {}

        for field in required_fields:
            if field not in request.POST:
                context['error'] = "There was an error with the form"
                return render(request, self.template_name, context)

        for field in required_fields:
            if not request.POST[field]:
                context['error'] = "A field was missing"
                return render(request, self.template_name, context)

        user = User.objects.get(pk=request.POST['id'])
        action = request.POST['action']

        if action == "Approve":
            user.is_active = True
            user.save()
            context['success'] = "Approved: {}".format(user.email)

        elif action == "Reject":
            user.delete()
            context['success'] = "Rejected: {}".format(user.email)

        unapproved_users = Subscriber.objects.filter(user__is_active=False)
        context['users'] = unapproved_users

        return render(request, self.template_name, context)


class UserView(TemplateView):
    template_name = 'humanist_app/user.html'

    @method_decorator(require_user)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)


class UserChangePasswordView(View):
    template_name = 'humanist_app/user_password.html'

    @method_decorator(require_user)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, {})

    def post(self, request, *args, **kwargs):
        required_fields = ['old_password', 'password', 'password2']

        for field in required_fields:
            if field not in request.POST:
                return render(request, self.template_name, {
                    'error': "There was an error with the form"})

        for field in required_fields:
            if not request.POST[field]:
                return render(request, self.template_name, {
                    'error': "A field was missing",
                })

        if not request.POST['password'] == request.POST['password2']:
            return render(request, self.template_name, {
                'error': "Passwords did not match",

            })

        if not len(request.POST['password']) >= 8:
            return render(request, self.template_name, {
                'error': "Password must be at least 8 characters",
            })

        if request.user.check_password(request.POST['old_password']):
            u = request.user
            request.user.set_password(request.POST['password'])
            request.user.save()
            login(request, u)

            return render(request, self.template_name, {
                'success': 'Your password has been changed.'})

        else:
            return render(request, self.template_name, {
                'error': 'Invalid password.'})


class UserUnsubscribeView(TemplateView):
    template_name = 'humanist_app/user_unsubscribe.html'

    @method_decorator(require_user)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)


class UserUnsubscribeConfirmView(View):
    template_name = 'humanist_app/user_unsubscribe_successful.html'

    @method_decorator(require_user)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        # Keep it simple!
        # Deleting allows re-subscription without admin interference.
        request.user.delete()
        logout(request)
        return render(request, self.template_name, {})


class UserUpdateView(View):
    template_name = 'humanist_app/user_update.html'

    @method_decorator(require_user)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get(self, request, *args, **kwargs):
        subscriber = Subscriber.objects.get(user=request.user)
        return render(request, self.template_name, {'subscriber': subscriber})

    def post(self, request, *args, **kwargs):
        subscriber = Subscriber.objects.get(user=request.user)
        if request.POST['action'] == 'Update Email':
            required_fields = ['new_email']

            for field in required_fields:
                if field not in request.POST:
                    return render(request, self.template_name, {
                        'error': "There was an error with the form",
                        'subscriber': subscriber})

            for field in required_fields:
                if not request.POST[field]:
                    return render(request, self.template_name, {
                        'error': "A field was missing",
                        'subscriber': subscriber
                    })

            email = request.POST['new_email']

            # Quick sanity check
            users = User.objects.filter(email__iexact=email)

            if users.count():
                return render(request, self.template_name, {
                    'error': 'That email already exists.',
                    'subscriber': subscriber})

            else:
                request.user.email = email
                request.user.username = email
                request.user.save()

                return render(request, self.template_name, {
                    'success': 'Your email has been changed.',
                    'subscriber': subscriber})

        elif request.POST['action'] == 'Update Preferences':
            subscriber.digest = 'digest' in request.POST
            subscriber.save()

            return render(request, self.template_name, {
                'success': 'Your preferences have been updated.',
                'subscriber': subscriber})


class UserLogoutView(View):
    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            logout(request)
        return redirect('/Restricted/')


class WebAnnouncementView(TemplateView):
    template_name = 'legacy/announcement.html'


class WebHomepageView(TemplateView):
    template_name = 'legacy/index.html'

    def get(self, request, *args, **kwargs):
        context = {}

        context['volumes'] = Edition.objects.exclude(
            volume=None).values_list('volume', flat=True).distinct()

        return render(request, self.template_name, context)


class WebVolumeView(TemplateView):
    template_name = 'legacy/volume.html'

    def get(self, request, *args, **kwargs):
        context = {}

        volume = kwargs['volume']
        editions = Edition.objects.filter(volume=volume).order_by('issue')

        context['volume'] = volume
        context['editions'] = editions

        return render(request, self.template_name, context)


class WebIssueView(TemplateView):
    template_name = 'legacy/issue.html'

    def get(self, request, *args, **kwargs):
        context = {}

        volume = kwargs['volume']
        issue = kwargs['issue']

        edition = Edition.objects.filter(volume=volume).get(issue=issue)

        context['volume'] = volume
        context['edition'] = edition

        return render(request, self.template_name, context)


class WebLogin(View):
    template_name = 'legacy/restricted_login.html'

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.is_active:
                if request.user.is_staff:
                    return redirect('/editor/')
                else:
                    return redirect('/user/')

        return render(request, self.template_name, {})

    def post(self, request, *args, **kwargs):
        required_fields = ['username', 'password']

        for field in required_fields:
            if field not in request.POST:
                return render(request, self.template_name, {
                    'error': "There was an error with the form"})

        for field in required_fields:
            if not request.POST[field]:
                return render(request, self.template_name, {
                    'error': "A field was missing",
                    'username': request.POST['username'],
                })

        username = request.POST['username']
        password = request.POST['password']

        user = authenticate(username=username, password=password)
        if user is not None:
            if user.is_active:
                login(request, user)
                if 'next' in request.GET:
                    return redirect(request.GET['next'])
                else:
                    if user.is_staff:
                        return redirect('/editor/')
                    else:
                        return redirect('/user/')
            else:
                return render(request, self.template_name, {
                    'error': "Your account is not yet active",
                    'username': request.POST['username'],
                })
        else:
            # Return an 'invalid login' error message.
            return render(request, self.template_name, {
                'error': "Incorrect username (email) or password",
                'username': request.POST['username'],
            })

        # TODO - send email for verification
        return render(request, self.template_name, {
            'success': 'Your account has been created,\
            it will be reviewed by an administrator shortly.'})


class WebQuackView(TemplateView):
    template_name = 'legacy/quack.html'


class WebMembershipFormView(View):
    template_name = 'legacy/membership_form.html'

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, {})

    def post(self, request, *args, **kwargs):
        required_fields = ['firstname', 'lastname', 'email',
                           'password', 'password2', 'bioblurb']

        for field in required_fields:
            if field not in request.POST:
                return render(request, self.template_name, {
                              'error': "There was an error with the form"})

        for field in required_fields:
            if not request.POST[field]:
                return render(request, self.template_name, {
                    'error': "A required (*) field was missing",
                    'firstname': request.POST['firstname'],
                    'lastname': request.POST['lastname'],
                    'email': request.POST['email'],
                    'bioblurb': request.POST['bioblurb'],
                })

        if not request.POST['password'] == request.POST['password2']:
            return render(request, self.template_name, {
                'error': "Passwords did not match",
                'firstname': request.POST['firstname'],
                'lastname': request.POST['lastname'],
                'email': request.POST['email'],
                'bioblurb': request.POST['bioblurb'],
            })

        if not len(request.POST['password']) >= 8:
            return render(request, self.template_name, {
                'error': "Password must be at least 8 characters",
                'firstname': request.POST['firstname'],
                'lastname': request.POST['lastname'],
                'email': request.POST['email'],
                'bioblurb': request.POST['bioblurb'],
            })

        user = User()
        user.username = request.POST['email']
        user.first_name = request.POST['firstname']
        user.last_name = request.POST['lastname']
        user.email = request.POST['email']
        user.is_active = False
        user.is_staff = False
        user.is_superuser = False
        user.set_password(request.POST['password'])
        user.save()

        # create subscriber infomation
        sub = Subscriber()
        sub.user = user
        sub.bio = request.POST['bioblurb']
        sub.save()

        # Send emails
        email = UserEmail(user)
        email.subject = "Humanist Registration"
        email.body = (
            "Dear {},\n\n"
            "We have received your Humanist registration request. "
            "It will shortly be reviewed by an administrator."
            "Kind Regards,\n Humanist").format(user.first_name)
        email.send()

        email = AdminEmail()
        email.subject = "Humanist New Registration"
        email.body = (
            "Dear Administrator,\n\n"
            "{} {} has registered for Humanist. Their bio:\n\n"
            "{} \n\n"
            "To approve or deny this request, please visit"
            "{}/editor/users \n\n"
            "Kind Regards,\n Humanist").format(user.first_name,
                                               user.last_name,
                                               sub.bio,
                                               settings.BASE_URL)
        email.send()

        return render(request, self.template_name, {
                      'success': 'Your account has been created,\
                      it will be reviewed by an administrator shortly.'})


class WebResetPasswordView(View):
    template_name = 'legacy/forgot_password_2.html'

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, {})

    def post(self, request, *args, **kwargs):
        required_fields_post = ['password', 'password2']
        required_fields_get = ['email', 'key']

        for field in required_fields_post:
            if field not in request.POST:
                return render(request, self.template_name, {
                              'error': "There was an error with the form"})

        for field in required_fields_get:
            if field not in request.GET:
                return render(request, self.template_name, {
                              'error': "Email or key missing"})

        for field in required_fields_post:
            if not request.POST[field]:
                return render(request, self.template_name, {
                    'error': "A required (*) field was missing",
                })

        for field in required_fields_get:
            if not request.GET[field]:
                return render(request, self.template_name, {
                    'error': "A required (*) field was missing",
                })

        if not request.POST['password'] == request.POST['password2']:
            return render(request, self.template_name, {
                'error': "Passwords did not match",

            })

        if not len(request.POST['password']) >= 8:
            return render(request, self.template_name, {
                'error': "Password must be at least 8 characters",
            })

        user = User.objects.filter(email=request.GET['email'])
        if user.count():
            user = user[0]
            subscriber = Subscriber.objects.get(user=user)
            if subscriber.validate_password_reset_key(request.GET['key']):
                user.set_password(request.POST['password'])
                user.save()
                return render(request, self.template_name, {
                    'success': 'Your password has been changed'})
            else:
                return render(request, self.template_name, {
                    'error': "Invalid key",
                })
        else:
            return render(request, self.template_name, {
                'error': "Invalid email",
            })


class WebForgottenPasswordForm(View):
    template_name = 'legacy/forgot_password.html'

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, {})

    def post(self, request, *args, **kwargs):
        email = request.POST['email']
        user = User.objects.filter(email=email)

        error = None
        success = None

        if user.count():
            user = user[0]
            sub = Subscriber.objects.filter(user=user)[0]
            print(sub)
            sub.generate_password_reset_key()
            success = 'Please check your email.'
        else:
            error = 'Sorry, an error occured.'

        if error:
            return render(request, self.template_name, {'error': error})

        if success:
            return render(request, self.template_name, {'success': success})


class WebRestrictedDeniedView(TemplateView):
    template_name = 'legacy/restricted_denied.html'
