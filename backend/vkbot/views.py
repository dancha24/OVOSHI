"""
Callback API сообщества ВКонтакте.
"""
import datetime as dt
import json
import logging
import re
import unicodedata

from django.conf import settings
from django.utils import timezone as dj_tz
from django.core.cache import cache
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from core.models import ShopLot, SiteSettings
from users.bot_users import ensure_vk_player
from users.models import ClanApplication, Profile, User, age_years_from_birth

from .outgoing import vk_send_message as _vk_send_message
from .vk_media import vk_upload_message_photo

logger = logging.getLogger(__name__)

VK_API = 'https://api.vk.com/method'


def _format_birth_ru(birth_date) -> str:
    if not birth_date:
        return ''
    return birth_date.strftime('%d.%m.%Y')

_ZW_RE = re.compile(r'[\u200b-\u200d\ufeff\u00a0]')

_VK_PROFILE_CACHE_TIMEOUT = 30 * 60


def _norm_text(text: str) -> str:
    t = unicodedata.normalize('NFKC', (text or '').strip())
    t = _ZW_RE.sub('', t)
    return t.lower()


def _menu_keyboard() -> dict:
    """
    Inline-клавиатура под сообщением.
    У сообществ ВК «нижняя» клавиатура (inline: false) часто не рисуется в чате —
    inline: true показывает кнопки сразу под ответом бота.
    """
    def txt(label: str, cmd: str) -> dict:
        # payload — маршрутизация по нажатию (текст с кнопки иногда «ломается» в Unicode)
        return {
            'action': {
                'type': 'text',
                'label': label,
                'payload': json.dumps({'cmd': cmd}, separators=(',', ':')),
            },
        }

    return {
        'one_time': False,
        'inline': True,
        'buttons': [
            [txt('Магаз', 'shop'), txt('Вступить', 'join'), txt('Помощь', 'help')],
            [txt('Мой профиль', 'profile')],
        ],
    }


def _public_media_url(lot: ShopLot) -> str:
    if not lot.image:
        return ''
    base = getattr(settings, 'BACKEND_PUBLIC_URL', '') or getattr(settings, 'FRONTEND_URL', '')
    if not base:
        return ''
    base = base.rstrip('/')
    name = lot.image.name.lstrip('/')
    media = settings.MEDIA_URL.strip('/')
    return f'{base}/{media}/{name}'


def _welcome_text() -> str:
    return (
        'Добро пожаловать в OVOSHI!\n\n'
        'Что тебе нужно? Выбери кнопку ниже.\n\n'
        'Магаз — каталог лотов за очки клана (ОК).\n'
        'Мой профиль — никнейм, баланс ОК, UID, дата рождения, город.\n'
        'Вступить — правила, контакт набора и кнопка «Подать заявку» в клан '
        '(нужны никнейм, UID, дата рождения и город в профиле).\n'
        'Помощь — вопрос администратору.'
    )


def _vk_payload_button(label: str, cmd: str, **extra) -> dict:
    payload = {'cmd': cmd, **extra}
    return {
        'action': {
            'type': 'text',
            'label': label,
            'payload': json.dumps(payload, separators=(',', ':')),
        },
    }


def _profile_card_keyboard(site_user) -> dict:
    row1 = [_vk_payload_button('Никнейм', 'profile_edit_nick')]
    if site_user.can_change_own_uid:
        row1.append(_vk_payload_button('UID', 'profile_edit_uid'))
    return {
        'one_time': False,
        'inline': True,
        'buttons': [
            row1,
            [
                _vk_payload_button('Дата рождения', 'profile_edit_birth'),
                _vk_payload_button('Город', 'profile_edit_city'),
            ],
            [_vk_payload_button('Главное меню', 'menu')],
        ],
    }


def _profile_cancel_edit_keyboard() -> dict:
    return {
        'one_time': False,
        'inline': True,
        'buttons': [[_vk_payload_button('Отмена', 'profile')]],
    }


def _vk_profile_wait_nick_key(peer_id: int) -> str:
    return f'vk_prof_nick:{peer_id}'


def _vk_profile_wait_uid_key(peer_id: int) -> str:
    return f'vk_prof_uid:{peer_id}'


def _vk_profile_wait_birth_key(peer_id: int) -> str:
    return f'vk_prof_birth:{peer_id}'


def _vk_profile_wait_city_key(peer_id: int) -> str:
    return f'vk_prof_city:{peer_id}'


def _vk_clear_profile_input_waits(peer_id: int) -> None:
    cache.delete(_vk_profile_wait_nick_key(peer_id))
    cache.delete(_vk_profile_wait_uid_key(peer_id))
    cache.delete(_vk_profile_wait_birth_key(peer_id))
    cache.delete(_vk_profile_wait_city_key(peer_id))


