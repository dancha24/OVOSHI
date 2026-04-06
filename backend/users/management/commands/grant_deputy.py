"""Выдать роль «Заместитель» — кабинет /leader/*, заявки, участники, журнал ОК; без настроек сайта."""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

User = get_user_model()


class Command(BaseCommand):
    help = 'Назначить роль «Заместитель» по email (ОК, участники, заявки; настройки сайта — только у лидера).'

    def add_arguments(self, parser):
        parser.add_argument('email', type=str, help='Email учётной записи (как в БД)')

    def handle(self, *args, **options):
        email = (options['email'] or '').strip().lower()
        if not email:
            raise CommandError('Укажите email.')
        user = User.objects.filter(email__iexact=email).first()
        if not user:
            raise CommandError(f'Пользователь с email {email!r} не найден.')
        user.role = User.Role.DEPUTY
        user.save(update_fields=['role'])
        self.stdout.write(self.style.SUCCESS(f'{email} — роль «Заместитель».'))
