from rest_framework import generics, status
from rest_framework.permissions import AllowAny

from users.permissions import IsAuthenticatedNotGuest
from rest_framework.response import Response

from .models import ShopLot
from .serializers import ShopLotSerializer


class ShopLotListCreateView(generics.ListCreateAPIView):
    """Список активных лотов (публично). Создание — только лидер."""

    serializer_class = ShopLotSerializer

    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAuthenticatedNotGuest()]

    def get_queryset(self):
        base = ShopLot.objects.all().order_by('sort_order', 'id')
        if self.request.method == 'GET':
            if (
                self.request.user.is_authenticated
                and self.request.user.can_manage_participants
                and self.request.query_params.get('all') == '1'
            ):
                return base
            return ShopLot.objects.filter(is_active=True).order_by('sort_order', 'id')
        if not self.request.user.is_authenticated or not self.request.user.can_manage_participants:
            return ShopLot.objects.none()
        return base

    def create(self, request, *args, **kwargs):
        if not request.user.can_manage_participants:
            return Response({'detail': 'Только лидер может добавлять лоты.'}, status=403)
        return super().create(request, *args, **kwargs)


class ShopLotDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Просмотр / правка / удаление лота — только лидер."""

    serializer_class = ShopLotSerializer
    permission_classes = [IsAuthenticatedNotGuest]
    queryset = ShopLot.objects.all()

    def get_queryset(self):
        if not self.request.user.can_manage_participants:
            return ShopLot.objects.none()
        return ShopLot.objects.all()

    def retrieve(self, request, *args, **kwargs):
        if not request.user.can_manage_participants:
            return Response({'detail': 'Недостаточно прав.'}, status=403)
        return super().retrieve(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        if not request.user.can_manage_participants:
            return Response({'detail': 'Только лидер может менять лоты.'}, status=403)
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if not request.user.can_manage_participants:
            return Response({'detail': 'Только лидер может удалять лоты.'}, status=403)
        return super().destroy(request, *args, **kwargs)