def _profile_display_line(label: str, value: str) -> str:
    return f'{label}: {value}' if value else f'{label}: не задан'


def _profile_card_text(site_user) -> str:
    profile, _ = Profile.objects.get_or_create(user=site_user)
    nick = (profile.nickname or '').strip()
    uid = (profile.uid or '').strip()
    city = (profile.city or '').strip()
    bal = site_user.clan_points
    bd_s = _format_birth_ru(profile.birth_date)
    age_s = str(profile.age_years) if profile.age_years is not None else ''
    lines = [
        'Мой профиль',
        '',
        _profile_display_line('Никнейм', nick),
        _profile_display_line('Баланс', f'{bal} ОК'),
        _profile_display_line('UID', uid),
        _profile_display_line('Дата рождения', bd_s),
        _profile_display_line('Возраст', f'{age_s} лет' if age_s else ''),
        _profile_display_line('Город', city),
    ]
    return '\n'.join(lines)


def _send_profile_vk(peer_id: int, from_id: int) -> None:
    _clear_vk_help_wait(peer_id)
    u = ensure_vk_player(from_id)
    u = type(u).objects.select_related('profile').get(pk=u.pk)
    _vk_send_message(peer_id, _profile_card_text(u), _profile_card_keyboard(u))


def _start_profile_edit_nick(peer_id: int) -> None:
    _vk_clear_profile_input_waits(peer_id)
    cache.set(_vk_profile_wait_nick_key(peer_id), True, timeout=_VK_PROFILE_CACHE_TIMEOUT)
    _vk_send_message(
        peer_id,
        'Напиши новый никнейм одним сообщением (до 50 символов).\n'
        'Чтобы сбросить ник, отправь «-».\n'
        '«Меню» — в главное меню.',
        _profile_cancel_edit_keyboard(),
    )


def _start_profile_edit_uid(peer_id: int) -> None:
    _vk_clear_profile_input_waits(peer_id)
    cache.set(_vk_profile_wait_uid_key(peer_id), True, timeout=_VK_PROFILE_CACHE_TIMEOUT)
    _vk_send_message(
        peer_id,
        'Напиши игровой UID одним сообщением.\n'
        'Чтобы сбросить UID, отправь «-».\n'
        '«Меню» — в главное меню.',
        _profile_cancel_edit_keyboard(),
    )


def _start_profile_edit_birth(peer_id: int) -> None:
    _vk_clear_profile_input_waits(peer_id)
    cache.set(_vk_profile_wait_birth_key(peer_id), True, timeout=_VK_PROFILE_CACHE_TIMEOUT)
    _vk_send_message(
        peer_id,
        'Напиши дату рождения в формате ДД.ММ.ГГГГ (день.месяц.год), например 15.08.2003.\n'
        'Возраст в профиле считается автоматически.\n'
        'Чтобы сбросить дату, отправь «-».\n'
        '«Меню» — в главное меню.',
        _profile_cancel_edit_keyboard(),
    )


def _start_profile_edit_city(peer_id: int) -> None:
    _vk_clear_profile_input_waits(peer_id)
    cache.set(_vk_profile_wait_city_key(peer_id), True, timeout=_VK_PROFILE_CACHE_TIMEOUT)
    _vk_send_message(
        peer_id,
        'Напиши город одним сообщением (до 120 символов).\n'
        'Чтобы сбросить, отправь «-».\n'
        '«Меню» — в главное меню.',
        _profile_cancel_edit_keyboard(),
    )


def _parse_birth_date_input(raw: str) -> tuple[str, dt.date | None]:
    """('clear', None) | ('bad', None) | ('ok', date). Возраст по дате: 5–120 лет."""
    s = (raw or '').strip()
    if s in ('-', '—'):
        return ('clear', None)
    parts = s.split('.')
    if len(parts) != 3:
        return ('bad', None)
    try:
        d, m, y = int(parts[0]), int(parts[1]), int(parts[2])
    except ValueError:
        return ('bad', None)
    try:
        birth = dt.date(y, m, d)
    except ValueError:
        return ('bad', None)
    today = dj_tz.now().date()
    if birth > today:
        return ('bad', None)
    ay = age_years_from_birth(birth)
    if ay is None or ay < 5 or ay > 120:
        return ('bad', None)
    return ('ok', birth)


def _apply_profile_field(raw: str, max_len: int) -> str:
    s = (raw or '').strip()
    if s in ('-', '—'):
        return ''
    return s[:max_len]


