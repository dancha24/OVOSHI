"""Выдать пользователю роль «Лидер» по email (кабинет /leader/*, заявки, участники)."""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

User = get_user_model()


class Command(BaseCommand):
    help = 'Назначить роль «Лидер» пользователю по email (доступ к заявкам и настройкам на сайте).'

    def add_arguments(self, parser):
        parser.add_argument('email', type=str, help='Email учётной записи (как в БД)')

    def handle(self, *args, **options):
        email = (options['email'] or '').strip().lower()
        if not email:
            raise CommandError('Укажите email.')
        user = User.objects.filter(email__iexact=email).first()
        if not user:
            raise CommandError(f'Пользователь с email {email!r} не найден.')
        user.role = User.Role.LEADER
        user.save(update_fields=['role'])
        self.stdout.write(self.style.SUCCESS(f'{email} — роль «Лидер».'))
