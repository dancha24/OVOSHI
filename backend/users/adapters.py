"""django-allauth: соц. вход (VK и др.)."""
from django.conf import settings as dj_settings
from django.http import HttpResponseRedirect
from allauth.exceptions import ImmediateHttpResponse
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

from .models import Profile, User


class OvoshiSocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    VK ID не всегда отдаёт email (зависит от прав приложения и согласия).
    Для уникального email в БД подставляем технический адрес.

    Если тот же numeric id ВК уже есть в Profile (пользователь писал боту), вход через ВК
    привязывается к этому аккаунту — не создаётся второй User.

    Новые учётные записи через allauth не создаём: регистрация только через бота в группе ВК.
    """

    def is_open_for_signup(self, request, sociallogin):
        return False

    def pre_social_login(self, request, sociallogin):
        super().pre_social_login(request, sociallogin)
        if not sociallogin.is_existing and sociallogin.account.provider == 'vk':
            try:
                uid = int(str(sociallogin.account.uid).strip())
            except (ValueError, TypeError):
                uid = 0
            if uid >= 1:
                profile = Profile.objects.filter(vk_user_id=uid).select_related('user').first()
                if profile:
                    sociallogin.connect(request, profile.user)
        u = sociallogin.user
        if u is not None and getattr(u, 'pk', None) and u.role == User.Role.GUEST:
            login_url = f"{dj_settings.FRONTEND_URL.rstrip('/')}/login?cabinet_guest=1"
            raise ImmediateHttpResponse(HttpResponseRedirect(login_url))

    def populate_user(self, request, sociallogin, data):
        user = super().populate_user(request, sociallogin, data)
        email = (user.email or data.get('email') or '').strip()
        uid = str(sociallogin.account.uid).strip()
        provider = sociallogin.account.provider
        if not email and provider == 'vk' and uid:
            user.email = f'vk{uid}@oauth.ovoshi.local'
        if not (user.username or '').strip():
            base = (data.get('username') or data.get('screen_name') or '').strip() or f'vk_{uid}'[:120]
            user.username = self._unique_username(base)
        return user

    def _unique_username(self, base: str) -> str:
        from django.contrib.auth import get_user_model

        User = get_user_model()
        base = (base or 'user')[:140]
        if not User.objects.filter(username=base).exists():
            return base
        n = 1
        while n < 10000:
            candidate = f'{base}_{n}'[:150]
            if not User.objects.filter(username=candidate).exists():
                return candidate
            n += 1
        return f'{base}_x'[:150]
