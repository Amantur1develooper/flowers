import random
from django.db.models import Min, Max
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator

from .telegram_bot import send_telegram_notification
from .models import Product, Category, MainCategory, Cart, CartItem, Order, Shop, Review, Customer
from .forms import CustomerForm


def index(request):
    featured_products = Product.objects.filter(featured=True)[:8]
    categories = Category.objects.all()
    shops = Shop.objects.all()
    reviews = Review.objects.filter(approved=True)[:5]
    
    context = {
        'featured_products': featured_products,
        'categories': categories,
        'shops': shops,
        'reviews': reviews,
    }
    return render(request, 'index.html', context)


def about(request):
    return render(request, 'about.html')


def delivery(request):
    shops = Shop.objects.all()
    return render(request, 'delivery.html', {'shops': shops})


def contacts(request):
    shops = Shop.objects.all()
    return render(request, 'contacts.html', {'shops': shops})


def apply_price_filter(queryset, request):
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price') 
    
    if min_price and min_price.isdigit():
        queryset = queryset.filter(price__gte=int(min_price))
    
    if max_price and max_price.isdigit():
        queryset = queryset.filter(price__lte=int(max_price))
            
    return queryset


def get_min_max_prices(products):
    """Получаем минимальную и максимальную цену для товаров"""
    if not products.exists():
        return {'min': 0, 'max': 10000}
    
    prices = products.aggregate(
        min_price=Min('price'),
        max_price=Max('price')
    )
    
    min_price = prices['min_price'] or 0
    max_price = prices['max_price'] or 10000
    
    return {'min': int(min_price), 'max': int(max_price)}


def catalog_view(request, main_category_slug=None, category_slug=None):
    # Получаем основную категорию и подкатегорию
    main_categories = MainCategory.objects.all()
    
    # Определяем базовый набор товаров
    if main_category_slug and category_slug:
        main_category = get_object_or_404(MainCategory, slug=main_category_slug)
        category = get_object_or_404(Category, slug=category_slug, main_category=main_category)
        base_products = Product.objects.filter(category=category, available=True)
    elif main_category_slug:
        main_category = get_object_or_404(MainCategory, slug=main_category_slug)
        categories = Category.objects.filter(main_category=main_category)
        base_products = Product.objects.filter(category__in=categories, available=True)
        category = None
    else:
        base_products = Product.objects.filter(available=True)
        main_category = None
        category = None
    
    # Получаем диапазон цен для ВСЕХ товаров в базовом наборе
    min_price_range = {
        'min': base_products.aggregate(min_price=Min('price'))['min_price'] or 0,
        'max': base_products.aggregate(max_price=Max('price'))['max_price'] or 10000
    }
    
    # Применяем фильтр по цене
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    
    filtered_products = base_products
    if min_price and min_price.isdigit():
        filtered_products = filtered_products.filter(price__gte=int(min_price))
    if max_price and max_price.isdigit():
        filtered_products = filtered_products.filter(price__lte=int(max_price))
    
    # Пагинация
    paginator = Paginator(filtered_products, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'main_categories': main_categories,
        'main_category': main_category,
        'category': category,
        'categories': Category.objects.filter(main_category=main_category) if main_category else Category.objects.all(),
        'products': page_obj,
        'min_price_range': min_price_range,
    }
    return render(request, 'shop/catalog.html', context)


def catalog_by_main_category(request, main_category_slug):
    main_category = get_object_or_404(MainCategory, slug=main_category_slug)
    categories = Category.objects.filter(main_category=main_category)
    products = Product.objects.filter(
        available=True,
        category__in=categories
    )
    
    min_price_range = get_min_max_prices(products)  # Добавляем
    products = apply_price_filter(products, request)
    
    paginator = Paginator(products, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'main_categories': MainCategory.objects.all(),
        'main_category': main_category,
        'category': None,
        'categories': categories,
        'products': page_obj,
        'min_price_range': min_price_range,  # Добавляем в контекст
    }
    return render(request, 'shop/catalog.html', context)


