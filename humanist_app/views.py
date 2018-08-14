from django.views.generic import (TemplateView)
from django.shortcuts import render, redirect
from django.views import View
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from .helpers import AdminEmail, UserEmail
from django.conf import settings
from .models import Subscriber
from .decorators import require_user, require_editor  # noqa
from django.utils.decorators import method_decorator

'''
The following views (prefixed "Web") are the legacy
website. I've converted them to views because:
a) it's not a big job
b) some of them require integration with the new app
c) all of them require static files handling.
'''


class UserView(TemplateView):
    template_name = 'humanist_app/user.html'

    @method_decorator(require_user)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)


class UserUnsubscribeView(TemplateView):
    template_name = 'humanist_app/user_unsubscribe.html'


class UserUnsubscribeConfirmView(View):
    template_name = 'humanist_app/user_unsubscribe_successful.html'

    def post(self, request, *args, **kwargs):
        # Keep it simple!
        # Deleting allows re-subscription without admin interference.
        request.user.delete()
        logout(request)
        return render(request, self.template_name, {})


class UserUpdateView(View):
    template_name = 'humanist_app/user_update.html'

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
