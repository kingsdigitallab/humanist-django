from django.views.generic import (TemplateView)

'''
The following views (prefixed "Web") are the legacy
website. I've converted them to views because:
a) it's not a big job
b) some of them require integration with the new app
c) all of them require static files handling.
'''


class WebAnnouncementView(TemplateView):
    template_name = 'legacy/announcement.html'


class WebHomepageView(TemplateView):
    template_name = 'legacy/index.html'


class WebQuackView(TemplateView):
    template_name = 'legacy/quack.html'


class WebMembershipFormView(TemplateView):
    template_name = 'legacy/membership_form.html'
