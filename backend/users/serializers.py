import re

from rest_framework import serializers
from .models import ClanApplication, ClanPointsEntry, Profile, User, age_years_from_birth  # noqa: F401

_VK_BOT_EMAIL_PREFIX = re.compile(r'^vk(\d+)@', re.IGNORECASE)
_PARTICIPANT_BIRTH_UNSET = object()


def _vk_name_from_extra_data(extra_data) -> str:
    """Имя и фамилия из extra_data SocialAccount (VK ID: vk_id_user; старый OAuth — корень или response)."""
    if not isinstance(extra_data, dict):
        return ''
    vu = extra_data.get('vk_id_user')
    if isinstance(vu, dict):
        parts = []
        for key in ('first_name', 'last_name'):
            s = (vu.get(key) or '').strip()
            if s:
                parts.append(s)
        if parts:
            return ' '.join(parts)
    fn = (extra_data.get('first_name') or '').strip()
    ln = (extra_data.get('last_name') or '').strip()
    parts = [x for x in (fn, ln) if x]
    if parts:
        return ' '.join(parts)
    resp = extra_data.get('response')
    if isinstance(resp, list) and resp:
        u0 = resp[0]
        if isinstance(u0, dict):
            parts = []
            for key in ('first_name', 'last_name'):
                s = (u0.get(key) or '').strip()
                if s:
                    parts.append(s)
            if parts:
                return ' '.join(parts)
    return ''


def _moderator_label(mod: User | None) -> str | None:
    if mod is None:
        return None
    prof = getattr(mod, 'profile', None)
    nick = (prof.nickname or '').strip() if prof else ''
    base = f'#{mod.pk}'
    if nick:
        return f'{base} {nick}'
    return base


def _vk_display_name_for_user(user: User) -> str:
    """Имя из привязанного ВК; иначе никнейм профиля; иначе «—»."""
    for sa in user.socialaccount_set.all():
        if sa.provider not in ('vk', 'vk_oauth2'):
            continue
        name = _vk_name_from_extra_data(sa.extra_data or {})
        if name:
            return name
    if hasattr(user, 'profile') and user.profile:
        nick = (user.profile.nickname or '').strip()
        if nick:
            return nick
    return '—'


class ProfileSerializer(serializers.ModelSerializer):
    age_years = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = ('nickname', 'uid', 'avatar', 'birth_date', 'age_years')
        read_only_fields = ('age_years',)
        extra_kwargs = {
            'nickname': {'max_length': 50, 'allow_blank': True},
            'birth_date': {'required': False, 'allow_null': True},
        }

    def get_age_years(self, obj):
        return obj.age_years

    def validate_birth_date(self, value):
        if value is None:
            return value
        ay = age_years_from_birth(value)
        if ay is None or ay < 5 or ay > 120:
            raise serializers.ValidationError('Возраст по дате должен быть от 5 до 120 лет.')
        return value

    def validate_nickname(self, value):
        if value and len(value) > 50:
            raise serializers.ValidationError('Не длиннее 50 символов.')
        return value


class UserSerializer(serializers.ModelSerializer):
    profile = serializers.SerializerMethodField()
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    can_access_leader_cabinet = serializers.ReadOnlyField()
    can_manage_clan_points = serializers.ReadOnlyField()
    can_manage_settings = serializers.ReadOnlyField()
    can_change_own_uid = serializers.ReadOnlyField()

    class Meta:
        model = User
        fields = (
            'id', 'email', 'username', 'role', 'role_display',
            'clan_points',  # 'karma',  # временно скрыто
            'uid_confirmed',
            'is_staff',
            'is_superuser',
            'can_access_leader_cabinet',
            'can_manage_clan_points',
            'can_manage_settings',
            'can_change_own_uid',
            'profile',
        )
        read_only_fields = (
            'id', 'email', 'username', 'role', 'clan_points',  # 'karma',
            'uid_confirmed',
            'is_staff', 'is_superuser', 'can_access_leader_cabinet',
            'can_manage_clan_points', 'can_manage_settings', 'can_change_own_uid',
        )

    def get_profile(self, obj):
        profile = getattr(obj, 'profile', None)
        if profile:
            return ProfileSerializer(profile).data
        return {'nickname': '', 'uid': '', 'avatar': None, 'birth_date': None, 'age_years': None}