def _should_leave_profile_edit_mode(t: str) -> bool:
    if t in ('меню', 'отмена', 'назад', 'start', '/start', 'начать'):
        return True
    if t in ('магаз', 'магазин', 'shop') or 'магаз' in t:
        return True
    if t in ('вступить', 'вступление') or t.startswith('вступ'):
        return True
    if t in ('помощь', 'help', '?') or t.startswith('помощ'):
        return True
    if t in ('профиль', 'мой профиль', 'profile') or 'профиль' in t:
        return True
    greetings = ('привет', 'hi', 'hello', 'добро пожаловать')
    if t in greetings:
        return True
    if t in ('заявка', 'подать заявку', 'заявку') or 'заявк' in t:
        return True
    return False


def _recruiter_url_for_bot() -> str:
    """Ссылка на наборщика: из настроек сайта, иначе VK_BOT_RECRUITER_URL в .env."""
    try:
        u = (SiteSettings.load().recruiter_url or '').strip()
        if u:
            return u
    except Exception:
        pass
    return (getattr(settings, 'VK_BOT_RECRUITER_URL', '') or '').strip()


def _join_text() -> str:
    rules = getattr(settings, 'VK_BOT_RULES_URL', '')
    rec = _recruiter_url_for_bot()
    return (
        'Чтобы вступить в клан:\n\n'
        f'1) Ознакомься с правилами и плюшками:\n{rules}\n\n'
        f'2) Напиши наборщику:\n{rec}\n\n'
        '3) В «Мой профиль» укажи никнейм, игровой UID, дату рождения (ДД.ММ.ГГГГ) и город, затем нажми «Подать заявку» — '
        'лидер получит заявку в боте, заявка сохранится в админке сайта.'
    )


def _join_keyboard() -> dict:
    """Экран вступления: заявка + переход в профиль / меню."""
    return {
        'one_time': False,
        'inline': True,
        'buttons': [
            [_vk_payload_button('Подать заявку', 'apply')],
            [
                _vk_payload_button('Мой профиль', 'profile'),
                _vk_payload_button('Главное меню', 'menu'),
            ],
        ],
    }


def _is_profile_complete(site_user) -> bool:
    profile, _ = Profile.objects.get_or_create(user=site_user)
    nick = (profile.nickname or '').strip()
    uid = (profile.uid or '').strip()
    city = (profile.city or '').strip()
    ay = profile.age_years
    birth_ok = ay is not None and 5 <= ay <= 120
    return bool(nick and uid and city and birth_ok)


def _profile_missing_for_apply_labels(profile) -> list[str]:
    miss: list[str] = []
    if not (profile.nickname or '').strip():
        miss.append('никнейм')
    if not (profile.uid or '').strip():
        miss.append('UID')
    ay = profile.age_years
    if ay is None or not (5 <= ay <= 120):
        miss.append('дата рождения')
    if not (profile.city or '').strip():
        miss.append('город')
    return miss


def _apply_need_profile_keyboard() -> dict:
    return {
        'one_time': False,
        'inline': True,
        'buttons': [
            [_vk_payload_button('Мой профиль', 'profile')],
            [_vk_payload_button('Главное меню', 'menu')],
        ],
    }


def _notify_admin_clan_application_vk(
    from_id: int,
    peer_id: int,
    site_user,
    profile: Profile,
    application_id: int,
) -> bool:
    aid = getattr(settings, 'VK_BOT_ADMIN_VK_ID', '') or ''
    if not aid.isdigit():
        return False
    nick = (profile.nickname or '').strip()
    uid = (profile.uid or '').strip()
    city = (profile.city or '').strip()
    bd_s = _format_birth_ru(profile.birth_date) or '—'
    ay = profile.age_years
    age_part = f' (полных лет: {ay})' if ay is not None else ''
    text = (
        f'Заявка в клан #{application_id}\n'
        f'ВК: https://vk.com/id{from_id}\n'
        f'Никнейм: {nick}\n'
        f'UID: {uid}\n'
        f'Дата рождения: {bd_s}{age_part}\n'
        f'Город: {city}\n'
        f'ОК: {site_user.clan_points}\n'
        f'peer_id: {peer_id}'
    )
    return _vk_send_message(int(aid), text, keyboard=None)


def _clan_application_public_comment(app: ClanApplication) -> str:
    """Текст комментария для пользователя: из БД или значение по умолчанию для ожидания."""
    c = (app.status_comment or '').strip()
    if c:
        return c
    if app.status == ClanApplication.Status.PENDING:
        return 'На рассмотрении'
    return '—'


def _clan_application_duplicate_reply(app: ClanApplication) -> str:
    return (
        'Ты уже отправил заявку в клан. Повторно подать нельзя.\n\n'
        f'Статус: {app.get_status_display()}\n'
        f'Комментарий: {_clan_application_public_comment(app)}'
    )


