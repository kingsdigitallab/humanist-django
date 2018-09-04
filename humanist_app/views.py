from django.views.generic import (TemplateView)
from django.shortcuts import render, redirect
from django.views import View
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from .helpers import AdminEmail, UserEmail
from django.conf import settings
from .models import (Edition, IncomingEmail, EditedEmail, Subscriber)
from .decorators import require_user, require_editor
from django.utils.decorators import method_decorator

'''
The following views (prefixed "Web") are the legacy
website. I've converted them to views because:
a) it's not a big job
b) some of them require integration with the new app
c) all of them require static files handling.
'''


class EditorView(View):
    template_name = 'humanist_app/editor.html'

    @method_decorator(require_editor)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get(self, request, *args, **kwargs):

        user_counts = {}
        user_counts['active'] = User.objects.filter(is_active=True).count()
        user_counts['inactive'] = User.objects.filter(is_active=False).count()
        user_counts['admin'] = User.objects.filter(is_staff=True).count()

        editions = {}
        editions['drafts'] = Edition.get_drafts()
        editions['sent'] = Edition.get_sent()

        emails = {}
        emails['inbox'] = IncomingEmail.get_available()
        emails['used'] = IncomingEmail.get_used()
        emails['deleted'] = IncomingEmail.get_deleted()

        context = {}
        context['editions'] = editions
        context['emails'] = emails
        context['user_counts'] = user_counts
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
                            edited_email.body = email.body
                            edited_email.subject = email.subject
                            edited_email.sender = email.sender
                            edited_email.incoming = email
                            edited_email.save()

                            email.used = True
                            email.save()
                pass

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


class EditorTrashView(View):
    template_name = 'humanist_app/editor_trash.html'

    @method_decorator(require_editor)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get(self, request, *args, **kwargs):

        emails = {}
        emails['inbox'] = IncomingEmail.get_available()
        emails['used'] = IncomingEmail.get_used()
        emails['deleted'] = IncomingEmail.get_deleted()

        context = {}
        context['emails'] = emails

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
                    email.delete()

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

        emails = {}
        emails['inbox'] = IncomingEmail.get_available()
        emails['used'] = IncomingEmail.get_used()
        emails['deleted'] = IncomingEmail.get_deleted()

        context = {}
        context['emails'] = emails

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
        return render(request, self.template_name, {})

    def post(self, request, *args, **kwargs):
        required_fields = ['new_email']

        for field in required_fields:
            if field not in request.POST:
                return render(request, self.template_name, {
                    'error': "There was an error with the form"})

        for field in required_fields:
            if not request.POST[field]:
                return render(request, self.template_name, {
                    'error': "A field was missing",
                })

        email = request.POST['new_email']

        # Quick sanity check
        users = User.objects.filter(email__iexact=email)

        if users.count():
            return render(request, self.template_name, {
                'error': 'That email already exists.'})

        else:
            request.user.email = email
            request.user.username = email
            request.user.save()

            return render(request, self.template_name, {
                'success': 'Your email has been changed.'})


class UserLogoutView(View):
    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            logout(request)
        return redirect('/Restricted/')


class WebAnnouncementView(TemplateView):
    template_name = 'legacy/announcement.html'


class WebHomepageView(TemplateView):
    template_name = 'legacy/index.html'


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