class UserListSerializer(serializers.ModelSerializer):
    """Для таблицы участников (никнейм, дата рождения, возраст, UID, очки). Карма временно скрыта в API."""
    nickname = serializers.SerializerMethodField()
    uid = serializers.SerializerMethodField()
    vk_user_id = serializers.SerializerMethodField()
    vk_display_name = serializers.SerializerMethodField()
    birth_date = serializers.SerializerMethodField()
    age_years = serializers.SerializerMethodField()
    kicked_by_label = serializers.SerializerMethodField()
    banned_by_label = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id', 'vk_display_name', 'nickname', 'birth_date', 'age_years', 'uid', 'vk_user_id',
            'clan_points',  # 'karma',
            'role', 'uid_confirmed',
            'kicked_at', 'kick_reason', 'kicked_by_label',
            'banned_at', 'ban_reason', 'banned_by_label',
        )

    def get_nickname(self, obj):
        return getattr(obj.profile, 'nickname', '') if hasattr(obj, 'profile') and obj.profile else ''

    def _profile(self, obj):
        return obj.profile if hasattr(obj, 'profile') else None

    def get_birth_date(self, obj):
        prof = self._profile(obj)
        if not prof or not prof.birth_date:
            return None
        return prof.birth_date.isoformat()

    def get_age_years(self, obj):
        prof = self._profile(obj)
        if not prof:
            return None
        return prof.age_years

    def get_uid(self, obj):
        return getattr(obj.profile, 'uid', '') if hasattr(obj, 'profile') and obj.profile else ''

    def get_vk_display_name(self, obj):
        return _vk_display_name_for_user(obj)

    def get_vk_user_id(self, obj):
        if hasattr(obj, 'profile') and obj.profile and obj.profile.vk_user_id is not None:
            return int(obj.profile.vk_user_id)
        m = _VK_BOT_EMAIL_PREFIX.match((obj.email or '').strip())
        if m:
            return int(m.group(1))
        return None

    def get_kicked_by_label(self, obj):
        return _moderator_label(obj.kicked_by)

    def get_banned_by_label(self, obj):
        return _moderator_label(obj.banned_by)


class ClanPointsEntryReadSerializer(serializers.ModelSerializer):
    """Строка журнала ОК для API."""
    created_by_label = serializers.SerializerMethodField()

    class Meta:
        model = ClanPointsEntry
        fields = ('id', 'amount', 'comment', 'created_at', 'created_by', 'created_by_label')
        read_only_fields = fields

    def get_created_by_label(self, obj):
        u = obj.created_by
        if not u:
            return '—'
        nick = ''
        prof = getattr(u, 'profile', None)
        if prof:
            nick = (prof.nickname or '').strip()
        base = f'#{u.pk}'
        if nick:
            return f'{base} {nick}'
        return f'{base} {u.email}'


class ParticipantUpdateSerializer(serializers.ModelSerializer):
    """Обновление участника лидером/замом: профиль, роль. ОК — журнал; карма временно не в API."""
    nickname = serializers.CharField(required=False, allow_blank=True, max_length=50)
    uid = serializers.CharField(required=False, allow_blank=True, max_length=50)
    birth_date = serializers.DateField(required=False, allow_null=True)

    class Meta:
        model = User
        fields = ('nickname', 'uid', 'birth_date', 'role', 'uid_confirmed')  # 'karma' временно

    def validate_role(self, value):
        if value in (User.Role.ASSOCIATE, User.Role.BANNED):
            raise serializers.ValidationError(
                'Роли «Соучастник» и «Забанен» задаются через действия «Исключить из клана» и «Забанить».'
            )
        return value

    def validate_birth_date(self, value):
        if value is None:
            return value
        ay = age_years_from_birth(value)
        if ay is None or ay < 5 or ay > 120:
            raise serializers.ValidationError('Возраст по дате должен быть от 5 до 120 лет.')
        return value

    def update(self, instance, validated_data):
        old_role = instance.role
        new_role = validated_data.get('role', old_role)
        nickname = validated_data.pop('nickname', None)
        uid = validated_data.pop('uid', None)
        birth_date = validated_data.pop('birth_date', _PARTICIPANT_BIRTH_UNSET)
        profile = getattr(instance, 'profile', None) or Profile.objects.get_or_create(user=instance)[0]
        if nickname is not None:
            profile.nickname = nickname
        if uid is not None:
            profile.uid = uid
        if birth_date is not _PARTICIPANT_BIRTH_UNSET:
            profile.birth_date = birth_date
        profile.save()
        instance = super().update(instance, validated_data)
        if new_role == User.Role.PLAYER and old_role == User.Role.ASSOCIATE:
            User.objects.filter(pk=instance.pk).update(
                kicked_at=None,
                kick_reason='',
                kicked_by_id=None,
            )
            instance.refresh_from_db(fields=('kicked_at', 'kick_reason', 'kicked_by', 'role'))
        return instance


