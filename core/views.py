import random
from django.db.models import Min, Max, Q
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.views.generic import ListView, CreateView, UpdateView
from django.urls import reverse_lazy

from .telegram_bot import send_telegram_notification
from .models import Product, Category, MainCategory, Order, OrderItem, Shop, Review, Customer
from .forms import CustomerForm
# views.py - добавим в начало
def get_product_by_id(product_id, model_type='product'):
    """
    Универсальная функция для получения товара по ID и типу
    """
    if model_type == 'akchii':
        return get_object_or_404(Akchii, id=product_id)
    else:
        return get_object_or_404(Product, id=product_id)


def get_cart_products(cart):
    """
    Универсальная функция для получения товаров из корзины
    Возвращает список товаров и общую сумму
    """
    products = []
    total_price = 0
    total_original_price = 0
    total_savings = 0

    for key, quantity in cart.items():
        try:
            # Определяем тип модели и ID
            if '_' in key:
                model_type, product_id = key.split('_')
            else:
                model_type, product_id = 'product', key

            # Получаем объект товара
            if model_type == 'akchii':
                product = Akchii.objects.get(id=int(product_id), available=True)
            else:
                product = Product.objects.get(id=int(product_id), available=True)

            # Цены
            unit_price = product.final_price
            original_unit_price = product.price

            item_total = unit_price * quantity
            original_item_total = original_unit_price * quantity
            item_savings = original_item_total - item_total

            # Добавляем данные в список
            products.append({
                'product': product,
                'model_type': model_type,
                'quantity': quantity,
                'unit_price': unit_price,
                'original_unit_price': original_unit_price,
                'item_total': item_total,
                'original_item_total': original_item_total,
                'item_savings': item_savings,
            })

            # Считаем общие итоги
            total_price += item_total
            total_original_price += original_item_total
            total_savings += item_savings

        except (Product.DoesNotExist, Akchii.DoesNotExist, ValueError) as e:
            # Логируем и пропускаем невалидный элемент
            print(f"Внимание: элемент корзины {key} не найден: {e}")
            continue

    return products, total_price, total_original_price, total_savings



class CustomerListView(ListView):
    model = Customer
    template_name = 'customers/customer_list.html'
    context_object_name = 'customers'
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset()
        search_query = self.request.GET.get('search', '')
        if search_query:
            queryset = queryset.filter(
                Q(full_name__icontains=search_query) |
                Q(phone__icontains=search_query) |
                Q(spouse_name__icontains=search_query) |
                Q(spouse_phone__icontains=search_query)
            )
        return queryset


class CustomerCreateView(CreateView):
    model = Customer
    template_name = 'customers/customer_form.html'
    fields = [
        'full_name', 'phone', 'birthday', 
        'spouse_name', 'spouse_birthday', 'spouse_phone',
        'favorite_flowers', 'notes', 'point'
    ]
    success_url = reverse_lazy('customer-list')


class CustomerUpdateView(UpdateView):
    model = Customer
    template_name = 'customers/customer_form.html'
    fields = [
        'full_name', 'phone', 'birthday', 
        'spouse_name', 'spouse_birthday', 'spouse_phone',
        'favorite_flowers', 'notes', 'point'
    ]
    success_url = reverse_lazy('customer-list')


def index(request):
    context = {
        'featured_products': Product.objects.filter(featured=True)[:8],
        'categories': Category.objects.all(),
        'shops': Shop.objects.all(),
        'reviews': Review.objects.filter(approved=True)[:5],
    }
    return render(request, 'index.html', context)


def about(request):
    context = {
        'shops': Shop.objects.all(), 
    }
    return render(request, 'about.html', context)


def delivery(request):
    return render(request, 'delivery.html', {'shops': Shop.objects.all()})


def contacts(request):
    return render(request, 'contacts.html', {'shops': Shop.objects.all()})


def get_min_max_prices(products):
    """Get min and max prices for products"""
    prices = products.aggregate(
        min_price=Min('price'),
        max_price=Max('price')
    )
    return {
        'min': int(prices['min_price']) if prices['min_price'] else 0,
        'max': int(prices['max_price']) if prices['max_price'] else 10000
    }


