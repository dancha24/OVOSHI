from django.urls import path

from . import views

urlpatterns = [
    # Без завершающего / — иначе CommonMiddleware редиректит POST и ВК может не дойти до view
    path('callback', views.vk_callback, name='vk_callback_noslash'),
    path('callback/', views.vk_callback, name='vk_callback'),
    path('ping/', views.vk_ping, name='vk_ping'),
    path('diag/', views.vk_diag, name='vk_diag'),
]
