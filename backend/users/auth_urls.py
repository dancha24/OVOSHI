from django.urls import path
from . import views as auth_views
from . import vkid_views

urlpatterns = [
    path('me/', auth_views.CurrentUserView.as_view(), name='current-user'),
    path('vkid/config/', vkid_views.VkIdConfigView.as_view(), name='vkid-config'),
    path('vkid/complete/', vkid_views.VkIdCompleteView.as_view(), name='vkid-complete'),
]
