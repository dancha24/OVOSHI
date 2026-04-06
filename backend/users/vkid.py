"""Обмен кода VK ID (id.vk.ru) на токен и запрос профиля — как в Beats (lib/vkid.ts)."""
import os
from typing import Any

import requests


def _client_id() -> str:
    cid = (os.environ.get('VK_CLIENT_ID') or '').strip()
    if not cid:
        raise ValueError('VK_CLIENT_ID is not configured')
    return cid


def exchange_vk_id_code(
    *,
    code: str,
    device_id: str,
    code_verifier: str,
    state: str,
    redirect_uri: str,
) -> Any:
    body = {
        'grant_type': 'authorization_code',
        'client_id': _client_id(),
        'code': code,
        'device_id': device_id,
        'code_verifier': code_verifier,
        'state': state,
        'redirect_uri': redirect_uri,
    }
    r = requests.post(
        'https://id.vk.ru/oauth2/auth',
        data=body,
        headers={'content-type': 'application/x-www-form-urlencoded'},
        timeout=20,
    )
    return r.json()


def fetch_vk_id_user_info(access_token: str) -> Any:
    body = {
        'client_id': _client_id(),
        'access_token': access_token,
    }
    r = requests.post(
        'https://id.vk.ru/oauth2/user_info',
        data=body,
        headers={'content-type': 'application/x-www-form-urlencoded'},
        timeout=20,
    )
    return r.json()
