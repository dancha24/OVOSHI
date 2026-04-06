from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


def age_years_from_birth(birth_date):
    """Полных лет на сегодня."""
    if not birth_date:
        return None
    today = timezone.now().date()
    n = today.year - birth_date.year
    if (today.month, today.day) < (birth_date.month, birth_date.day):
        n -= 1
    return n


class User(AbstractUser):
    """Custom user with role. Email as main identifier for OAuth."""

    class Role(models.TextChoices):
        GUEST = 'guest', 'Гость'
        PLAYER = 'player', 'Игрок'
        ELITE = 'elite', 'Элита'
        DEPUTY = 'deputy', 'Заместитель'
        LEADER = 'leader', 'Лидер'
        ASSOCIATE = 'associate', 'Соучастник'
        BANNED = 'banned', 'Забанен'

    email = models.EmailField('email', unique=True)
    role = models.CharField(
        max_length=12,
        choices=Role.choices,
        default=Role.GUEST,
    )
    clan_points = models.IntegerField('Очки клана', default=0)
    karma = models.IntegerField('Карма', default=0)
    uid_confirmed = models.BooleanField('UID подтверждён', default=False)

    kicked_at = models.DateTimeField('Исключён из клана', null=True, blank=True)
    kick_reason = models.TextField('Причина исключения', blank=True, default='')
    kicked_by = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='clan_kicks_executed',
        verbose_name='Исключил',
    )
    banned_at = models.DateTimeField('Забанен', null=True, blank=True)
    ban_reason = models.TextField('Причина бана', blank=True, default='')
    banned_by = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='clan_bans_executed',
        verbose_name='Забанил',
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.email

    @property
    def is_leader(self):
        return self.role == self.Role.LEADER

    @property
    def can_manage_participants(self):
        if self.is_superuser:
            return True
        return self.role in (self.Role.LEADER, self.Role.DEPUTY)

    @property
    def can_manage_clan_points(self):
        """Начисление и списание ОК (журнал) — лидер, заместитель, суперпользователь."""
        if self.is_superuser:
            return True
        return self.role in (self.Role.LEADER, self.Role.DEPUTY)

    @property
    def can_manage_settings(self):
        if self.is_superuser:
            return True
        return self.role == self.Role.LEADER

    @property
    def can_access_leader_cabinet(self):
        """Кабинет /leader/* — лидер, заместитель или суперпользователь (настройки сайта только у лидера)."""
        return bool(
            self.is_superuser or self.role in (self.Role.LEADER, self.Role.DEPUTY)
        )

    @property
    def can_change_own_uid(self):
        """Смена игрового UID самостоятельно: гость, лидер, staff/superuser. Игрок/элита/зам — только через лидера."""
        if self.is_superuser or self.is_staff:
            return True
        return self.role in (self.Role.GUEST, self.Role.LEADER)


class Profile(models.Model):
    """Extended profile: nickname, UID, дата рождения (возраст вычисляется), город, avatar."""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    nickname = models.CharField('Никнейм', max_length=50, blank=True)
    uid = models.CharField('UID', max_length=50, blank=True)
    birth_date = models.DateField('Дата рождения', null=True, blank=True)
    city = models.CharField('Город', max_length=120, blank=True)
    vk_user_id = models.BigIntegerField(
        'ID ВКонтакте',
        null=True,
        blank=True,
        unique=True,
        help_text='Числовой id как в vk.com/id… — при входе через ВК подставляется автоматически.',
    )
    avatar = models.ImageField('Аватар', upload_to='avatars/', blank=True, null=True)

    class Meta:
        verbose_name = 'Профиль'
        verbose_name_plural = 'Профили'

    def __str__(self):
        return self.nickname or self.user.email

    @property
    def age_years(self):
        return age_years_from_birth(self.birth_date)


class ClanApplication(models.Model):
    """Заявка в клан из бота ВК (снимок полей на момент отправки)."""

    class Status(models.TextChoices):
        PENDING = 'pending', 'На рассмотрении'
        APPROVED = 'approved', 'Принята'
        REJECTED = 'rejected', 'Отклонена'

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='clan_applications',
        verbose_name='Пользователь',
    )
    created_at = models.DateTimeField('Создана', auto_now_add=True)
    status = models.CharField(
        'Статус',
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    nickname = models.CharField('Никнейм', max_length=100, blank=True)
    uid = models.CharField('UID', max_length=50, blank=True)
    birth_date = models.DateField('Дата рождения', null=True, blank=True)
    city = models.CharField('Город', max_length=120, blank=True)
    vk_user_id = models.BigIntegerField('ID ВКонтакте', null=True, blank=True)
    clan_points_snapshot = models.IntegerField('ОК на момент заявки', default=0)
    status_comment = models.TextField(
        'Комментарий',
        blank=True,
        default='',
        help_text='Показывается пользователю в боте. Для новой заявки задаётся «На рассмотрении»; при принятии/отклонении лидер обязан указать свой комментарий.',
    )
    resolved_at = models.DateTimeField(
        'Дата и время решения',
        null=True,
        blank=True,
        help_text='Заполняется при переводе заявки в «Принята» или «Отклонена».',
    )

    class Meta:
        verbose_name = 'Заявка в клан'
        verbose_name_plural = 'Заявки в клан'
        ordering = ['-created_at']

    def __str__(self):
        return f'Заявка #{self.pk} от {self.user.email} ({self.get_status_display()})'

    @property
    def age_years(self):
        return age_years_from_birth(self.birth_date)


class ClanPointsEntry(models.Model):
    """Строка журнала очков клана (ОК): сумма может быть отрицательной (списание)."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='clan_points_entries',
        verbose_name='Игрок',
    )
    amount = models.IntegerField('Сумма ОК')
    comment = models.CharField('Комментарий', max_length=500, blank=True, default='')
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='clan_points_entries_created',
        verbose_name='Кем начислено / списано',
    )
    created_at = models.DateTimeField('Когда', auto_now_add=True)

    class Meta:
        verbose_name = 'Запись журнала ОК'
        verbose_name_plural = 'Журнал ОК'
        ordering = ['-created_at']

    def __str__(self):
        return f'ОК #{self.pk} user={self.user_id} {self.amount:+d}'