def apply_price_filter(queryset, request):
    """Apply price filtering to queryset"""
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    
    if min_price and min_price.isdigit():
        queryset = queryset.filter(price__gte=int(min_price))
    if max_price and max_price.isdigit():
        queryset = queryset.filter(price__lte=int(max_price))
    return queryset

from django.db import models
def catalog_view(request, main_category_slug=None, category_slug=None):
    """Unified catalog view for all categories"""
    # Get base products and categories
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
    
    # Apply filters and pagination
    filtered_products = apply_price_filter(base_products, request)
    min_price_range = get_min_max_prices(base_products)
    # Добавляем аннотацию для сортировки по скидкам
    from django.db.models import Case, When, Value, IntegerField
    filtered_products = filtered_products.annotate(
        has_discount_order=Case(
            When(skidka__isnull=False, skidka__lt=models.F('price'), then=Value(1)),
            default=Value(0),
            output_field=IntegerField()
        )
    ).order_by('?')
    paginator = Paginator(filtered_products, 12)
    page_obj = paginator.get_page(request.GET.get('page'))
    
    context = {
        'main_categories': MainCategory.objects.all(),
        'main_category': main_category,
        'category': category,
        'categories': Category.objects.filter(main_category=main_category) if main_category else Category.objects.all(),
        'products': page_obj,
        'min_price_range': min_price_range,
    }
    return render(request, 'shop/catalog.html', context)


def product_detail(request, id, slug):
    product = get_object_or_404(Product, id=id, slug=slug, available=True)
    context = {
        'product': product,
        'related_products': Product.objects.filter(category=product.category)
                                  .exclude(id=product.id)[:4],
    }
    return render(request, 'shop/product_detail.html', context)


# views.py - заменим cart_operations и cart_operations2
def cart_operations(request, product_id, operation):
    """Универсальная функция для операций с корзиной (работает с Product и Akchii)"""
    # Определяем тип модели из POST или GET параметров
    model_type = request.POST.get('model_type') or request.GET.get('model_type', 'product')
    
    # Получаем товар
    product = get_product_by_id(product_id, model_type)
    
    cart = request.session.get('cart', {})
    
    # Создаем уникальный ключ для корзины (включая тип модели)
    cart_key = f"{model_type}_{product_id}"
    
    if operation == 'add':
        quantity = int(request.POST.get('quantity', 1))
        cart[cart_key] = cart.get(cart_key, 0) + quantity
        msg = f'Товар "{product.name}" добавлен в корзину'
        
        # Если запрос AJAX, возвращаем JSON
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            cart_items_count = sum(cart.values())
            request.session['cart_items_count'] = cart_items_count
            request.session.modified = True
            
            return JsonResponse({
                'success': True,
                'message': msg,
                'cart_items_count': cart_items_count
            })
            
    elif operation == 'remove':
        if cart_key in cart:
            del cart[cart_key]
            msg = f'Товар "{product.name}" удален из корзины'
    elif operation == 'update' and request.method == 'POST':
        quantity = int(request.POST.get('quantity', 1))
        if quantity > 0:
            cart[cart_key] = quantity
            msg = f'Количество товара "{product.name}" обновлено'
        else:
            del cart[cart_key]
            msg = f'Товар "{product.name}" удален из корзины'
    else:
        return redirect('cart_detail')
    
    request.session['cart'] = cart
    request.session.modified = True
    
    # Для обычных запросов используем messages и редирект
    messages.success(request, msg)
    return redirect('cart_detail')
# def cart_operations(request, product_id, operation):
#     """Handle all cart operations (add/remove/update) with discount support"""
#     product = get_object_or_404(Product, id=product_id)
#     cart = request.session.get('cart', {})
#     str_id = str(product_id)
    
#     if operation == 'add':
#         quantity = int(request.POST.get('quantity', 1))
#         cart[str_id] = cart.get(str_id, 0) + quantity
#         msg = f'Товар "{product.name}" добавлен в корзину'
#     elif operation == 'remove':
#         if str_id in cart:
#             del cart[str_id]
#             msg = f'Товар "{product.name}" удален из корзины'
#     elif operation == 'update' and request.method == 'POST':
#         quantity = int(request.POST.get('quantity', 1))
#         if quantity > 0:
#             cart[str_id] = quantity
#             msg = f'Количество товара "{product.name}" обновлено'
#         else:
#             del cart[str_id]
#             msg = f'Товар "{product.name}" удален из корзины'
#     else:
#         return redirect('cart_detail')
    