def _handle_clan_apply_vk(peer_id: int, from_id: int) -> None:
    """Заявка в клан: никнейм, UID, дата рождения, город. Одна заявка на пользователя."""
    u = ensure_vk_player(from_id)
    existing = ClanApplication.objects.filter(user=u).order_by('-created_at').first()
    if existing:
        _vk_send_message(peer_id, _clan_application_duplicate_reply(existing), _join_keyboard())
        return
    profile, _ = Profile.objects.get_or_create(user=u)
    if not _is_profile_complete(u):
        parts = _profile_missing_for_apply_labels(profile)
        tail = ', '.join(parts) if parts else 'данных'
        _vk_send_message(
            peer_id,
            'Заявку можно отправить только с заполненным профилем.\n'
            f'Сейчас не указано: {tail}.\n\n'
            'Нажми «Мой профиль» и заполни недостающие поля (никнейм, UID, дата рождения, город), '
            'затем снова открой «Вступить» и нажми «Подать заявку».',
            _apply_need_profile_keyboard(),
        )
        return
    u = type(u).objects.select_related('profile').get(pk=u.pk)
    profile = u.profile
    nick = (profile.nickname or '').strip()
    uid = (profile.uid or '').strip()
    city = (profile.city or '').strip()
    app = ClanApplication.objects.create(
        user=u,
        nickname=nick,
        uid=uid,
        birth_date=profile.birth_date,
        city=city,
        vk_user_id=from_id,
        clan_points_snapshot=u.clan_points,
        status_comment='На рассмотрении',
    )
    admin_id = getattr(settings, 'VK_BOT_ADMIN_VK_ID', '') or ''
    admin_ok = _notify_admin_clan_application_vk(from_id, peer_id, u, profile, app.pk)
    if admin_ok:
        reply = (
            'Заявка отправлена лидеру и сохранена. В профиле переданы никнейм, UID, дата рождения, город и ссылка на твою страницу ВК. '
            'О решении сообщат отдельно; при необходимости напиши в «Помощь».'
        )
    elif not admin_id.isdigit():
        reply = (
            'Профиль заполнен, но VK_BOT_ADMIN_VK_ID не задан — заявку через бота не кому доставить. '
            'Напиши наборщику по ссылке из пункта «Вступить».'
        )
    else:
        reply = (
            'Заявка сформирована, но ВК не доставил уведомление лидеру. '
            'Напиши наборщику из раздела «Вступить» или в «Помощь».'
        )
    _vk_send_message(peer_id, reply, _menu_keyboard())


def _help_text() -> str:
    return (
        'Напиши, чем мы можем помочь — администратор увидит твоё обращение '
        'и сможет ответить в этом диалоге с сообществом.'
    )


def _vk_help_wait_key(peer_id: int) -> str:
    return f'vk_help_wait:{peer_id}'


def _clear_vk_help_wait(peer_id: int) -> None:
    cache.delete(_vk_help_wait_key(peer_id))
    _vk_clear_profile_input_waits(peer_id)


def _should_leave_help_wait_mode(t: str) -> bool:
    """Команды меню — выходим из режима «ждём текст для админа»."""
    greetings = (
        'start', '/start', 'начать', 'привет', 'hi', 'hello',
        'меню', 'добро пожаловать',
    )
    if t in greetings:
        return True
    if t in ('магаз', 'магазин', 'shop') or 'магаз' in t:
        return True
    if t in ('профиль', 'мой профиль', 'profile') or 'профиль' in t:
        return True
    if t in ('вступить', 'вступление') or t.startswith('вступ'):
        return True
    if t in ('заявка', 'подать заявку', 'заявку') or 'заявк' in t:
        return True
    return False


def _notify_admin_help(from_id: int) -> bool:
    aid = getattr(settings, 'VK_BOT_ADMIN_VK_ID', '') or ''
    if not aid.isdigit():
        return False
    text = (
        f'Помощь в боте: пользователь https://vk.com/id{from_id}\n'
        'Открой диалог с ним или ответь здесь, если ВК позволяет.'
    )
    return _vk_send_message(int(aid), text, keyboard=None)


def _lot_buy_keyboard_vk(lot_id: int) -> dict:
    return {
        'one_time': False,
        'inline': True,
        'buttons': [[
            {
                'action': {
                    'type': 'text',
                    'label': 'Купить',
                    'payload': json.dumps({'cmd': 'buy', 'lot': lot_id}, separators=(',', ':')),
                },
            },
        ]],
    }


def _notify_admin_purchase_vk(
    from_id: int,
    peer_id: int,
    lot: ShopLot,
    buyer_balance_ok: int | None,
) -> bool:
    aid = getattr(settings, 'VK_BOT_ADMIN_VK_ID', '') or ''
    if not aid.isdigit():
        return False
    text = (
        f'Заявка на покупку: «{lot.title}» ({lot.price_points} ОК)\n'
        f'Пользователь https://vk.com/id{from_id}\n'
        f'peer_id: {peer_id}'
    )
    if buyer_balance_ok is not None:
        text += f'\nБаланс на момент заявки: {buyer_balance_ok} ОК'
    return _vk_send_message(int(aid), text, keyboard=None)


