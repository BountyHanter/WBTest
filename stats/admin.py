from django.contrib import admin

from stats.models import Image, Test, WBToken


class ImageInline(admin.TabularInline):
    model = Image
    extra = 0
    fields = (
        "id",
        "position",
        "status",
        "total_views",
        "total_clicks",
        "rounds_passed",
        "wins_count",
    )
    readonly_fields = fields
    ordering = ("position",)

@admin.register(Test)
class TestAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "user",
        "name",
        "status",
        "current_image",
        "created_at",
    )

    list_filter = (
        "status",
        "created_at",
    )

    search_fields = (
        "name",
        "campaign_id",
        "product_id",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
        "started_at",

        "error_log",
    )

    fieldsets = (
        ("Основное", {
            "fields": (
                "user",
                "name",
                "status",
                "wb_token",
            )
        }),

        ("Идентификаторы", {
            "fields": (
                "campaign_id",
                "product_id",
            )
        }),

        ("Настройки теста", {
            "fields": (
                "impressions_per_cycle",
                "max_impressions_per_image",
                "time_per_cycle",
            )
        }),

        ("Состояние", {
            "fields": (
                "current_image",
                "set_pause",
                "started_at",
                "finished_at",
            )
        }),

        ("Ошибки", {
            "fields": (
                "error_counts",
                "last_error",
                "error_log",
            )
        }),

        ("Системное", {
            "fields": (
                "created_at",
                "updated_at",
            )
        }),
    )

    inlines = [ImageInline]

    ordering = ("-created_at",)


@admin.register(Image)
class ImageAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "test",
        "position",
        "status",
        "total_views",
        "total_clicks",
        "rounds_passed",
        "wins_count",
    )

    list_filter = (
        "status",
        "test",
    )

    search_fields = (
        "test__name",
    )

    ordering = ("test", "position")


@admin.register(WBToken)
class WBTokenAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "user",
        "created_at",
    )

    search_fields = (
        "user__email",
        "token",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    ordering = ("-created_at",)

    fieldsets = (
        ("Основное", {
            "fields": (
                "user",
                "token",
            )
        }),

        ("Системное", {
            "fields": (
                "created_at",
                "updated_at",
            )
        }),
    )