from django.contrib import admin
from .models import Product, Category

from django.contrib import admin
from django.utils.html import format_html
from .models import *

class ShopAdmin(admin.ModelAdmin):
    list_display = ('name', 'address', 'phone', 'work_hours')
    search_fields = ('name', 'address', 'phone')
    list_filter = ('name',)

class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)

class ProductAdmin(admin.ModelAdmin):
    list_display = (
        'name', 
        'category', 
        'get_product_type_display',
        'price', 
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

admin.site.register(MainCategory)
admin.site.register(Category)
admin.site.register(Product, ProductAdmin)
admin.site.register(Shop)

class ReviewAdmin(admin.ModelAdmin):
    list_display = ('product', 'name', 'rating', 'approved', 'created')
    list_filter = ('approved', 'rating', 'created')
    search_fields = ('product__name', 'name', 'email', 'text')
    list_editable = ('approved',)
    actions = ['approve_reviews']
    
    def approve_reviews(self, request, queryset):
        queryset.update(approved=True)
    approve_reviews.short_description = "Одобрить выбранные отзывы"

class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ('get_cost',)
    
    def get_cost(self, obj):
        return obj.get_cost()
    get_cost.short_description = "Стоимость"

class CartAdmin(admin.ModelAdmin):
    list_display = ('user', 'created', 'updated', 'get_total_price')
    inlines = [CartItemInline]
    readonly_fields = ('created', 'updated')
    
    def get_total_price(self, obj):
        return obj.get_total_price()
    get_total_price.short_description = "Общая стоимость"

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('get_cost',)
    
    def get_cost(self, obj):
        return obj.get_cost()
    get_cost.short_description = "Стоимость"

class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'user', 'first_name', 'last_name', 'phone', 
        'status', 'payment_method', 'total_price', 'created'
    )
    list_filter = ('status', 'payment_method', 'created', 'shop')
    search_fields = (
        'first_name', 'last_name', 'email', 'phone', 
        'address', 'card_message', 'comments'
    )
    inlines = [OrderItemInline]
    readonly_fields = ('created', 'updated')
    list_editable = ('status',)
    date_hierarchy = 'created'

class CustomerAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'phone', 'birthday', 
        'spouse_name', 'spouse_birthday'
    )
    search_fields = (
        'user__first_name', 'user__last_name', 'phone', 
        'spouse_name', 'favorite_flowers'
    )
    list_filter = ('birthday', 'spouse_birthday')
    readonly_fields = ('user',)



admin.site.register(Review, ReviewAdmin)
admin.site.register(Cart, CartAdmin)
admin.site.register(Order, OrderAdmin)
admin.site.register(Customer, CustomerAdmin)
# Register your models here.
from django.contrib import admin
from .models import TelegramManager

@admin.register(TelegramManager)
class TelegramManagerAdmin(admin.ModelAdmin):
    list_display = ('user', 'chat_id', 'is_active', 'notify_orders')
    list_filter = ('is_active', 'notify_orders')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'chat_id')
    list_editable = ('is_active', 'notify_orders')