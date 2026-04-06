"""Вход через VK ID (PKCE), без редиректа на allauth /accounts/vk/login/."""
import os

from django.conf import settings
from django.contrib.auth import login
from django.db import IntegrityError, transaction
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from allauth.socialaccount.models import SocialAccount

from .bot_users import resolve_user_by_vk_id
from .models import User
from .serializers import UserSerializer
from .vkid import exchange_vk_id_code, fetch_vk_id_user_info


def _vk_public_group_url() -> str:
    try:
        from core.models import SiteSettings

        row = SiteSettings.objects.only('vk_public_url').first()
        if row and (row.vk_public_url or '').strip():
            return row.vk_public_url.strip()
    except Exception:
        pass
    return ''


def _vk_client_id_configured() -> bool:
    if (os.environ.get('VK_CLIENT_ID') or '').strip():
        return True
    prov = getattr(settings, 'SOCIALACCOUNT_PROVIDERS', {}) or {}
    vk = prov.get('vk') or {}
    app = vk.get('APP') or {}
    return bool((app.get('client_id') or '').strip())


class VkIdConfigView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        env_id = (os.environ.get('VK_CLIENT_ID') or '').strip()
        prov = getattr(settings, 'SOCIALACCOUNT_PROVIDERS', {}) or {}
        vk = prov.get('vk') or {}
        app = vk.get('APP') or {}
        settings_id = (app.get('client_id') or '').strip()
        client_id = env_id or settings_id
        return Response({'client_id': client_id})


class VkIdCompleteView(APIView):
    """POST: code + PKCE + redirect_uri с фронта после колбэка VK ID на /login."""
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        if not _vk_client_id_configured():
            return Response(
                {'error': 'VK ID не настроен (VK_CLIENT_ID).'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        d = request.data
        code = (d.get('code') or '').strip()
        device_id = (d.get('device_id') or d.get('deviceId') or '').strip()
        code_verifier = (d.get('code_verifier') or d.get('codeVerifier') or '').strip()
        st = (d.get('state') or '').strip()
        redirect_uri = (d.get('redirect_uri') or d.get('redirectUri') or '').strip()

        if not code or not device_id or not code_verifier or not st or not redirect_uri:
            return Response(
                {'error': 'Не хватает параметров VK ID (code, device_id, code_verifier, state, redirect_uri).'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            token_json = exchange_vk_id_code(
                code=code,
                device_id=device_id,
                code_verifier=code_verifier,
                state=st,
                redirect_uri=redirect_uri,
            )
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except OSError:
            return Response(
                {'error': 'Не удалось связаться с VK ID. Попробуйте позже.'},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        access_token = token_json.get('access_token') if isinstance(token_json, dict) else None
        if not access_token or not isinstance(access_token, str):
            msg = token_json.get('error_description') if isinstance(token_json, dict) else None
            return Response(
                {'error': (msg or 'Обмен кода VK ID не удался.')},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user_info_json = fetch_vk_id_user_info(access_token)
        except (ValueError, OSError):
            return Response(
                {'error': 'Не удалось получить профиль VK ID.'},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        vk_user = user_info_json.get('user') if isinstance(user_info_json, dict) else None
        if not isinstance(vk_user, dict):
            return Response({'error': 'Некорректный ответ user_info VK ID.'}, status=status.HTTP_400_BAD_REQUEST)

        provider_account_id = vk_user.get('user_id')
        if not provider_account_id or not isinstance(provider_account_id, str):
            return Response({'error': 'VK не вернул user_id.'}, status=status.HTTP_400_BAD_REQUEST)
        provider_account_id = provider_account_id.strip()
        if not provider_account_id:
            return Response({'error': 'VK не вернул user_id.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            vk_numeric = int(provider_account_id)
        except (ValueError, TypeError):
            return Response({'error': 'Некорректный VK user_id.'}, status=status.HTTP_400_BAD_REQUEST)
        if vk_numeric < 1:
            return Response({'error': 'Некорректный VK user_id.'}, status=status.HTTP_400_BAD_REQUEST)

        user = resolve_user_by_vk_id(vk_numeric)
        if not user:
            group_url = _vk_public_group_url()
            payload = {
                'error': (
                    'Учётная запись не найдена. Сначала зарегистрируйтесь через сообщество ВКонтакте '
                    '(напишите боту в группе клана), затем войдите здесь тем же аккаунтом ВК.'
                ),
                'code': 'registration_via_group_only',
            }
            if group_url:
                payload['vk_group_url'] = group_url
            return Response(payload, status=status.HTTP_403_FORBIDDEN)

        extra_data = {
            'id': provider_account_id,
            'vk_id_user': vk_user,
            'token': {k: token_json.get(k) for k in ('token_type', 'expires_in', 'scope') if isinstance(token_json, dict)},
        }

        sa = SocialAccount.objects.filter(provider='vk', uid=provider_account_id).select_related('user').first()
        if sa is not None and sa.user_id != user.pk:
            return Response(
                {'error': 'Этот профиль ВКонтакте уже привязан к другой учётной записи.'},
                status=status.HTTP_409_CONFLICT,
            )

        try:
            with transaction.atomic():
                if sa is not None:
                    sa = SocialAccount.objects.select_for_update().get(pk=sa.pk)
                    sa.extra_data = extra_data
                    sa.save(update_fields=['extra_data'])
                else:
                    SocialAccount.objects.create(
                        user=user,
                        provider='vk',
                        uid=provider_account_id,
                        extra_data=extra_data,
                    )
        except IntegrityError:
            return Response(
                {'error': 'Аккаунт ВКонтакте уже используется или конфликт данных.'},
                status=status.HTTP_409_CONFLICT,
            )

        if user.role == User.Role.BANNED:
            return Response(
                {
                    'error': 'Доступ к сайту заблокирован администрацией клана.',
                    'code': 'banned_no_access',
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        if user.role == User.Role.ASSOCIATE:
            group_url = _vk_public_group_url()
            payload = {
                'error': (
                    'Соучастники (турниры, исключённые из клана) не входят в кабинет на сайте — '
                    'пользуйтесь ботом ВКонтакте.'
                ),
                'code': 'associate_no_cabinet',
            }
            if group_url:
                payload['vk_group_url'] = group_url
            return Response(payload, status=status.HTTP_403_FORBIDDEN)
        if user.role == User.Role.GUEST:
            group_url = _vk_public_group_url()
            payload = {
                'error': (
                    'Гости не входят в кабинет на сайте — пользуйтесь ботом ВКонтакте в сообществе. '
                    'После принятия заявки в клан лидером здесь откроется вход.'
                ),
                'code': 'guest_no_cabinet',
            }
            if group_url:
                payload['vk_group_url'] = group_url
            return Response(payload, status=status.HTTP_403_FORBIDDEN)

        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        return Response(UserSerializer(user).data)
