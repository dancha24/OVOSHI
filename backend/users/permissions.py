"""Права DRF: гости (только бот ВК) не ходят в кабинет сайта."""

from rest_framework.permissions import BasePermission

from .models import User


class IsAuthenticatedNotGuest(BasePermission):
    """
    Авторизованный пользователь с ролью от игрока и выше; суперпользователь — всегда.
    Роль guest — только VK-бот, без доступа к API кабинета.
    """

    message = (
        'Вход в кабинет сайта только для участников клана. '
        'Гости пользуются ботом ВКонтакте; после принятия заявки лидером откроется доступ сюда.'
    )

    def has_permission(self, request, view):
        u = request.user
        if not u.is_authenticated:
            return False
        if u.is_superuser:
            return True
        if u.role == User.Role.BANNED:
            return False
        return u.role not in (User.Role.GUEST, User.Role.ASSOCIATE)
