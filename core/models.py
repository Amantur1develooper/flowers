from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator

from phonenumber_field.modelfields import PhoneNumberField


class Shop(models.Model):
    name = models.CharField(max_length=100, verbose_name="Название магазина")
    address = models.CharField(max_length=200, verbose_name="Адрес")
    phone = PhoneNumberField(verbose_name="Телефон")
    work_hours = models.CharField(max_length=100, verbose_name="Часы работы")
    map_link = models.URLField(blank=True, verbose_name="Ссылка на карту")
    
    class Meta:
        verbose_name = "Магазин"
        verbose_name_plural = "Магазины"
        ordering = ['name']
    
    def __str__(self):
        return self.name
    

class MainCategory(models.Model):
    name = models.CharField(max_length=100, verbose_name="Основная категория")
    slug = models.SlugField(max_length=100, unique=True, verbose_name="URL-адрес")
    icon = models.CharField(max_length=50, blank=True, verbose_name="Иконка (Font Awesome)")
    
    class Meta:
        verbose_name = "Основная категория"
        verbose_name_plural = "Основные категории"
    
    def __str__(self):
        return self.name
    
    
class Category(models.Model):
    main_category = models.ForeignKey(
        MainCategory, 
        related_name='categories',
        on_delete=models.CASCADE,
        verbose_name="Основная категория"
    )
    name = models.CharField(max_length=100, verbose_name="Название категории")
    slug = models.SlugField(max_length=100, unique=True, verbose_name="URL-адрес")
    
    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"
        ordering = ['name']
    
    def __str__(self):
        return f"{self.main_category.name} - {self.name}"
    

class Product(models.Model):
    PRODUCT_TYPES = [
        ('flower', 'Цветы'),
        ('toy', 'Игрушки'),
        ('cake', 'Десерты'),
    ]
    
    category = models.ForeignKey(
        Category, 
        related_name='products', 
        on_delete=models.CASCADE, 
        verbose_name="Категория"
    )
    product_type = models.CharField(
        max_length=10,
        choices=PRODUCT_TYPES,
        verbose_name="Тип товара"
    )
    name = models.CharField(max_length=100, verbose_name="Название товара")
    image = models.ImageField(
        upload_to='products/', 
        verbose_name="Изображение товара"
    )
    slug = models.SlugField(max_length=100, unique=True, verbose_name="URL-адрес")
    description = models.TextField(verbose_name="Описание товара")
    price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        verbose_name="Цена (сом)"
    )
    available = models.BooleanField(default=True, verbose_name="Доступен")
    featured = models.BooleanField(default=False, verbose_name="Рекомендуемый")
    created = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")
    skidka = models.DecimalField(max_digits=10,decimal_places=2, null=True, blank=True, verbose_name="Скидка((новая цена)сом)")
    
    # Дополнительные поля для цветов
    flowers_included = models.TextField(
        blank=True, 
        verbose_name="Состав букета (для цветов)"
    )
    height_cm = models.PositiveIntegerField(
        null=True, 
        blank=True,
        verbose_name="Высота букета (см)"
    )
    
    # Дополнительные поля для игрушек
    age_limit = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Возрастные ограничения"
    )
    material = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Материал"
    )
    
    # Дополнительные поля для десертов
    weight_grams = models.PositiveIntegerField(
        null=True, 
        blank=True,
        verbose_name="Вес (грамм)"
    )
    ingredients = models.TextField(
        blank=True, 
        verbose_name="Ингредиенты"
    )
    
    class Meta:
        verbose_name = "Товар"
        verbose_name_plural = "Товары"
        ordering = ['-created']
    
    def __str__(self):
        return self.name
    
    def get_product_type_display(self):
        return dict(self.PRODUCT_TYPES).get(self.product_type)    
    @property
    def savings_amount(self):
        """Вычисление суммы экономии при наличии скидки"""
        if self.has_discount:
            return self.price - self.final_price
        return 0
    @property
    def has_discount(self):
        """Проверяет, есть ли скидка у товара"""
        return self.skidka is not None and self.skidka < self.price
    
    @property
    def discount_percentage(self):
        """Вычисляет процент скидки"""
        if self.has_discount:
            return int(((self.price - self.skidka) / self.price) * 100)
        return 0
    
    @property
    def final_price(self):
        """Возвращает итоговую цену (со скидкой или оригинальную)"""
        return self.skidka if self.has_discount else self.price
    
    
class Review(models.Model):
    product = models.ForeignKey(
        Product, 
        related_name='reviews', 
        on_delete=models.CASCADE,
        verbose_name="Товар"
    )
    user = models.ForeignKey(
        User, 
        null=True, 
        blank=True, 
        on_delete=models.SET_NULL,
        verbose_name="Пользователь"
    )
    name = models.CharField(max_length=50, verbose_name="Имя")
    email = models.EmailField(verbose_name="Email")
    text = models.TextField(verbose_name="Текст отзыва")
    rating = models.PositiveSmallIntegerField(default=5, verbose_name="Рейтинг")
    created = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    approved = models.BooleanField(default=False, verbose_name="Одобрен")
    
    class Meta:
        verbose_name = "Отзыв"
        verbose_name_plural = "Отзывы"
        ordering = ['-created']
    
    def __str__(self):
        return f"Отзыв на {self.product.name} от {self.name}"