#     request.session['cart'] = cart
#     request.session.modified = True
#     messages.success(request, msg)
#     return redirect('cart_detail')
# views.py - заменим cart_detail и cart_detail2
def cart_detail(request):
    """Универсальная функция для отображения корзины"""
    cart = request.session.get('cart', {})
    
    # Получаем все товары из корзины (и Product и Akchii)
    cart_items, total_price, total_original_price, total_savings = get_cart_products(cart)
    
    items_count = sum(item['quantity'] for item in cart_items)
    request.session['cart_items_count'] = items_count
    
    return render(request, 'shop/cart.html', {
        'cart_items': cart_items,
        'total_price': total_price,
        'total_original_price': total_original_price,
        'total_savings': total_savings,
    })

# def cart_detail(request):
#     """Display cart contents with discount support"""
#     cart = request.session.get('cart', {})
#     products = []
#     total_price = 0
#     total_original_price = 0  # Сумма без скидок
#     total_savings = 0  # Общая экономия
    
#     for product_id, quantity in cart.items():
#         product = get_object_or_404(Product, id=int(product_id))
        
#         # Используем финальную цену (со скидкой если есть)
#         unit_price = product.final_price
#         item_total = unit_price * quantity
        
#         # Рассчитываем оригинальную цену для отображения скидки
#         original_unit_price = product.price
#         original_item_total = original_unit_price * quantity
        
#         # Рассчитываем экономию для этого товара
#         item_savings = original_item_total - item_total
        
#         products.append({
#             'product': product,
#             'quantity': quantity,
#             'unit_price': unit_price,
#             'total': item_total,
#             'original_unit_price': original_unit_price,
#             'original_total': original_item_total,
#             'savings': item_savings,
#             'has_discount': product.has_discount,
#             'discount_percentage': product.discount_percentage,
#         })
        
#         total_price += item_total
#         total_original_price += original_item_total
#         total_savings += item_savings

#     items_count = sum(item['quantity'] for item in products)
#     request.session['cart_items_count'] = items_count
    
#     return render(request, 'shop/cart.html', {
#         'cart_items': products,
#         'total_price': total_price,
#         'total_original_price': total_original_price,
#         'total_savings': total_savings,
#     })

# views.py - обновим checkout функцию
def checkout(request):
    """Универсальная функция оформления заказа (работает с Product и Akchii)"""
    cart = request.session.get('cart', {})
    
    if not cart:
        messages.warning(request, "Ваша корзина пуста")
        return redirect('cart_detail')
    
    # Получаем товары из корзины
    cart_items, total_price, total_original_price, total_savings = get_cart_products(cart)
    
    if not cart_items:
        messages.warning(request, "В вашей корзине нет доступных товаров")
        return redirect('cart_detail')
    
    if request.method == 'POST':
        # Валидация обязательных полей
        required_fields = ['name', 'phone']
        if not all(request.POST.get(field) for field in required_fields):
            messages.error(request, "Пожалуйста, заполните обязательные поля")
            return redirect('checkout')
        
        # Создаем заказ
        order = Order.objects.create(
            full_name=request.POST.get('name'),
            phone=request.POST.get('phone'),
            address=request.POST.get('address', ''),
            delivery_type=request.POST.get('delivery_type', 'pickup'),
            comment=request.POST.get('comment', ''),
            payment_method=request.POST.get('payment_method', 'cash'),
            check_file=request.FILES.get('receipt')
        )
        
        # Создаем элементы заказа
        for item in cart_items:
            product = item['product']
            quantity = item['quantity']
            final_price = item['unit_price']
            model_type = item['model_type']
            
            OrderItem.objects.create(
                order=order,
                product=product if model_type == 'product' else None,
                akchii=product if model_type == 'akchii' else None,
                quantity=quantity,
                price=final_price
            )
        
        # Подготавливаем детали заказа для Telegram
        order_details = {
            'id': order.id,
            'name': order.full_name,
            'phone': order.phone,
            'address': order.address,
            'delivery_type': order.delivery_type,
            'payment_method': order.get_payment_method_display(),
            'comment': order.comment,
            'has_receipt': bool(order.check_file),
            'items': [{
                'name': f"{item['product'].name} {'(АКЦИЯ)' if item['model_type'] == 'akchii' else ''}",
                'quantity': item['quantity'],
                'price': item['unit_price'],
                'total': item['item_total']
            } for item in cart_items],
            'total_price': total_price,
        }
        
        # Отправляем уведомление в Telegram
        document_path = None
        if order.check_file:
            document_path = order.check_file.path
        
        message = format_telegram_message(order_details)
        if send_telegram_notification(message, document_path):
            messages.success(request, "Заказ успешно оформлен! Уведомление отправлено менеджерам.")
        else:
            messages.success(request, "Заказ оформлен! Не удалось отправить уведомление менеджерам.")
        
        # Очищаем корзину
        request.session['cart'] = {}
        request.session.modified = True
        
        return redirect('order_success')
    
    return render(request, 'shop/checkout.html', {
        'cart_items': cart_items,
        'total_price': total_price,
    })
    
    
