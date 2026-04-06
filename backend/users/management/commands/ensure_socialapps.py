"""Создать/обновить SocialApp из SOCIALACCOUNT_PROVIDERS (.env), привязать к Site."""

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.management.base import BaseCommand

from allauth.socialaccount.models import SocialApp


class Command(BaseCommand):
    help = 'Синхронизировать VK (и при необходимости др.) SocialApp с ключами из settings / .env.'

    def handle(self, *args, **options):
        site = Site.objects.get(pk=settings.SITE_ID)
        self._sync_vk(site)

    def _sync_vk(self, site):
        vk = settings.SOCIALACCOUNT_PROVIDERS.get('vk', {}).get('APP', {})
        cid = (vk.get('client_id') or '').strip()
        secret = (vk.get('secret') or '').strip()
        if not cid:
            self.stdout.write('VK_CLIENT_ID пуст — приложение VK в админке не трогаем.')
            return
        app = SocialApp.objects.filter(provider='vk').order_by('id').first()
        if app:
            app.name = 'VK'
            app.client_id = cid
            app.secret = secret
            app.save()
        else:
            app = SocialApp.objects.create(
                provider='vk',
                name='VK',
                client_id=cid,
                secret=secret,
            )
        if not app.sites.filter(pk=site.pk).exists():
            app.sites.add(site)
        self.stdout.write(self.style.SUCCESS('Приложение «VK» для allauth обновлено и привязано к сайту.'))