def catalog_by_category(request, main_category_slug, category_slug):
    main_category = get_object_or_404(MainCategory, slug=main_category_slug)
    category = get_object_or_404(Category, slug=category_slug, main_category=main_category)
    products = Product.objects.filter(
        available=True,
        category=category
    )
    
    min_price_range = get_min_max_prices(products)  # Добавляем
    products = apply_price_filter(products, request)
    
    paginator = Paginator(products, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'main_categories': MainCategory.objects.all(),
        'main_category': main_category,
        'category': category,
        'categories': Category.objects.filter(main_category=main_category),
        'products': page_obj,
        'min_price_range': min_price_range,  # Добавляем в контекст
    }
    return render(request, 'shop/catalog.html', context)


def main_category_view(request, main_category_slug):
    main_category = get_object_or_404(MainCategory, slug=main_category_slug)
    categories = Category.objects.filter(main_category=main_category)
    products = Product.objects.filter(
        available=True,
        category__in=categories
    )
    
    # Пагинация
    paginator = Paginator(products, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'main_categories': MainCategory.objects.all(),
        'main_category': main_category,
        'category': None,
        'categories': categories,
        'products': page_obj,
    }
    return render(request, 'shop/catalog.html', context)


def product_detail(request, id, slug):
    product = get_object_or_404(Product, id=id, slug=slug, available=True)
    related_products = Product.objects.filter(
        category=product.category
    ).exclude(id=product.id)[:4]  # 4 похожих товара
    
    context = {
        'product': product,
        'related_products': related_products,
    }
    return render(request, 'shop/product_detail.html', context)


def cart_add(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)
    
    if not created:
        cart_item.quantity += 1
        cart_item.save()
    
    return redirect('cart_detail')