# def checkout(request):
#     """Handle order checkout with receipt support"""
#     cart = request.session.get('cart', {})
    
#     if not cart:
#         messages.warning(request, "Ваша корзина пуста")
#         return redirect('cart_detail')
    
#     # Calculate order totals (your existing code)
#     products = []
#     total_price = 0
#     # ... keep your existing cart calculation code ...
    
#     if request.method == 'POST':
#         # Validate required fields
#         required_fields = ['name', 'phone']
#         if not all(request.POST.get(field) for field in required_fields):
#             messages.error(request, "Пожалуйста, заполните обязательные поля")
#             return redirect('checkout')
        
#         # Create the order
#         order = Order.objects.create(
#             full_name=request.POST.get('name'),
#             phone=request.POST.get('phone'),
#             address=request.POST.get('address', ''),
#             delivery_type=request.POST.get('delivery_type', 'pickup'),
#             comment=request.POST.get('comment', ''),
#             payment_method=request.POST.get('payment_method', 'cash'),
#             check_file=request.FILES.get('receipt')  # This handles file upload
#         )
        
#         # Create order items
#         for product_id, quantity in cart.items():
#             product = get_object_or_404(Product, id=int(product_id))
#             final_price = product.final_price
            
#             OrderItem.objects.create(
#                 order=order,
#                 product=product,
#                 quantity=quantity,
#                 price=final_price
#             )
        
#         # Prepare order details for notification
#         order_details = {
#             'id': order.id,
#             'name': order.full_name,
#             'phone': order.phone,
#             'address': order.address,
#             'delivery_type': order.delivery_type,
#             'payment_method': order.get_payment_method_display(),
#             'comment': order.comment,
#             'has_receipt': bool(order.check_file),
#             'items': [{
#                 'name': item.product.name,
#                 'quantity': item.quantity,
#                 'price': item.price,
#                 'total': item.get_cost()
#             } for item in order.items.all()],
#             'total_price': total_price,
#         }
        
#         # Send Telegram notification with optional receipt
#         document_path = None
#         if order.check_file:
#             # Get the full path to the uploaded file
#             document_path = order.check_file.path
        
#         message = format_telegram_message(order_details)
#         if send_telegram_notification(message, document_path):
#             messages.success(request, "Заказ успешно оформлен! Уведомление отправлено менеджерам.")
#         else:
#             messages.success(request, "Заказ оформлен! Не удалось отправить уведомление менеджерам.")
        
#         # Clear the cart
#         request.session['cart'] = {}
#         request.session.modified = True
        
#         return redirect('order_success')
    
#     return render(request, 'shop/checkout.html', {
#         'cart_items': products,
#         'total_price': total_price,
#     })





def order_success(request):
    """Order success page"""
    return render(request, 'shop/order_success.html')


