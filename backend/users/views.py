from django.db import transaction
from django.db.models import F, Prefetch
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from allauth.socialaccount.models import SocialAccount

from .permissions import IsAuthenticatedNotGuest
from .moderation import can_ban_user, can_kick_from_clan, can_unban_user

from .models import ClanPointsEntry, User, Profile
from .serializers import (
    ClanPointsEntryReadSerializer,
    ParticipantUpdateSerializer,
    ProfileSerializer,
    UserListSerializer,
    UserSerializer,
)


def _users_queryset_with_vk_accounts():
    vk_accounts = SocialAccount.objects.filter(provider__in=('vk', 'vk_oauth2')).only('provider', 'extra_data', 'user_id')
    return User.objects.select_related(
        'profile',
        'kicked_by',
        'kicked_by__profile',
        'banned_by',
        'banned_by__profile',
    ).prefetch_related(
        Prefetch('socialaccount_set', queryset=vk_accounts),
    )


def _managed_participants_queryset(user: User):
    """
    Участники, доступные в кабинете лидера/заместителя.
    Заместитель не видит гостей и соучастников (полный список — у лидера и superuser).
    """
    if not user.can_manage_participants:
        return User.objects.none()
    qs = _users_queryset_with_vk_accounts()
    if user.is_superuser or user.role == User.Role.LEADER:
        return qs
    if user.role == User.Role.DEPUTY:
        return qs.exclude(role__in=(User.Role.GUEST, User.Role.ASSOCIATE))
    return User.objects.none()


