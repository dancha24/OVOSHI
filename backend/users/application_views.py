from rest_framework import generics
from .permissions import IsAuthenticatedNotGuest

from .models import ClanApplication
from .serializers import ClanApplicationDecisionSerializer, ClanApplicationReadSerializer


class ClanApplicationListView(generics.ListAPIView):
    """Список заявок в клан — лидер или заместитель. Фильтр: ?status=pending|approved|rejected"""

    permission_classes = [IsAuthenticatedNotGuest]
    serializer_class = ClanApplicationReadSerializer

    def get_queryset(self):
        if not self.request.user.can_manage_participants:
            return ClanApplication.objects.none()
        qs = ClanApplication.objects.select_related('user', 'user__profile').order_by('-created_at')
        st = (self.request.query_params.get('status') or '').strip().lower()
        if st in ('pending', 'approved', 'rejected'):
            qs = qs.filter(status=st)
        return qs


class ClanApplicationDetailView(generics.RetrieveUpdateAPIView):
    """Просмотр заявки и решение (PATCH: status + status_comment) — лидер или заместитель."""

    permission_classes = [IsAuthenticatedNotGuest]

    def get_queryset(self):
        if not self.request.user.can_manage_participants:
            return ClanApplication.objects.none()
        return ClanApplication.objects.select_related('user', 'user__profile')

    def get_serializer_class(self):
        if self.request.method in ('PUT', 'PATCH'):
            return ClanApplicationDecisionSerializer
        return ClanApplicationReadSerializer