@login_required
def order_confirmation(request, order_id):
    """View for showing order confirmation details"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'order_confirmation.html', {'order': order})


@login_required
def account(request):
    """User account page"""
    customer, created = Customer.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        form = CustomerForm(request.POST, instance=customer)
        if form.is_valid():
            form.save()
            return redirect('account')
    else:
        form = CustomerForm(instance=customer)
    
    return render(request, 'account.html', {
        'customer': customer,
        'orders': Order.objects.filter(user=request.user).order_by('-created'),
        'form': form,
    })


@login_required
def crm_view(request, template):
    """Unified CRM view"""
    if not request.user.is_staff:
        return redirect('index')
    
    templates = {
        'customers': ('crm/customer_list.html', {'customers': Customer.objects.all()}),
        'birthdays': ('crm/birthday_reminders.html', {}),
        'orders': ('crm/order_management.html', {'orders': Order.objects.all().order_by('-created')}),
    }
    
    if template not in templates:
        return redirect('index')
    
    template_path, context = templates[template]
    return render(request, template_path, context)






def format_telegram_message(order_details):
    """Format order details for Telegram notification with HTML formatting"""
    
    items_text = "\n".join(
        f"• {item['name']} - {item['quantity']} × {item['price']} сом = {item['total']} сом"
        for item in order_details['items']
    )
    
    delivery_info = "🚚 Доставка" if order_details['delivery_type'] == 'delivery' else "🏪 Самовывоз"
    if order_details.get('address'):
        delivery_info += f"\n📍 Адрес: {order_details['address']}"
    
    payment_method = order_details.get('payment_method', 'не указан')
    receipt_info = "\n🧾 Чек об оплате приложен" if order_details.get('has_receipt') else "\n⏳ Чек не предоставлен"
    
    return f"""
<b>🛒 НОВЫЙ ЗАКАЗ #{order_details.get('id', '')}</b>

👤 <b>Клиент:</b> {order_details['name']}
📞 <b>Телефон:</b> {order_details['phone']}
💳 <b>Способ оплаты:</b> {payment_method}{receipt_info}

{delivery_info}

<b>Состав заказа:</b>
{items_text}

<b>💰 Итого к оплате:</b> <u>{order_details['total_price']} сом</u>