class TelegramManager(models.Model):
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE,
        verbose_name="Пользователь системы"
    )
    chat_id = models.CharField(
        max_length=50,
        verbose_name="Chat ID в Telegram",
        unique=True
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Активный"
    )
    notify_orders = models.BooleanField(
        default=True,
        verbose_name="Уведомлять о новых заказах"
    )
    
    class Meta:
        verbose_name = "Телеграм менеджер"
        verbose_name_plural = "Телеграм менеджеры"
    
    def __str__(self):
        return f"{self.user.get_full_name()} ({self.chat_id})"


class Order(models.Model):
    STATUS_CHOICES = [
        ('new', 'Новый'),
        ('processing', 'В обработке'),
        ('ready', 'Готов к самовывозу'),
        ('delivering', 'В доставке'),
        ('completed', 'Завершен'),
        ('cancelled', 'Отменен'),
    ]
    
    PAYMENT_CHOICES = [
        ('cash', 'Наличными'),
        ('card', 'Картой онлайн'),
    ]
    
    # user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Пользователь")
    full_name = models.CharField(max_length=50, verbose_name="ФИО")
    phone = models.CharField(max_length=20, verbose_name="Телефон")
    address = models.CharField(max_length=250, blank=True, verbose_name="Адрес доставки")
    shop = models.ForeignKey(
        Shop, 
        null=True, 
        blank=True, 
        on_delete=models.SET_NULL,
        verbose_name="Магазин самовывоза"
    )
    delivery_date = models.DateField(verbose_name="Дата доставки", null=True, blank=True)
    delivery_time = models.TimeField(verbose_name="Время доставки", null=True, blank=True)
    delivery_type = models.CharField(
        max_length=20, 
        choices=[
            ('pickup', 'Самовывоз'),
            ('delivery', 'Доставка')
        ],
        default='pickup',
        verbose_name="Тип доставки"
    )
    card_message = models.TextField(blank=True, verbose_name="Текст открытки")
    comment = models.TextField(blank=True, verbose_name="Комментарии к заказу")
    created_date = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_date = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")
    check_file = models.FileField(upload_to='checks/', blank=True, verbose_name="Чек (фото/файл)")
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='new',
        verbose_name="Статус заказа"
    )
    payment_method = models.CharField(
        max_length=10, 
        choices=PAYMENT_CHOICES, 
        default='cash',
        verbose_name="Способ оплаты"
    )
    
    class Meta:
        verbose_name = "Заказ"
        verbose_name_plural = "Заказы"
        ordering = ['-created_date']

    @property
    def total_price(self):
        return sum(item.get_cost() for item in self.items.all())
    
    def __str__(self):
        return f"Заказ №{self.id} от {self.full_name}"


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order, 
        related_name='items', 
        on_delete=models.CASCADE,
        verbose_name="Заказ"
    )
    product = models.ForeignKey(
        Product, 
        on_delete=models.CASCADE,
        verbose_name="Товар"
    )
    price = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        verbose_name="Цена",
        default=0.00,
    )
    quantity = models.PositiveIntegerField(
        default=1,
        verbose_name="Количество"
    )
    
    class Meta:
        verbose_name = "Элемент заказа"
        verbose_name_plural = "Элементы заказа"
        ordering = ['-id']
    
    def get_cost(self):
        return self.price * self.quantity
    
    def __str__(self):
        return f"{self.quantity} x {self.product.name} (заказ №{self.order.id})"


class Customer(models.Model):
    full_name = models.CharField(max_length=100, verbose_name="Полное имя")
    phone = models.CharField(max_length=20, verbose_name="Телефон",)
    birthday = models.DateField(
        null=True, 
        blank=True,
        verbose_name="Дата рождения"
    )
    spouse_name = models.CharField(
        max_length=100, 
        blank=True,
        verbose_name="Имя супруга/супруги (жена или муж)"
    )
    spouse_birthday = models.DateField(
        null=True, 
        blank=True,
        verbose_name="Дата рождения супруга/супруги"
    )
    spouse_phone = models.CharField(max_length=20, verbose_name="Телефон супруга/супруги", blank=True)
    favorite_flowers = models.CharField(
        max_length=200, 
        blank=True,
        verbose_name="Любимые цветы"
    )
    notes = models.TextField(blank=True, verbose_name="Заметки")
    point = models.PositiveIntegerField(
        default=0, 
        validators=[MinValueValidator(0)],
        verbose_name="Баллы"
    )
    is_paid = models.BooleanField(default=False, verbose_name="Оплачен")
    self_pickup = models.BooleanField(default=False, verbose_name="Самовывоз")

    class Meta:
        verbose_name = "Клиент"
        verbose_name_plural = "Клиенты"
        ordering = ['-id']
    
    def __str__(self):
        return f"Клиент {self.full_name}"