class ClanApplicationReadSerializer(serializers.ModelSerializer):
    """Заявка в клан — просмотр лидером (email в списке не отдаём)."""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    age_years = serializers.SerializerMethodField()

    class Meta:
        model = ClanApplication
        fields = (
            'id',
            'created_at',
            'resolved_at',
            'status',
            'status_display',
            'status_comment',
            'user',
            'nickname',
            'uid',
            'birth_date',
            'age_years',
            'city',
            'vk_user_id',
            'clan_points_snapshot',
        )
        read_only_fields = fields

    def get_age_years(self, obj):
        return obj.age_years


class ClanApplicationDecisionSerializer(serializers.ModelSerializer):
    """Принятие / отклонение только из статуса «на рассмотрении»; комментарий обязателен."""

    status_comment = serializers.CharField(required=False, allow_blank=True, max_length=4000)

    class Meta:
        model = ClanApplication
        fields = ('status', 'status_comment')

    def validate_status(self, value):
        if value not in (ClanApplication.Status.APPROVED, ClanApplication.Status.REJECTED):
            raise serializers.ValidationError('Укажите approved или rejected.')
        return value

    def validate(self, attrs):
        if self.instance and self.instance.status != ClanApplication.Status.PENDING:
            raise serializers.ValidationError({'detail': 'Заявка уже обработана.'})
        if 'status' not in attrs:
            raise serializers.ValidationError({'status': 'Укажите approved или rejected.'})
        initial = getattr(self, 'initial_data', None)
        comment = attrs.get('status_comment')
        if initial is not None and 'status_comment' in initial:
            raw = initial.get('status_comment')
            if isinstance(raw, list):
                raw = raw[0] if raw else ''
            comment = str(raw).strip() if raw is not None else ''
        else:
            comment = (comment or '').strip() if comment is not None else ''
        if not comment:
            raise serializers.ValidationError({'status_comment': 'Укажите комментарий к решению.'})
        if comment == 'На рассмотрении':
            raise serializers.ValidationError(
                {
                    'status_comment': (
                        'Нельзя оставить текст «На рассмотрении» — введите комментарий к принятию или отклонению.'
                    )
                }
            )
        attrs['status_comment'] = comment
        return attrs

    def update(self, instance, validated_data):
        from django.utils import timezone

        from .clan_notify import send_clan_application_decision_vk

        new_status = validated_data['status']
        instance.status_comment = validated_data['status_comment']
        instance.status = new_status
        instance.resolved_at = timezone.now()
        instance.save(update_fields=['status', 'status_comment', 'resolved_at'])

        user = instance.user
        if new_status == ClanApplication.Status.APPROVED:
            if user.role == User.Role.GUEST:
                user.role = User.Role.PLAYER
                user.save(update_fields=['role'])
            elif user.role == User.Role.ASSOCIATE:
                user.role = User.Role.PLAYER
                user.kicked_at = None
                user.kick_reason = ''
                user.kicked_by = None
                user.save(update_fields=['role', 'kicked_at', 'kick_reason', 'kicked_by'])

        send_clan_application_decision_vk(instance)
        return instance