def _forward_support_text_to_vk_admin(from_id: int, peer_id: int, body: str) -> bool:
    aid = getattr(settings, 'VK_BOT_ADMIN_VK_ID', '') or ''
    if not aid.isdigit():
        return False
    head = (
        f'Текст в поддержку от https://vk.com/id{from_id}\n'
        f'peer_id диалога: {peer_id}\n\n'
    )
    return _vk_send_message(int(aid), head + (body or '')[:3500], keyboard=None)


def _send_shop_catalog(peer_id: int) -> None:
    lots = list(ShopLot.objects.filter(is_active=True).order_by('sort_order', 'id'))
    if not lots:
        _vk_send_message(
            peer_id,
            'Пока нет лотов в каталоге. Загляни позже.',
            _menu_keyboard(),
        )
        return
    _vk_send_message(peer_id, 'Каталог лотов (цены в ОК — очках клана):', None)
    for lot in lots:
        caption = f'{lot.title}\nЦена: {lot.price_points} ОК'
        att = None
        if lot.image:
            try:
                path = lot.image.path
            except (NotImplementedError, ValueError):
                path = ''
            if path:
                att = vk_upload_message_photo(peer_id, path)
            if not att:
                url = _public_media_url(lot)
                if url:
                    caption = f'{caption}\n{url}'
        _vk_send_message(peer_id, caption, _lot_buy_keyboard_vk(lot.pk), attachment=att)
    _vk_send_message(
        peer_id,
        'Нажми «Купить» под лотом — лидер получит заявку. Или договорись в беседе клана. Ниже — меню.',
        _menu_keyboard(),
    )


