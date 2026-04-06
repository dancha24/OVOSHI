"""Права на исключение из клана (соучастник) и бан."""
from __future__ import annotations

from .models import User


def can_moderate_clan_user(actor: User, target: User) -> bool:
    """Лидер/заместитель: кого можно модерировать (не себя, не суперпользователя, не лидера)."""
    if not getattr(actor, 'can_manage_participants', False):
        return False
    if actor.pk == target.pk:
        return False
    if target.is_superuser:
        return False
    if target.role == User.Role.LEADER:
        return False
    if actor.role == User.Role.DEPUTY:
        if target.role in (User.Role.DEPUTY, User.Role.GUEST, User.Role.ASSOCIATE):
            return False
        return True
    if actor.role == User.Role.LEADER or actor.is_superuser:
        return True
    return False


def can_kick_from_clan(actor: User, target: User) -> bool:
    if not can_moderate_clan_user(actor, target):
        return False
    if target.role == User.Role.BANNED:
        return False
    return True


def can_ban_user(actor: User, target: User) -> bool:
    if not can_moderate_clan_user(actor, target):
        return False
    if target.role == User.Role.BANNED:
        return False
    return True


def can_unban_user(actor: User, target: User) -> bool:
    if not getattr(actor, 'can_manage_participants', False):
        return False
    return target.role == User.Role.BANNED
