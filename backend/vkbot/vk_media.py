"""Загрузка фото в ВК для вложения в messages.send."""
import logging
from pathlib import Path

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

VK_API = 'https://api.vk.com/method'


def vk_upload_message_photo(peer_id: int, file_path: str) -> str | None:
    """
    Возвращает строку вложения вида photo{owner_id}_{id} или None.
    peer_id — диалог с пользователем (тот же, что в messages.send).
    """
    token = getattr(settings, 'VK_BOT_GROUP_TOKEN', '') or ''
    if not token or not file_path:
        return None
    path = Path(file_path)
    if not path.is_file():
        return None
    try:
        r = requests.get(
            f'{VK_API}/photos.getMessagesUploadServer',
            params={'access_token': token, 'v': '5.199', 'peer_id': peer_id},
            timeout=15,
        )
        data = r.json()
        if 'error' in data:
            logger.warning('photos.getMessagesUploadServer: %s', data['error'])
            return None
        upload_url = data['response']['upload_url']
        with path.open('rb') as f:
            up = requests.post(upload_url, files={'photo': f}, timeout=60)
        up_json = up.json()
        if up_json.get('photo') == '[]' or 'server' not in up_json:
            logger.warning('VK photo upload failed: %s', up_json)
            return None
        save = requests.get(
            f'{VK_API}/photos.saveMessagesPhoto',
            params={
                'access_token': token,
                'v': '5.199',
                'photo': up_json['photo'],
                'server': up_json['server'],
                'hash': up_json['hash'],
            },
            timeout=15,
        )
        sj = save.json()
        if 'error' in sj or not sj.get('response'):
            logger.warning('photos.saveMessagesPhoto: %s', sj)
            return None
        ph = sj['response'][0]
        return f"photo{ph['owner_id']}_{ph['id']}"
    except (OSError, KeyError, requests.RequestException, ValueError, TypeError) as e:
        logger.warning('vk_upload_message_photo: %s', e)
        return None
