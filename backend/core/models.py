from django.db import models


class SiteSettings(models.Model):
    """Singleton: настройки сайта (ссылки на соцсети и т.д.)."""

    vk_public_url = models.URLField(
        'Ссылка на паблик клана ВКонтакте',
        max_length=500,
        blank=True,
    )
    recruiter_url = models.URLField(
        'Ссылка на наборщика',
        max_length=500,
        blank=True,
        help_text='Используется в боте ВК в тексте «Вступить» (напиши наборщику). Если пусто — из VK_BOT_RECRUITER_URL в .env.',
    )

    class Meta:
        verbose_name = 'Настройки сайта'
        verbose_name_plural = 'Настройки сайта'

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class ShopLot(models.Model):
    """Лот магазина клана (ВК-бот и сайт). Цена в очках клана (ОК)."""

    title = models.CharField('Название', max_length=200)
    image = models.ImageField('Картинка', upload_to='shop/', blank=True, null=True)
    price_points = models.PositiveIntegerField('Цена, ОК')
    sort_order = models.PositiveSmallIntegerField('Порядок', default=0)
    is_active = models.BooleanField('Активен', default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('sort_order', 'id')
        verbose_name = 'Лот магазина'
        verbose_name_plural = 'Лоты магазина'

    def __str__(self):
        return f'{self.title} — {self.price_points} ОК'
