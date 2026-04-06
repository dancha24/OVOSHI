"""
Исходящие сообщения ВК (без views) — можно вызывать из users и др. без циклических импортов.
"""
import json
import logging
import random

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

VK_API = 'https://api.vk.com/method'


def vk_send_message(
    peer_id: int,
    text: str,
    keyboard: dict | None = None,
    attachment: str | None = None,
) -> bool:
    """
    Отправка от имени сообщества. При ошибке API (клавиатура, вложение, flood)
    один раз повторяет только текст — иначе пользователь не видит ответа.
    """
    token = getattr(settings, 'VK_BOT_GROUP_TOKEN', '') or ''
    if not token:
        logger.error(
            'VK_BOT_GROUP_TOKEN не задан — callback от ВК обработан, но ответ в чат не уйдёт. '
            'Задайте ключ сообщества в .env (токен из Управление → Настройки → Работа с API → Ключи доступа).'
        )
        return False

    def _post(extra: dict) -> dict:
        params = {
            'access_token': token,
            'v': '5.199',
            'random_id': random.randint(1, 2**31 - 1),
            'peer_id': peer_id,
            'message': text,
            **extra,
        }
        try:
            r = requests.post(f'{VK_API}/messages.send', data=params, timeout=30)
        except requests.RequestException as e:
            logger.error('VK messages.send: сеть peer_id=%s err=%s', peer_id, e)
            return {'error': {'error_code': -1, 'error_msg': str(e)}}
        try:
            return r.json()
        except json.JSONDecodeError:
            logger.error(
                'VK messages.send: не JSON в ответе peer_id=%s status=%s body=%r',
                peer_id,
                r.status_code,
                (r.text or '')[:500],
            )
            return {'error': {'error_code': -2, 'error_msg': 'invalid json'}}

    extra: dict = {}
    if keyboard:
        extra['keyboard'] = json.dumps(keyboard, ensure_ascii=False)
    if attachment:
        extra['attachment'] = attachment

    data = _post(extra)
    if 'error' in data and (keyboard or attachment):
        logger.warning(
            'VK messages.send (с клавиатурой/вложением) не прошло, повтор только текст: %s',
            data.get('error'),
        )
        data = _post({})

    if 'error' in data:
        err = data['error']
        code = err.get('error_code')
        hints = {
            5: 'неверный или просроченный access_token — перевыпустите ключ сообщества в ВК.',
            6: 'слишком много запросов к API — подождите; при частых сообщениях ВК временно режет ответы.',
            9: 'flood control ВК — слишком частые ответы бота; увеличьте паузу между сообщениями или дождитесь снятия лимита.',
            901: 'пользователь не разрешил сообщения от сообщества — откройте чат с сообществом и нажмите «Начать» / разрешите уведомления.',
            902: 'нельзя писать этому peer_id (удалённый диалог и т.п.).',
            947: 'ошибка клавиатуры — бот повторит отправку без клавиатуры (см. лог выше).',
        }
        hint = hints.get(code, '')
        if hint:
            hint = ' ' + hint
        logger.error(
            'VK messages.send error code=%s peer_id=%s: %s%s',
            code,
            peer_id,
            err,
            hint,
        )
        return False
    mid = data.get('response')
    logger.info('VK messages.send OK peer_id=%s message_id=%s', peer_id, mid)
    return True