def _handle_message_text(
    peer_id: int,
    from_id: int,
    text: str,
    payload_raw: str | dict | None = None,
) -> None:
    u_block = ensure_vk_player(from_id)
    u_block = User.objects.select_related('profile').get(pk=u_block.pk)
    if u_block.role == User.Role.BANNED:
        _vk_send_message(
            peer_id,
            'Доступ к боту заблокирован администрацией клана.',
            None,
        )
        return

    if payload_raw is not None and payload_raw != '':
        try:
            if isinstance(payload_raw, dict):
                pl = payload_raw
            elif isinstance(payload_raw, str):
                pl = json.loads(payload_raw)
            else:
                pl = None
            if isinstance(pl, dict):
                cmd = pl.get('cmd')
                if cmd == 'buy':
                    _clear_vk_help_wait(peer_id)
                    lot_raw = pl.get('lot')
                    try:
                        lid = int(lot_raw)
                    except (TypeError, ValueError):
                        _vk_send_message(
                            peer_id,
                            'Не удалось обработать заявку. Открой каталог снова.',
                            _menu_keyboard(),
                        )
                        return
                    try:
                        lot = ShopLot.objects.get(pk=lid, is_active=True)
                    except ShopLot.DoesNotExist:
                        _vk_send_message(
                            peer_id,
                            'Лот не найден или снят с продажи.',
                            _menu_keyboard(),
                        )
                        return
                    site_user = ensure_vk_player(from_id)
                    balance = site_user.clan_points
                    if balance < lot.price_points:
                        _vk_send_message(
                            peer_id,
                            f'Недостаточно очков клана (ОК). У тебя: {balance}, нужно: {lot.price_points}.',
                            _menu_keyboard(),
                        )
                        return
                    admin_id = getattr(settings, 'VK_BOT_ADMIN_VK_ID', '') or ''
                    admin_ok = _notify_admin_purchase_vk(from_id, peer_id, lot, balance)
                    if admin_ok:
                        user_buy_reply = (
                            f'«{lot.title}», {lot.price_points} ОК — заявка принята (у тебя {balance} ОК). '
                            'Лидер получит уведомление. Если что-то срочное, напиши в «Помощь».'
                        )
                    elif not admin_id.isdigit():
                        user_buy_reply = (
                            f'«{lot.title}» — по балансу всё ок, но VK_BOT_ADMIN_VK_ID не задан. '
                            'Договорись о покупке в беседе клана.'
                        )
                    else:
                        user_buy_reply = (
                            f'«{lot.title}» — заявка учтена, но ВК не доставил уведомление лидеру. '
                            'Напиши в беседу клана или в «Помощь».'
                        )
                    _vk_send_message(peer_id, user_buy_reply, _menu_keyboard())
                    return
                if cmd == 'shop':
                    _clear_vk_help_wait(peer_id)
                    _send_shop_catalog(peer_id)
                    return
                if cmd == 'join':
                    _clear_vk_help_wait(peer_id)
                    _vk_send_message(peer_id, _join_text(), _join_keyboard())
                    return
                if cmd == 'apply':
                    _clear_vk_help_wait(peer_id)
                    _handle_clan_apply_vk(peer_id, from_id)
                    return
                if cmd == 'help':
                    _notify_admin_help(from_id)
                    cache.set(_vk_help_wait_key(peer_id), True, timeout=30 * 60)
                    _vk_send_message(peer_id, _help_text(), _menu_keyboard())
                    return
                if cmd == 'profile':
                    _send_profile_vk(peer_id, from_id)
                    return
                if cmd == 'profile_edit_nick':
                    _clear_vk_help_wait(peer_id)
                    _start_profile_edit_nick(peer_id)
                    return
                if cmd == 'profile_edit_uid':
                    _clear_vk_help_wait(peer_id)
                    uchk = ensure_vk_player(from_id)
                    uchk = type(uchk).objects.select_related('profile').get(pk=uchk.pk)
                    if not uchk.can_change_own_uid:
                        _vk_send_message(
                            peer_id,
                            'Игровой UID могут менять гость и лидер. Для смены UID обратись к лидеру клана.',
                            _profile_card_keyboard(uchk),
                        )
                        return
                    _start_profile_edit_uid(peer_id)
                    return
                if cmd == 'profile_edit_birth':
                    _clear_vk_help_wait(peer_id)
                    _start_profile_edit_birth(peer_id)
                    return
                if cmd == 'profile_edit_city':
                    _clear_vk_help_wait(peer_id)
                    _start_profile_edit_city(peer_id)
                    return
                if cmd == 'menu':
                    _clear_vk_help_wait(peer_id)
                    _vk_send_message(peer_id, _welcome_text(), _menu_keyboard())
                    return
        except (json.JSONDecodeError, TypeError, ValueError):
            pass

    t = _norm_text(text)
    help_key = _vk_help_wait_key(peer_id)
    raw = (text or '').strip()

    nick_k = _vk_profile_wait_nick_key(peer_id)
    if cache.get(nick_k):
        if _should_leave_profile_edit_mode(t):
            cache.delete(nick_k)
        else:
            u = ensure_vk_player(from_id)
            profile, _ = Profile.objects.get_or_create(user=u)
            profile.nickname = _apply_profile_field(raw, Profile._meta.get_field('nickname').max_length)
            profile.save(update_fields=['nickname'])
            cache.delete(nick_k)
            u = type(u).objects.select_related('profile').get(pk=u.pk)
            _vk_send_message(
                peer_id,
                'Никнейм обновлён.\n\n' + _profile_card_text(u),
                _profile_card_keyboard(u),
            )
            return

    uid_k = _vk_profile_wait_uid_key(peer_id)
    if cache.get(uid_k):
        if _should_leave_profile_edit_mode(t):
            cache.delete(uid_k)
        else:
            u = ensure_vk_player(from_id)
            u = type(u).objects.select_related('profile').get(pk=u.pk)
            if not u.can_change_own_uid:
                cache.delete(uid_k)
                _vk_send_message(
                    peer_id,
                    'Игровой UID для твоей роли меняет лидер. Обратись к лидеру клана.',
                    _profile_card_keyboard(u),
                )
                return
            profile, _ = Profile.objects.get_or_create(user=u)
            profile.uid = _apply_profile_field(raw, Profile._meta.get_field('uid').max_length)
            profile.save(update_fields=['uid'])
            cache.delete(uid_k)
            u = type(u).objects.select_related('profile').get(pk=u.pk)
            _vk_send_message(
                peer_id,
                'UID обновлён.\n\n' + _profile_card_text(u),
                _profile_card_keyboard(u),
            )
            return

    birth_k = _vk_profile_wait_birth_key(peer_id)
    if cache.get(birth_k):
        if _should_leave_profile_edit_mode(t):
            cache.delete(birth_k)
        else:
            kind, val = _parse_birth_date_input(raw)
            if kind == 'bad':
                _vk_send_message(
                    peer_id,
                    'Нужна дата в формате ДД.ММ.ГГГГ (возраст по ней — от 5 до 120 лет) или «-» чтобы сбросить.',
                    _profile_cancel_edit_keyboard(),
                )
                return
            u = ensure_vk_player(from_id)
            profile, _ = Profile.objects.get_or_create(user=u)
            profile.birth_date = None if kind == 'clear' else val
            profile.save(update_fields=['birth_date'])
            cache.delete(birth_k)
            u = type(u).objects.select_related('profile').get(pk=u.pk)
            _vk_send_message(
                peer_id,
                'Дата рождения обновлена.\n\n' + _profile_card_text(u),
                _profile_card_keyboard(u),
            )
            return

    city_k = _vk_profile_wait_city_key(peer_id)
    if cache.get(city_k):
        if _should_leave_profile_edit_mode(t):
            cache.delete(city_k)
        else:
            u = ensure_vk_player(from_id)
            profile, _ = Profile.objects.get_or_create(user=u)
            profile.city = _apply_profile_field(raw, Profile._meta.get_field('city').max_length)
            profile.save(update_fields=['city'])
            cache.delete(city_k)
            u = type(u).objects.select_related('profile').get(pk=u.pk)
            _vk_send_message(
                peer_id,
                'Город обновлён.\n\n' + _profile_card_text(u),
                _profile_card_keyboard(u),
            )
            return

    if cache.get(help_key):
        if t in ('помощь', 'help', '?') or t.startswith('помощ'):
            _vk_send_message(peer_id, _help_text(), _menu_keyboard())
            return
        if _should_leave_help_wait_mode(t):
            cache.delete(help_key)
        else:
            admin_id = getattr(settings, 'VK_BOT_ADMIN_VK_ID', '') or ''
            if not admin_id.isdigit():
                reply = (
                    'Сообщение не ушло: в настройках не задан VK_BOT_ADMIN_VK_ID. '
                    'Попроси лидера указать свой числовой id ВК в .env бота.'
                )
            elif _forward_support_text_to_vk_admin(from_id, peer_id, text):
                reply = (
                    'Передал администратору. Можешь написать ещё. Чтобы выйти в меню — отправь «меню» '
                    'или нажми «Магаз» / «Мой профиль» / «Вступить».'
                )
            else:
                reply = (
                    'ВК не доставил сообщение лидеру (ошибка API или диалог с сообществом не открыт). '
                    'Попробуй «Помощь» ещё раз или напиши в беседу клана.'
                )
            _vk_send_message(peer_id, reply, _menu_keyboard())
            return

    greetings = (
        'start', '/start', 'начать', 'привет', 'hi', 'hello',
        'меню', 'добро пожаловать',
    )
    if t in greetings:
        _clear_vk_help_wait(peer_id)
        _vk_send_message(peer_id, _welcome_text(), _menu_keyboard())
        return
    if t in ('магаз', 'магазин', 'shop') or 'магаз' in t:
        _clear_vk_help_wait(peer_id)
        _send_shop_catalog(peer_id)
        return
    if t in ('профиль', 'мой профиль', 'profile') or 'профиль' in t:
        _send_profile_vk(peer_id, from_id)
        return
    if t in ('вступить', 'вступление') or t.startswith('вступ'):
        _clear_vk_help_wait(peer_id)
        _vk_send_message(peer_id, _join_text(), _join_keyboard())
        return
    if t in ('заявка', 'подать заявку', 'заявку') or 'заявк' in t:
        _clear_vk_help_wait(peer_id)
        _handle_clan_apply_vk(peer_id, from_id)
        return
    if t in ('помощь', 'help', '?') or t.startswith('помощ'):
        _notify_admin_help(from_id)
        cache.set(help_key, True, timeout=30 * 60)
        _vk_send_message(peer_id, _help_text(), _menu_keyboard())
        return
    _vk_send_message(
        peer_id,
        'Не понял. Напиши «меню» или нажми кнопку ниже.',
        _menu_keyboard(),
    )