@method_decorator(ensure_csrf_cookie, name='dispatch')
class CurrentUserView(APIView):
    """Текущий пользователь (для проверки авторизации и получения профиля)."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if user.role == user.Role.BANNED and not user.is_superuser:
            return Response(
                {
                    'detail': 'Доступ к сайту заблокирован. Обратитесь к лидеру клана.',
                    'code': 'banned_no_access',
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        if user.role == user.Role.ASSOCIATE and not user.is_superuser:
            return Response(
                {
                    'detail': (
                        'Кабинет на сайте недоступен для соучастников (турниры, исключённые из клана). '
                        'Пользуйтесь ботом ВКонтакте.'
                    ),
                    'code': 'associate_no_cabinet',
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        if user.role == user.Role.GUEST and not user.is_superuser:
            return Response(
                {
                    'detail': (
                        'Вход в кабинет сайта только для участников клана. '
                        'Гости пользуются ботом ВКонтакте; после принятия заявки лидером откроется доступ сюда.'
                    ),
                    'code': 'guest_no_cabinet',
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = UserSerializer(user)
        return Response(serializer.data)

    def patch(self, request):
        """Обновление профиля (никнейм, UID, аватар) — только свои поля."""
        user = request.user
        if user.role == user.Role.BANNED and not user.is_superuser:
            return Response(
                {'detail': 'Доступ к сайту заблокирован.', 'code': 'banned_no_access'},
                status=status.HTTP_403_FORBIDDEN,
            )
        if user.role == user.Role.ASSOCIATE and not user.is_superuser:
            return Response(
                {'detail': 'Кабинет недоступен для соучастников.', 'code': 'associate_no_cabinet'},
                status=status.HTTP_403_FORBIDDEN,
            )
        if user.role == user.Role.GUEST and not user.is_superuser:
            return Response(
                {
                    'detail': (
                        'Вход в кабинет сайта только для участников клана. '
                        'Гости пользуются ботом ВКонтакте.'
                    ),
                    'code': 'guest_no_cabinet',
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        profile = getattr(user, 'profile', None)
        if not profile:
            profile = Profile.objects.create(user=user)
        data = dict(request.data)
        if 'uid' in data and not user.can_change_own_uid:
            return Response(
                {
                    'detail': (
                        'Игровой UID для вашей роли меняет лидер в разделе «Участники». '
                        'Гость и лидер могут менять UID сами (гость — в боте ВК).'
                    ),
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = ProfileSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserSerializer(user).data)


class ParticipantListView(generics.ListAPIView):
    """Список участников. Лидер или заместитель; у заместителя без гостей и соучастников."""
    serializer_class = UserListSerializer
    permission_classes = [IsAuthenticatedNotGuest]

    def get_queryset(self):
        return _managed_participants_queryset(self.request.user).order_by('-date_joined')

    def get_serializer_class(self):
        return UserListSerializer


class ParticipantDetailView(generics.RetrieveUpdateAPIView):
    """Детали/редактирование участника. Лидер или заместитель; заместитель — не гости и не соучастники."""
    permission_classes = [IsAuthenticatedNotGuest]

    def get_queryset(self):
        return _managed_participants_queryset(self.request.user)

    def get_serializer_class(self):
        if self.request.method in ('PUT', 'PATCH'):
            return ParticipantUpdateSerializer
        return UserListSerializer


class ClanPointsLedgerView(APIView):
    """
    GET — журнал ОК игрока (свой или при can_manage_clan_points — любого).
    POST — начисление/списание (amount ±), комментарий; только can_manage_clan_points.
    """

    permission_classes = [IsAuthenticatedNotGuest]

    def get_target(self, pk):
        target = get_object_or_404(_users_queryset_with_vk_accounts(), pk=pk)
        user = self.request.user
        if (
            user.pk != target.pk
            and user.role == User.Role.DEPUTY
            and target.role in (User.Role.GUEST, User.Role.ASSOCIATE)
        ):
            raise Http404()
        return target

    def can_read(self, request, target):
        if request.user.pk == target.pk:
            return True
        return request.user.can_manage_clan_points

    def get(self, request, pk):
        target = self.get_target(pk)
        if not self.can_read(request, target):
            return Response({'detail': 'Нет доступа к журналу ОК.'}, status=403)
        qs = (
            ClanPointsEntry.objects.filter(user=target)
            .select_related('created_by', 'created_by__profile')
            .order_by('-created_at')
        )
        return Response(ClanPointsEntryReadSerializer(qs, many=True).data)

    def post(self, request, pk):
        if not request.user.can_manage_clan_points:
            return Response({'detail': 'Нет прав на начисление или списание ОК.'}, status=403)
        target = self.get_target(pk)
        if not self.can_read(request, target):
            return Response({'detail': 'Нет доступа к игроку.'}, status=403)
        if target.role == User.Role.BANNED:
            return Response({'detail': 'Нельзя начислять или списывать ОК у забаненного пользователя.'}, status=403)
        raw_amount = request.data.get('amount')
        try:
            amount = int(raw_amount)
        except (TypeError, ValueError):
            return Response({'detail': 'Укажите целое число amount.', 'amount': ['Неверное значение.']}, status=400)
        if amount == 0:
            return Response({'detail': 'Сумма не может быть нулём.'}, status=400)
        comment = (request.data.get('comment') or '').strip()
        if not comment:
            return Response({'detail': 'Укажите комментарий.'}, status=400)
        with transaction.atomic():
            updated = (
                User.objects.select_for_update()
                .filter(pk=target.pk)
                .update(clan_points=F('clan_points') + amount)
            )
            if not updated:
                return Response({'detail': 'Пользователь не найден.'}, status=404)
            entry = ClanPointsEntry.objects.create(
                user_id=target.pk,
                amount=amount,
                comment=comment,
                created_by_id=request.user.pk,
            )
        target.refresh_from_db()
        return Response(
            {
                'participant': UserListSerializer(target).data,
                'entry': ClanPointsEntryReadSerializer(entry).data,
            },
            status=201,
        )


def _moderation_reason(request) -> tuple[str | None, Response | None]:
    raw = (request.data.get('reason') or '').strip()
    if len(raw) < 3:
        return None, Response(
            {'detail': 'Укажите причину (не короче 3 символов).', 'reason': ['Слишком коротко.']},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if len(raw) > 4000:
        return None, Response(
            {'detail': 'Причина слишком длинная.', 'reason': ['Не более 4000 символов.']},
            status=status.HTTP_400_BAD_REQUEST,
        )
    return raw, None


class ParticipantKickView(APIView):
    """Исключить из клана: роль «Соучастник», фиксируются дата, причина, кто исключил."""

    permission_classes = [IsAuthenticatedNotGuest]

    def post(self, request, pk):
        actor = request.user
        target = get_object_or_404(_managed_participants_queryset(actor), pk=pk)
        if not can_kick_from_clan(actor, target):
            return Response({'detail': 'Нет прав исключить этого пользователя из клана.'}, status=403)
        reason, err = _moderation_reason(request)
        if err:
            return err
        now = timezone.now()
        with transaction.atomic():
            u = User.objects.select_for_update().get(pk=target.pk)
            if not can_kick_from_clan(actor, u):
                return Response({'detail': 'Нет прав исключить этого пользователя из клана.'}, status=403)
            u.role = User.Role.ASSOCIATE
            u.kicked_at = now
            u.kick_reason = reason
            u.kicked_by = actor
            u.save(update_fields=['role', 'kicked_at', 'kick_reason', 'kicked_by'])
        u = get_object_or_404(_users_queryset_with_vk_accounts(), pk=pk)
        return Response(UserListSerializer(u).data)


class ParticipantBanView(APIView):
    """Бан: роль «Забанен», обнуление ОК, журнал, дата/причина/кто забанил."""

    permission_classes = [IsAuthenticatedNotGuest]

    def post(self, request, pk):
        actor = request.user
        target = get_object_or_404(_managed_participants_queryset(actor), pk=pk)
        if not can_ban_user(actor, target):
            return Response({'detail': 'Нет прав забанить этого пользователя.'}, status=403)
        reason, err = _moderation_reason(request)
        if err:
            return err
        now = timezone.now()
        with transaction.atomic():
            u = User.objects.select_for_update().get(pk=target.pk)
            if not can_ban_user(actor, u):
                return Response({'detail': 'Нет прав забанить этого пользователя.'}, status=403)
            prev = u.clan_points
            u.clan_points = 0
            u.role = User.Role.BANNED
            u.banned_at = now
            u.ban_reason = reason
            u.banned_by = actor
            u.save(update_fields=['clan_points', 'role', 'banned_at', 'ban_reason', 'banned_by'])
            if prev:
                ClanPointsEntry.objects.create(
                    user=u,
                    amount=-prev,
                    comment='Обнуление ОК при бане',
                    created_by=actor,
                )
        u = get_object_or_404(_users_queryset_with_vk_accounts(), pk=pk)
        return Response(UserListSerializer(u).data)


class ParticipantUnbanView(APIView):
    """Снять бан: роль «Гость», очистка полей бана (ОК не восстанавливаются)."""

    permission_classes = [IsAuthenticatedNotGuest]

    def post(self, request, pk):
        actor = request.user
        target = get_object_or_404(_managed_participants_queryset(actor), pk=pk)
        if not can_unban_user(actor, target):
            return Response({'detail': 'Нет прав снять бан с этого пользователя.'}, status=403)
        with transaction.atomic():
            u = User.objects.select_for_update().get(pk=target.pk)
            if u.role != User.Role.BANNED:
                return Response({'detail': 'Пользователь не в статусе «Забанен».'}, status=400)
            u.role = User.Role.GUEST
            u.banned_at = None
            u.ban_reason = ''
            u.banned_by = None
            u.save(update_fields=['role', 'banned_at', 'ban_reason', 'banned_by'])
        u = get_object_or_404(_users_queryset_with_vk_accounts(), pk=pk)
        return Response(UserListSerializer(u).data)
