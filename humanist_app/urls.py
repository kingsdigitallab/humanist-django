from django.urls import path

# Legacy views
from .views import (UserLogoutView, WebAnnouncementView,
                    WebHomepageView, WebLogin,
                    WebQuackView, WebMembershipFormView)

urlpatterns = [
    # These are the legacy website, which we have not changed
    path('', WebHomepageView.as_view()),
    path('announcement.html', WebAnnouncementView.as_view()),
    path('quack.html', WebQuackView.as_view()),
    path('Restricted/', WebLogin.as_view()),
    path('membership_form.php', WebMembershipFormView.as_view()),

    # User Pages
    path('user/logout/', UserLogoutView.as_view()),

    # Editor Pages
    path('editor/logout/', UserLogoutView.as_view()),

]
