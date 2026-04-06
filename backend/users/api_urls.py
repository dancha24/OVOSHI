from django.urls import path
from . import application_views, views

urlpatterns = [
    path('participants/', views.ParticipantListView.as_view(), name='participant-list'),
    path('participants/<int:pk>/', views.ParticipantDetailView.as_view(), name='participant-detail'),
    path(
        'participants/<int:pk>/ok-ledger/',
        views.ClanPointsLedgerView.as_view(),
        name='participant-ok-ledger',
    ),
    path(
        'participants/<int:pk>/kick/',
        views.ParticipantKickView.as_view(),
        name='participant-kick',
    ),
    path(
        'participants/<int:pk>/ban/',
        views.ParticipantBanView.as_view(),
        name='participant-ban',
    ),
    path(
        'participants/<int:pk>/unban/',
        views.ParticipantUnbanView.as_view(),
        name='participant-unban',
    ),
    path(
        'applications/',
        application_views.ClanApplicationListView.as_view(),
        name='clan-application-list',
    ),
    path(
        'applications/<int:pk>/',
        application_views.ClanApplicationDetailView.as_view(),
        name='clan-application-detail',
    ),
]
