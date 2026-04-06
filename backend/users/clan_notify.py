"""Уведомление заявителя о решении по заявке в клан (ВК)."""
import logging

from .models import ClanApplication, Profile

logger = logging.getLogger(__name__)


def resolve_vk_peer_id(application: ClanApplication) -> int | None:
    """
    Куда писать в ВК: снимок на заявке, иначе профиль, иначе привязка VK (вход на сайте).
    """
    if application.vk_user_id is not None:
        try:
            return int(application.vk_user_id)
        except (TypeError, ValueError):
            pass
    user = application.user
    profile = getattr(user, 'profile', None)
    if profile is None:
        profile = Profile.objects.filter(user=user).first()
    if profile and profile.vk_user_id is not None:
        try:
            return int(profile.vk_user_id)
        except (TypeError, ValueError):
            pass
    from allauth.socialaccount.models import SocialAccount

    for acc in SocialAccount.objects.filter(user=user, provider__in=('vk', 'vk_oauth2')):
        try:
            return int(str(acc.uid).strip())
        except (ValueError, TypeError):
            continue
    return None


def send_clan_application_decision_vk(application: ClanApplication) -> bool:
    """Сообщение в личку ВК со статусом и комментарием лидера."""
    from vkbot.outgoing import vk_send_message

    peer = resolve_vk_peer_id(application)
    if not peer:
        logger.warning(
            'Заявка %s: нет VK peer (ни в заявке, ни в профиле, ни в socialaccount) — уведомление не отправлено',
            application.pk,
        )
        return False
    lines = [
        'OVOSHI: решение по заявке в клан',
        '',
        f'Статус: {application.get_status_display()}',
        f'Комментарий: {application.status_comment or "—"}',
    ]
    text = '\n'.join(lines)
    ok = vk_send_message(peer, text, keyboard=None)
    if not ok:
        logger.error(
            'Заявка %s: VK messages.send не доставил сообщение (peer_id=%s)',
            application.pk,
            peer,
        )
    return ok
