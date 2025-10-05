from django.contrib import admin
from .models import Product, Category

from django.contrib import admin
from django.utils.html import format_html
from .models import *

from django.contrib import admin
from .models import MainCategory


@admin.register(MainCategory)
class MainCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "icon", "preview_icon")   # колонки в списке
    search_fields = ("name", "slug")                         # поиск
    prepopulated_fields = {"slug": ("name",)}                # автозаполнение slug по name
    list_editable = ("icon",)                                # можно менять иконку прямо в списке
    ordering = ("name",)                                     # сортировка по имени

    # маленький рендер иконки для удобства
    def preview_icon(self, obj):
        if obj.icon:
            return f'<i class="{obj.icon}"></i>'
        return "—"
    preview_icon.short_description = "Иконка"
    preview_icon.allow_tags = True

@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    list_display = ('name', 'address', 'phone', 'work_hours')
    search_fields = ('name', 'address', 'phone')
    list_filter = ('name',)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        'name', 
        'category', 
        'get_product_type_display',
        'price', 
        "skidka",
        'available',
        'display_image'
    )
    list_filter = (
        'product_type',
        'category',
        'available',
        'created'
    )
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    fieldsets = (
        (None, {
            'fields': (
                'product_type',
                'category',
                'name',
                'slug',
                'image',
                'description',
                'price',
                'skidka',
                'available',
                'featured'
            )
        }),
        ('Для цветов', {
            'fields': (
                'flowers_included',
                'height_cm'
            ),
            'classes': ('collapse',)
        }),
        ('Для игрушек', {
            'fields': (
                'age_limit',
                'material'
            ),
            'classes': ('collapse',)
        }),
        ('Для десертов', {
            'fields': (
                'weight_grams',
                'ingredients'
            ),
            'classes': ('collapse',)
        }),
    )
    
    def display_image(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="50" />', obj.image.url)
        return "Нет изображения"
    display_image.short_description = "Изображение"


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('product', 'name', 'rating', 'approved', 'created')
    list_filter = ('approved', 'rating', 'created')
    search_fields = ('product__name', 'name', 'email', 'text')
    list_editable = ('approved',)
    actions = ['approve_reviews']
    
    def approve_reviews(self, request, queryset):
        queryset.update(approved=True)
    approve_reviews.short_description = "Одобрить выбранные отзывы"


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('get_cost',)
    
    def get_cost(self, obj):
        return obj.get_cost()
    get_cost.short_description = "Стоимость"


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'full_name', 'phone', 
        'status', 'payment_method', 'total_price', 'created_date'
    )
    list_display_links = ('id', 'full_name')
    list_filter = ('status', 'payment_method', 'created_date', 'shop')
    search_fields = (
        'full_name', 'email', 'phone', 
        'address', 'card_message', 'comments'
    )
    inlines = [OrderItemInline]
    readonly_fields = ('created_date', 'updated_date', 'total_price')
    list_editable = ('status',)
    date_hierarchy = 'created_date'


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = (
        'full_name', 'phone', 'birthday', 
        'spouse_name', 'spouse_birthday'
    )
    search_fields = (
        'full_name', 'phone', 
        'spouse_name', 'favorite_flowers'
    )
    list_filter = ('birthday', 'spouse_birthday')


@admin.register(TelegramManager)
class TelegramManagerAdmin(admin.ModelAdmin):
    list_display = ('user', 'chat_id', 'is_active', 'notify_orders')
    list_filter = ('is_active', 'notify_orders')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'chat_id')
    list_editable = ('is_active', 'notify_orders')