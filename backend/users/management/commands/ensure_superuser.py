"""Создать первого суперпользователя из env, если в БД ещё нет ни одного."""

import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

User = get_user_model()


class Command(BaseCommand):
    help = (
        'Если нет ни одного суперпользователя: создать из OVOSHI_ADMIN_EMAIL и '
        'OVOSHI_ADMIN_PASSWORD (опционально OVOSHI_ADMIN_USERNAME). '
        'Если пользователь с таким email уже есть — выдать staff/superuser и обновить пароль.'
    )

    def handle(self, *args, **options):
        if User.objects.filter(is_superuser=True).exists():
            self.stdout.write(self.style.SUCCESS('Суперпользователь уже есть — пропуск.'))
            return

        email = (os.environ.get('OVOSHI_ADMIN_EMAIL') or '').strip()
        password = os.environ.get('OVOSHI_ADMIN_PASSWORD') or ''
        username = (os.environ.get('OVOSHI_ADMIN_USERNAME') or '').strip()

        if not email or not password:
            self.stdout.write(
                'Нет суперпользователя. Задайте OVOSHI_ADMIN_EMAIL и OVOSHI_ADMIN_PASSWORD '
                'в .env или выполните: python manage.py createsuperuser'
            )
            return

        if not username:
            username = email.split('@')[0][:150]

        base = username
        n = 0
        while User.objects.filter(username=username).exclude(email=email).exists():
            n += 1
            username = f'{base}{n}'[:150]

        existing = User.objects.filter(email=email).first()
        if existing:
            existing.is_staff = True
            existing.is_superuser = True
            existing.set_password(password)
            existing.save()
            self.stdout.write(self.style.SUCCESS(f'Пользователь {email} повышен до суперпользователя.'))
            return

        User.objects.create_superuser(email=email, username=username, password=password)
        self.stdout.write(self.style.SUCCESS(f'Создан суперпользователь {email}'))