@login_required
def cart_remove(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    cart = Cart.objects.get(user=request.user)
    cart_item = CartItem.objects.get(cart=cart, product=product)
    
    if cart_item.quantity > 1:
        cart_item.quantity -= 1
        cart_item.save()
    else:
        cart_item.delete()
    
    return redirect('cart_detail')


@login_required
def order_confirmation(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'order_confirmation.html', {'order': order})


@login_required
def account(request):
    customer, created = Customer.objects.get_or_create(user=request.user)
    orders = Order.objects.filter(user=request.user).order_by('-created')
    
    if request.method == 'POST':
        form = CustomerForm(request.POST, instance=customer)
        if form.is_valid():
            form.save()
            return redirect('account')
    else:
        form = CustomerForm(instance=customer)
    
    context = {
        'customer': customer,
        'orders': orders,
        'form': form,
    }
    return render(request, 'account.html', context)


# CRM функции (только для админов)
@login_required
def customer_list(request):
    if not request.user.is_staff:
        return redirect('index')
    
    customers = Customer.objects.all()
    return render(request, 'crm/customer_list.html', {'customers': customers})

@login_required
def birthday_reminders(request):
    if not request.user.is_staff:
        return redirect('index')
    
    # Логика для дней рождения
    return render(request, 'crm/birthday_reminders.html')


@login_required
def order_management(request):
    if not request.user.is_staff:
        return redirect('index')
    
    orders = Order.objects.all().order_by('-created')
    return render(request, 'crm/order_management.html', {'orders': orders})


def get_cart(request):
    """Получаем корзину из сессии или создаем новую"""
    cart = request.session.get('cart', {})
    return cart


def update_cart(request, cart):
    """Обновляем корзину в сессии"""
    request.session['cart'] = cart
    request.session.modified = True


def add_to_cart(request, product_id):
    """Добавление товара в корзину"""
    product = get_object_or_404(Product, id=product_id)
    cart = get_cart(request)
    
    # Получаем количество из формы (по умолчанию 1)
    quantity = int(request.POST.get('quantity', 1))
    
    # Обновляем количество товара в корзине
    if str(product_id) in cart:
        cart[str(product_id)] += quantity
    else:
        cart[str(product_id)] = quantity
    
    update_cart(request, cart)
    messages.success(request, f'Товар "{product.name}" добавлен в корзину')
    return redirect(request.META.get('HTTP_REFERER', 'catalog'))


def remove_from_cart(request, product_id):
    """Удаление товара из корзины"""
    product = get_object_or_404(Product, id=product_id)
    cart = get_cart(request)
    
    if str(product_id) in cart:
        del cart[str(product_id)]
        update_cart(request, cart)
        messages.success(request, f'Товар "{product.name}" удален из корзины')
    
    return redirect('cart_detail')


def update_cart_item(request, product_id):
    """Обновление количества товара в корзине"""
    if request.method == 'POST':
        product = get_object_or_404(Product, id=product_id)
        cart = get_cart(request)
        quantity = int(request.POST.get('quantity', 1))
        
        if quantity > 0:
            cart[str(product_id)] = quantity
        else:
            del cart[str(product_id)]
        
        update_cart(request, cart)
        messages.success(request, f'Количество товара "{product.name}" обновлено')
    
    return redirect('cart_detail')


def cart_detail(request):
    """Просмотр корзины"""
    cart = get_cart(request)
    products = []
    total_price = 0
    
    # Получаем товары из корзины
    for product_id, quantity in cart.items():
        product = get_object_or_404(Product, id=int(product_id))
        item_total = product.price * quantity
        products.append({
            'product': product,
            'quantity': quantity,
            'total': item_total
        })
        total_price += item_total
    
    context = {
        'cart_items': products,
        'total_price': total_price
    }
    return render(request, 'shop/cart.html', context)


def checkout(request):
    """Оформление заказа"""
    cart = request.session.get('cart', {})
    
    if not cart:
        messages.warning(request, "Ваша корзина пуста")
        return redirect('cart_detail')
    
    # Получаем товары для отображения (для GET и POST запросов)
    products = []
    total_price = 0
    
    for product_id, quantity in cart.items():
        product = get_object_or_404(Product, id=int(product_id))
        item_total = product.price * quantity
        products.append({
            'product': product,
            'quantity': quantity,
            'total': item_total
        })
        total_price += item_total
    
    if request.method == 'POST':
        # Обработка формы заказа
        name = request.POST.get('name')
        phone = request.POST.get('phone')
        email = request.POST.get('email', '')
        address = request.POST.get('address', '')
        delivery_type = request.POST.get('delivery_type', 'self_pickup')
        comment = request.POST.get('comment', '')
        
        # Валидация данных
        if not name or not phone:
            messages.error(request, "Пожалуйста, заполните обязательные поля")
            return redirect('checkout')
        
        # Формируем заказ
        order_details = {
            'name': name,
            'phone': phone,
            'email': email,
            'address': address,
            'delivery_type': delivery_type,
            'comment': comment,
            'items': []
        }
        
        for product in products:
            order_details['items'].append({
                'name': product['product'].name,
                'quantity': product['quantity'],
                'price': product['product'].price,
                'total': product['total']
            })
        
        order_details['total_price'] = total_price
        
        # Отправляем уведомление в Telegram
        message = format_telegram_message(order_details)
        if send_telegram_notification(message):
            # Генерируем номер заказа
            order_id = random.randint(1000, 9999)
            request.session['order_id'] = order_id
            messages.success(request, "Заказ успешно оформлен! Мы свяжемся с вами в ближайшее время.")
        else:
            messages.success(request, "Заказ оформлен! Примечание: не удалось отправить уведомление менеджерам.")
        
        # Очищаем корзину
        request.session['cart'] = {}
        request.session.modified = True
        
        return redirect('order_success')
    
    context = {
        'cart_items': products,
        'total_price': total_price
    }
    return render(request, 'shop/checkout.html', context)


def order_success(request):
    """Страница успешного оформления заказа"""
    return render(request, 'shop/order_success.html')


def format_telegram_message(order_details):
    """Форматирование сообщения для Telegram"""
    items_text = "\n".join(
        f"➡ {item['name']} - {item['quantity']} × {item['price']} сом = {item['total']} сом"
        for item in order_details['items']
    )
    
    delivery_text = (
        f"🚚 Доставка: {order_details['address']}" 
        if order_details['delivery_type'] != 'self_pickup' 
        else "🏪 Самовывоз"
    )
    
    return f"""
<b>Новый заказ!</b>

👤 <b>Клиент:</b> {order_details['name']}
📞 <b>Телефон:</b> {order_details['phone']}
📧 <b>Email:</b> {order_details['email'] or 'не указан'}
{delivery_text}
💬 <b>Комментарий:</b> {order_details['comment'] or 'нет комментария'}

<b>Заказ:</b>
{items_text}

<b>Итого:</b> {order_details['total_price']} сом
"""