@csrf_exempt
@require_GET
def vk_ping(request):
    """Проверка, что /vk/ проксируется на Django (GET)."""
    return HttpResponse('vk_ok', content_type='text/plain; charset=utf-8')


@csrf_exempt
@require_GET
def vk_diag(request):
    """
    Диагностика доставки Callback API: если этот URL открывается в браузере, HTTP до backend доходит.
    ВК шлёт только POST на /vk/callback/ — при «бот молчит» смотри docker logs на строки POST /vk/callback/.
    """
    body = (
        'OVOSHI VK backend: HTTP до приложения доходит (GET /vk/diag/).\n\n'
        'Callback ВКонтакте должен указывать на этот же хост, путь:\n'
        '  https://ВАШ-ДОМЕН/vk/callback/\n'
        '(часто нужен HTTPS и прокси на порт backend, не только localhost:59722).\n\n'
        'Проверка: пока пишешь боту в ВК, выполни:\n'
        '  docker logs -f docker-backend-1\n'
        'Должны появляться строки вида: POST /vk/callback/ …\n'
        'Если их нет — ВК не достучался до этого сервера (URL в настройках сообщества, туннель, firewall, nginx).\n'
        'Если POST есть, но ответа в чат нет — смотри в логах VK messages.send / secret / DisallowedHost.\n'
    )
    return HttpResponse(body, content_type='text/plain; charset=utf-8')


def _vk_event_type(body: dict) -> str | None:
    t = body.get('type')
    if isinstance(t, str):
        return t.strip().lower()
    return t


