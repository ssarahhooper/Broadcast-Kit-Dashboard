from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from . import slack_events
from django.conf.urls.static import static
from django.conf import settings

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.user_login, name='login'),
    path('signup/', views.signup, name='signup'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),
    path("postmortem/<int:pk>/", views.postmortem, name='postmortem'),
    path("kit/<int:kit_id>/", views.kit_home, name="kit_home"),
    path('calendar/', views.calendar, name='calendar'),
    path('slack/events/', slack_events.slack_events, name='slack_events'),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)