"""
Django settings for OVOSHI clan site.
"""
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _env_plain(value: str) -> str:
    """Убирает пробелы и внешние кавычки (частая ошибка в .env: VK_BOT_ADMIN_VK_ID=\"123\")."""
    v = (value or '').strip()
    if len(v) >= 2 and v[0] in '"\'' and v[0] == v[-1]:
        v = v[1:-1].strip()
    return v


# Для makemigrations не нужен PostgreSQL — используем SQLite, чтобы не висеть без запущенной БД
MAKEMIGRATIONS = 'makemigrations' in sys.argv

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'dev-secret-change-in-production')

DEBUG = os.environ.get('DEBUG', '1') == '1'

ALLOWED_HOSTS = [
    h.strip()
    for h in os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')
    if h.strip()
]
# Явно в compose/.env: разрешить любой Host (Callback ВК за nginx с публичным доменом).
# Не привязываем к DEBUG: иначе при DEBUG=0 в .env снова 400 DisallowedHost → «Invalid response code» в ВК.
if os.environ.get('DJANGO_ALLOW_ALL_HOSTS', '').lower() in ('1', 'true', 'yes'):
    ALLOWED_HOSTS = ['*']

CSRF_TRUSTED_ORIGINS = os.environ.get('CSRF_TRUSTED_ORIGINS', 'http://localhost:3000,http://127.0.0.1:3000').split(',')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',

    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',

    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.vk',

    'users',
    'core',
    'vkbot',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

if MAKEMIGRATIONS:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': ':memory:',
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('POSTGRES_DB', 'ovoshi'),
            'USER': os.environ.get('POSTGRES_USER', 'ovoshi'),
            'PASSWORD': os.environ.get('POSTGRES_PASSWORD', 'ovoshi'),
            'HOST': os.environ.get('POSTGRES_HOST', 'localhost'),
            'PORT': os.environ.get('POSTGRES_PORT', '5432'),
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'ru-ru'
TIME_ZONE = 'Europe/Moscow'
USE_I18N = True
USE_TZ = True

# С ведущим / — иначе относительные URL из /admin/ уходят в /admin/static/… и CSS «пропадает».
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage',
    },
}

MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Кэш (режим «помощь» и т.д. у бота ВК). При нескольких воркерах gunicorn лучше Redis.
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'ovoshi-state',
    }
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = 'users.User'

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

SITE_ID = 1

# django-allauth: только соц. вход
ACCOUNT_EMAIL_VERIFICATION = 'optional'
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_QUERY_EMAIL = True
SOCIALACCOUNT_STORE_TOKENS = False
ACCOUNT_LOGIN_METHODS = {'email'}
ACCOUNT_SIGNUP_FIELDS = ['email*', 'username*']
# Редирект после OAuth — на фронт (задать в env, например http://localhost:3000)
FRONTEND_URL = os.environ.get('FRONTEND_URL', 'http://localhost:3000')
LOGIN_REDIRECT_URL = FRONTEND_URL + '/'
# После выхода — страница входа SPA (django-allauth и django.contrib.auth)
_logout_to = FRONTEND_URL.rstrip('/') + '/login'
LOGOUT_REDIRECT_URL = _logout_to
ACCOUNT_LOGOUT_REDIRECT_URL = _logout_to
# За NPM/HTTPS: redirect_uri для VK ID должен быть https://… (иначе ВК отклонит).
if FRONTEND_URL.strip().lower().startswith('https://'):
    ACCOUNT_DEFAULT_HTTP_PROTOCOL = 'https'
# Цепочка X-Forwarded-* от nginx/NPM (опционально).
if os.environ.get('DJANGO_BEHIND_HTTPS_PROXY', '').lower() in ('1', 'true', 'yes'):
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    USE_X_FORWARDED_HOST = True

SOCIALACCOUNT_ADAPTER = 'users.adapters.OvoshiSocialAccountAdapter'

# CORS for React frontend
CORS_ALLOWED_ORIGINS = os.environ.get('CORS_ORIGINS', 'http://localhost:3000,http://127.0.0.1:3000').split(',')
CORS_ALLOW_CREDENTIALS = True

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'users.permissions.IsAuthenticatedNotGuest',
    ],
}

# OAuth: только VK ID (вход через PKCE + /api/auth/vkid/complete/, см. users.vkid_views).
SOCIALACCOUNT_PROVIDERS = {
    'vk': {
        'APP': {
            'client_id': os.environ.get('VK_CLIENT_ID', ''),
            'secret': os.environ.get('VK_CLIENT_SECRET', ''),
        },
        'SCOPE': ['email'],
    },
}

# VK Callback API (бот сообщества): https://dev.vk.com/ru/api/callback/getting-started
VK_BOT_GROUP_TOKEN = os.environ.get('VK_BOT_GROUP_TOKEN', '').strip()
VK_BOT_SECRET = _env_plain(os.environ.get('VK_BOT_SECRET', ''))
VK_BOT_CONFIRMATION = _env_plain(os.environ.get('VK_BOT_CONFIRMATION', ''))
# Ссылка «Вступить» (по умолчанию — страница входа на сайте)
_join = os.environ.get('VK_BOT_JOIN_URL', '').strip()
VK_BOT_JOIN_URL = _join if _join else (FRONTEND_URL.rstrip('/') + '/login')
# Ссылка «Написать лидеру»: https://vk.me/id123 или https://vk.com/im?sel=...
VK_BOT_LEADER_LINK = os.environ.get('VK_BOT_LEADER_LINK', '').strip()
# Пустая строка в .env перебивает default у get() — как у VK_BOT_JOIN_URL.
_rules = os.environ.get('VK_BOT_RULES_URL', '').strip()
VK_BOT_RULES_URL = _rules or 'https://vk.com/@ovoshi_pubg-pravila-i-plushki-klana-pon'
# Fallback, если в админке сайта не задана «Ссылка на наборщика» (SiteSettings.recruiter_url)
_rec = os.environ.get('VK_BOT_RECRUITER_URL', '').strip()
VK_BOT_RECRUITER_URL = _rec or 'https://vk.com/danchachernov'
_vk_admin = _env_plain(os.environ.get('VK_BOT_ADMIN_VK_ID', ''))
VK_BOT_ADMIN_VK_ID = _vk_admin if _vk_admin.isdigit() else ''
BACKEND_PUBLIC_URL = os.environ.get('BACKEND_PUBLIC_URL', '').strip()

# Логи бота ВК в консоль (docker logs)
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {'format': '%(levelname)s %(name)s %(message)s'},
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'loggers': {
        'vkbot': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        # ВК шлёт callback на публичный Host — без ALLOW_ALL_HOSTS / правки ALLOWED_HOSTS будет 400 без vkbot-логов
        'django.security.DisallowedHost': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}