def _vk_normalize_message_new_object(obj: dict) -> dict:
    """
    Поля сообщения обычно в object.message; в части версий/клиентов часть полей — в object.
    Пустой object.message + peer_id/from_id на уровне object иначе даёт молчаливый пропуск ответа.
    """
    raw = obj.get('message')
    msg: dict = dict(raw) if isinstance(raw, dict) else {}
    if isinstance(obj, dict):
        for k in ('peer_id', 'from_id', 'text', 'payload', 'out'):
            if msg.get(k) is None and k in obj:
                msg[k] = obj[k]
    return msg


@csrf_exempt
@require_POST
def vk_callback(request):
    secret = getattr(settings, 'VK_BOT_SECRET', '') or ''
    confirmation = getattr(settings, 'VK_BOT_CONFIRMATION', '') or ''

    try:
        # utf-8-sig снимает BOM — иначе json.loads падает → 400 → у ВК «Invalid response code»
        raw = request.body.decode('utf-8-sig').strip()
        body = json.loads(raw)
        if not isinstance(body, dict):
            raise json.JSONDecodeError('root must be object', raw, 0)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        logger.warning(
            'VK callback: невалидный JSON method=%s path=%s len=%s err=%s',
            request.method,
            request.path,
            len(request.body or b''),
            e,
        )
        return HttpResponseBadRequest('invalid json')

    event_type = _vk_event_type(body)

    logger.info(
        'VK callback: type=%s group_id=%s',
        event_type,
        body.get('group_id'),
    )

    body_secret = body.get('secret')
    if body_secret is not None and not isinstance(body_secret, str):
        body_secret = str(body_secret)
    body_secret = (body_secret or '').strip()

    if secret:
        if not body_secret:
            logger.error(
                'VK callback: в .env задан VK_BOT_SECRET, а ВК не прислал поле secret. '
                'В Управление сообществом → Настройки → Работа с API → Callback API '
                'должен быть тот же «Секретный ключ», что и в VK_BOT_SECRET. '
                'Если в сообществе секрет не включён — удалите или очистите VK_BOT_SECRET в .env и перезапустите backend.'
            )
            return HttpResponseForbidden('bad secret')
        if body_secret != secret:
            logger.error(
                'VK callback: secret не совпадает с VK_BOT_SECRET в .env — исправьте один из них и перезапустите backend.'
            )
            return HttpResponseForbidden('bad secret')

    if event_type == 'confirmation':
        if not confirmation:
            logger.error(
                'VK_BOT_CONFIRMATION не задан — в .env добавь строку из окна подтверждения ВК '
                '(например VK_BOT_CONFIRMATION=4df9061d) и пересоздай backend'
            )
            return HttpResponseBadRequest('confirmation not configured')
        # ВК ждёт ровно эту строку в теле ответа и HTTP 200 (без лишних символов / BOM).
        code = confirmation.strip()
        logger.info('VK callback: confirmation OK, len=%s', len(code))
        resp = HttpResponse(code, content_type='text/plain')
        resp['Cache-Control'] = 'no-store'
        return resp

    if event_type == 'message_new':
        try:
            logger.info('VK Callback: message_new')
            obj = body.get('object')
            if not isinstance(obj, dict):
                obj = {}
            msg = _vk_normalize_message_new_object(obj)
            text = (msg.get('text') or '').strip()
            peer_id = msg.get('peer_id')
            from_id = msg.get('from_id')
            payload_raw = msg.get('payload')

            if msg.get('out'):
                return HttpResponse('ok')

            if from_id is not None and from_id < 0:
                return HttpResponse('ok')

            if peer_id is None or from_id is None:
                logger.warning(
                    'VK message_new без peer_id/from_id: keys_obj=%s keys_msg=%s',
                    list(obj.keys()),
                    list(msg.keys()) if isinstance(msg, dict) else [],
                )
                return HttpResponse('ok')

            logger.info(
                'VK message_new peer_id=%s from_id=%s text_len=%s has_payload=%s',
                peer_id,
                from_id,
                len(text),
                bool(payload_raw),
            )
            fid = int(from_id)
            if fid > 0:
                ensure_vk_player(fid)
            _handle_message_text(int(peer_id), fid, text, payload_raw)
        except Exception:
            logger.exception('VK message_new handler failed')
        return HttpResponse('ok')

    if event_type == 'message_allow':
        obj = body.get('object') or {}
        uid = obj.get('user_id')
        if uid:
            try:
                v = int(uid)
                if v > 0:
                    ensure_vk_player(v)
            except (TypeError, ValueError):
                pass
            _vk_send_message(int(uid), _welcome_text(), _menu_keyboard())
        return HttpResponse('ok')

    return HttpResponse('ok')