💬 <b>Комментарий:</b> {order_details['comment'] or 'нет'}
"""



def main_menu(request):
    # Получаем основные категории для отображения
    main_categories = MainCategory.objects.all()
    
    context = {
        'main_categories': main_categories,
    }
    return render(request, 'shop/main_menu.html', context)



from django.shortcuts import render
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q, Avg, Max
from .models import Akchii, Category
from django.db.models.functions import Coalesce
from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q, Avg, Max
from .models import Akchii
def discounts_view(request):
    """
    Представление для страницы акционных товаров
    """
    # Получаем все акционные товары (где skidka не None)
    discount_products = Akchii.objects.filter(
        skidka__isnull=False,
        available=True
    ).order_by('-created')
    
    # Вычисляем статистику для акций
    discount_products_count = discount_products.count()
    
    if discount_products_count > 0:
        # Максимальный процент скидки
        products_with_discount = [
            product for product in discount_products 
            if product.has_discount
        ]
        
        if products_with_discount:
            max_discount_percentage = max(
                product.discount_percentage 
                for product in products_with_discount
            )
            
            # Средний процент скидки
            total_discount = sum(
                product.discount_percentage 
                for product in products_with_discount
            )
            average_discount_percentage = total_discount // len(products_with_discount)
        else:
            max_discount_percentage = 0
            average_discount_percentage = 0
    else:
        max_discount_percentage = 0
        average_discount_percentage = 0
    
    # Пагинация
    page = request.GET.get('page', 1)
    paginator = Paginator(discount_products, 12)
    
    try:
        discount_products_paginated = paginator.page(page)
    except PageNotAnInteger:
        discount_products_paginated = paginator.page(1)
    except EmptyPage:
        discount_products_paginated = paginator.page(paginator.num_pages)
    
    context = {
        'discount_products': discount_products_paginated,
        'discount_products_count': discount_products_count,
        'max_discount_percentage': max_discount_percentage,
        'average_discount_percentage': average_discount_percentage,
    }
    
    return render(request, 'shop/akchii.html', context)

def discount_product_detail(request, id, slug):
    """
    Детальная страница акционного товара
    """
    product = get_object_or_404(
        Akchii, 
        id=id, 
        slug=slug, 
        available=True
    )
    
    # Похожие акционные товары (исключая текущий)
    similar_products = Akchii.objects.filter(
        skidka__isnull=False,
        available=True
    ).exclude(id=id).order_by('-created')[:4]
    
    context = {
        'product': product,
        'similar_products': similar_products,
    }
    
    return render(request, 'shop/discount_product_detail.html', context)


# Контекстный процессор для отображения количества акционных товаров в шапке
def discounts_context(request):
    """Добавляет информацию об акционных товарах в контекст всех шаблонов"""
    discount_products_count = Akchii.objects.filter(
        skidka__isnull=False,
        available=True
    ).count()
    
    # Рекомендуемые акционные товары для отображения в других местах
    featured_discounts = Akchii.objects.filter(
        skidka__isnull=False,
        available=True
    ).order_by('-created')[:3]
    
    return {
        'discount_products_count': discount_products_count,
        'featured_discounts': featured_discounts,
    }
    
    #!

def cart_operations2(request, product_id, operation):
    """Handle all cart operations (add/remove/update) with discount support"""
    product = get_object_or_404(Akchii, id=product_id)
    cart = request.session.get('cart', {})
    str_id = str(product_id)
    
    if operation == 'add':
        quantity = int(request.POST.get('quantity', 1))
        cart[str_id] = cart.get(str_id, 0) + quantity
        msg = f'Товар "{product.name}" добавлен в корзину'
        
        # Если запрос AJAX, возвращаем JSON
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            # Подсчитываем общее количество товаров в корзине
            cart_items_count = sum(cart.values())
            request.session['cart_items_count'] = cart_items_count
            
            return JsonResponse({
                'success': True,
                'message': msg,
                'cart_items_count': cart_items_count
            })
            
    elif operation == 'remove':
        if str_id in cart:
            del cart[str_id]
            msg = f'Товар "{product.name}" удален из корзины'
    elif operation == 'update' and request.method == 'POST':
        quantity = int(request.POST.get('quantity', 1))
        if quantity > 0:
            cart[str_id] = quantity
            msg = f'Количество товара "{product.name}" обновлено'
        else:
            del cart[str_id]
            msg = f'Товар "{product.name}" удален из корзины'
    else:
        return redirect('cart_detail')
    
    request.session['cart'] = cart
    request.session.modified = True
    
    # Для обычных запросов используем messages и редирект
    messages.success(request, msg)
    return redirect('cart_detail')

def cart_detail2(request):
    """Display cart contents with discount support"""
    cart = request.session.get('cart', {})
    products = []
    total_price = 0
    total_original_price = 0  # Сумма без скидок
    total_savings = 0  # Общая экономия
    
    for product_id, quantity in cart.items():
        product = get_object_or_404(Akchii, id=int(product_id))
        
        # Используем финальную цену (со скидкой если есть)
        unit_price = product.final_price
        item_total = unit_price * quantity
        
        # Рассчитываем оригинальную цену для отображения скидки
        original_unit_price = product.price
        original_item_total = original_unit_price * quantity
        
        # Рассчитываем экономию для этого товара
        item_savings = original_item_total - item_total
        
        products.append({
            'product': product,
            'quantity': quantity,
            'unit_price': unit_price,
            'total': item_total,
            'original_unit_price': original_unit_price,
            'original_total': original_item_total,
            'savings': item_savings,
            'has_discount': product.has_discount,
            'discount_percentage': product.discount_percentage,
        })
        
        total_price += item_total
        total_original_price += original_item_total
        total_savings += item_savings

    items_count = sum(item['quantity'] for item in products)
    request.session['cart_items_count'] = items_count
    
    return render(request, 'shop/cart.html', {
        'cart_items': products,
        'total_price': total_price,
        'total_original_price': total_original_price,
        'total_savings': total_savings,
    })

# Контекстный процессор для отображения количества товаров в корзине
def cart_context(request):
    """Добавляет информацию о корзине в контекст всех шаблонов"""
    cart = request.session.get('cart', {})
    cart_items_count = sum(cart.values())
    
    return {
        'cart_items_count': cart_items_count,
    }