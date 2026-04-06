from django.urls import path
from . import views as core_views

urlpatterns = [
    path('settings/', core_views.SiteSettingsView.as_view(), name='site-settings'),
]
