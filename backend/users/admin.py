from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import ClanApplication, ClanPointsEntry, Profile, User


class ProfileVkFilter(admin.SimpleListFilter):
    title = 'Бот ВК'
    parameter_name = 'profile_vk_bot'

    def lookups(self, request, model_admin):
        return (
            ('yes', 'С id ВК'),
            ('no', 'Без id ВК'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(vk_user_id__isnull=False)
        if self.value() == 'no':
            return queryset.filter(vk_user_id__isnull=True)
        return queryset


class VkBotUsersFilter(admin.SimpleListFilter):
    title = 'Бот ВК'
    parameter_name = 'vk_bot'

    def lookups(self, request, model_admin):
        return (
            ('yes', 'С id ВК в профиле'),
            ('no', 'Без id ВК'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(profile__vk_user_id__isnull=False)
        if self.value() == 'no':
            return queryset.filter(profile__vk_user_id__isnull=True)
        return queryset


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        'email',
        'username',
        'role',
        'clan_points',
        'vk_user_id_display',
        # 'karma',
        'uid_confirmed',
        'is_staff',
    )
    list_filter = ('role', 'is_staff', VkBotUsersFilter)
    list_select_related = ('profile',)
    search_fields = ('email', 'username', 'profile__nickname', 'profile__vk_user_id')

    @admin.display(description='VK id')
    def vk_user_id_display(self, obj):
        p = getattr(obj, 'profile', None)
        if p and p.vk_user_id:
            return p.vk_user_id
        return '—'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('profile')

    fieldsets = BaseUserAdmin.fieldsets + (
        (None, {'fields': ('role', 'clan_points', 'uid_confirmed')}),  # karma временно
        (
            'Исключение / бан',
            {
                'fields': (
                    'kicked_at',
                    'kick_reason',
                    'kicked_by',
                    'banned_at',
                    'ban_reason',
                    'banned_by',
                ),
            },
        ),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        (None, {'fields': ('email', 'role', 'clan_points', 'uid_confirmed')}),  # karma временно
    )


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'nickname',
        'uid',
        'clan_points_display',
        'birth_date',
        'age_years_display',
        'city',
        'vk_user_id',
    )
    list_filter = (ProfileVkFilter,)
    search_fields = ('nickname', 'uid', 'city', 'user__email', 'vk_user_id')
    raw_id_fields = ('user',)

    @admin.display(description='ОК', ordering='user__clan_points')
    def clan_points_display(self, obj):
        return obj.user.clan_points

    @admin.display(description='Лет')
    def age_years_display(self, obj):
        return obj.age_years if obj.age_years is not None else '—'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')


@admin.register(ClanPointsEntry)
class ClanPointsEntryAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'amount', 'comment_short', 'created_by', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('comment', 'user__email', 'created_by__email')
    raw_id_fields = ('user', 'created_by')
    readonly_fields = ('created_at',)

    @admin.display(description='Комментарий')
    def comment_short(self, obj):
        t = (obj.comment or '')[:80]
        return t + ('…' if len(obj.comment or '') > 80 else '')


@admin.register(ClanApplication)
class ClanApplicationAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'created_at',
        'resolved_at',
        'status',
        'status_comment',
        'user',
        'nickname',
        'uid',
        'birth_date',
        'age_years_display',
        'city',
        'vk_user_id',
        'clan_points_snapshot',
    )
    list_filter = ('status', 'created_at')
    search_fields = ('user__email', 'nickname', 'uid', 'city', 'vk_user_id')
    readonly_fields = (
        'created_at',
        'resolved_at',
        'nickname',
        'uid',
        'birth_date',
        'age_years_display',
        'city',
        'vk_user_id',
        'clan_points_snapshot',
    )
    raw_id_fields = ('user',)
    date_hierarchy = 'created_at'

    fieldsets = (
        (None, {'fields': ('user', 'status', 'status_comment', 'created_at', 'resolved_at')}),
        (
            'Данные на момент заявки',
            {
                'fields': (
                    'nickname',
                    'uid',
                    'birth_date',
                    'age_years_display',
                    'city',
                    'vk_user_id',
                    'clan_points_snapshot',
                ),
            },
        ),
    )

    @admin.display(description='Лет (сейчас)')
    def age_years_display(self, obj):
        return obj.age_years if obj.age_years is not None else '—'

    def has_add_permission(self, request):
        return False

    def get_readonly_fields(self, request, obj=None):
        ro = list(super().get_readonly_fields(request, obj))
        if obj:
            ro.append('user')
        return tuple(ro)
