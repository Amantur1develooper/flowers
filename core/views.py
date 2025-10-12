import random
from django.db.models import Min, Max, Q
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.views.generic import ListView, CreateView, UpdateView
from django.urls import reverse_lazy

from .telegram_bot import send_telegram_notification
from .models import Product, Category, MainCategory, Order, OrderItem, Shop, Review, Customer
from .forms import CustomerForm



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



def cart_operations(request, product_id, operation):
    """Handle all cart operations (add/remove/update) with discount support"""
    product = get_object_or_404(Product, id=product_id)
    cart = request.session.get('cart', {})
    str_id = str(product_id)
    
    if operation == 'add':
        quantity = int(request.POST.get('quantity', 1))
        cart[str_id] = cart.get(str_id, 0) + quantity
        msg = f'Товар "{product.name}" добавлен в корзину'
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
    messages.success(request, msg)
    return redirect('cart_detail')


def cart_detail(request):
    """Display cart contents with discount support"""
    cart = request.session.get('cart', {})
    products = []
    total_price = 0
    total_original_price = 0  # Сумма без скидок
    total_savings = 0  # Общая экономия
    
    for product_id, quantity in cart.items():
        product = get_object_or_404(Product, id=int(product_id))
        
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
# def cart_operations(request, product_id, operation):
#     """Handle all cart operations (add/remove/update)"""
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


# def cart_detail(request):
#     """Display cart contents"""
#     cart = request.session.get('cart', {})
#     products = []
#     total_price = 0
    
#     for product_id, quantity in cart.items():
#         product = get_object_or_404(Product, id=int(product_id))
#         item_total = product.price * quantity
#         products.append({
#             'product': product,
#             'quantity': quantity,
#             'total': item_total
#         })
#         total_price += item_total

#     items_count = sum(item['quantity'] for item in products)
#     request.session['cart_items_count'] = items_count
    
#     return render(request, 'shop/cart.html', {
#         'cart_items': products,
#         'total_price': total_price
#     })

def checkout(request):
    """Handle order checkout with receipt support"""
    cart = request.session.get('cart', {})
    
    if not cart:
        messages.warning(request, "Ваша корзина пуста")
        return redirect('cart_detail')
    
    # Calculate order totals (your existing code)
    products = []
    total_price = 0
    # ... keep your existing cart calculation code ...
    
    if request.method == 'POST':
        # Validate required fields
        required_fields = ['name', 'phone']
        if not all(request.POST.get(field) for field in required_fields):
            messages.error(request, "Пожалуйста, заполните обязательные поля")
            return redirect('checkout')
        
        # Create the order
        order = Order.objects.create(
            full_name=request.POST.get('name'),
            phone=request.POST.get('phone'),
            address=request.POST.get('address', ''),
            delivery_type=request.POST.get('delivery_type', 'pickup'),
            comment=request.POST.get('comment', ''),
            payment_method=request.POST.get('payment_method', 'cash'),
            check_file=request.FILES.get('receipt')  # This handles file upload
        )
        
        # Create order items
        for product_id, quantity in cart.items():
            product = get_object_or_404(Product, id=int(product_id))
            final_price = product.final_price
            
            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=quantity,
                price=final_price
            )
        
        # Prepare order details for notification
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
                'name': item.product.name,
                'quantity': item.quantity,
                'price': item.price,
                'total': item.get_cost()
            } for item in order.items.all()],
            'total_price': total_price,
        }
        
        # Send Telegram notification with optional receipt
        document_path = None
        if order.check_file:
            # Get the full path to the uploaded file
            document_path = order.check_file.path
        
        message = format_telegram_message(order_details)
        if send_telegram_notification(message, document_path):
            messages.success(request, "Заказ успешно оформлен! Уведомление отправлено менеджерам.")
        else:
            messages.success(request, "Заказ оформлен! Не удалось отправить уведомление менеджерам.")
        
        # Clear the cart
        request.session['cart'] = {}
        request.session.modified = True
        
        return redirect('order_success')
    
    return render(request, 'shop/checkout.html', {
        'cart_items': products,
        'total_price': total_price,
    })

# def checkout(request):
#     """Handle order checkout with discount support"""
#     cart = request.session.get('cart', {})
    
#     if not cart:
#         messages.warning(request, "Ваша корзина пуста")
#         return redirect('cart_detail')
    
#     # Prepare products for display with discount support
#     products = []
#     total_price = 0
#     total_original_price = 0
#     total_savings = 0
    
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
#         })
        
#         total_price += item_total
#         total_original_price += original_item_total
#         total_savings += item_savings
    
#     if request.method == 'POST':
#         required_fields = ['name', 'phone']
#         if not all(request.POST.get(field) for field in required_fields):
#             messages.error(request, "Пожалуйста, заполните обязательные поля")
#             return redirect('checkout')
        
#         # Создаем заказ
#         order = Order.objects.create(
#             full_name=request.POST.get('name'),
#             phone=request.POST.get('phone'),
#             address=request.POST.get('address', ''),
#             delivery_type=request.POST.get('delivery_type', 'pickup'),
#             comment=request.POST.get('comment', ''),
#             check_file=request.FILES.get('receipt', None),
#         )

#         # Создаем элементы заказа с учетом скидок
#         order_total_price = 0
#         for product_id, quantity in cart.items():
#             product = get_object_or_404(Product, id=int(product_id))
            
#             # Используем финальную цену (со скидкой)
#             final_price = product.final_price
#             item_total = final_price * quantity
            
#             OrderItem.objects.create(
#                 order=order,
#                 product=product,
#                 quantity=quantity,
#                 price=final_price  # Сохраняем цену с учетом скидки
#             )
#             order_total_price += item_total

#         # Обновляем общую сумму заказа
#         # order.total_price = order_total_price
#         order.save()

#         # Формируем детали заказа для уведомления
#         order_details = {
#             'name': order.full_name,
#             'phone': order.phone,
#             'address': order.address,
#             'delivery_type': order.delivery_type,
#             'comment': order.comment,
#             'items': [{
#                 'name': item.product.name,
#                 'quantity': item.quantity,
#                 'original_price': item.product.price,  # Оригинальная цена
#                 'final_price': item.price,  # Цена со скидкой
#                 'total': item.get_cost(),
#                 'has_discount': item.product.has_discount,
#                 'discount_percentage': item.product.discount_percentage if item.product.has_discount else 0,
#             } for item in order.items.all()],
#             'total_price': order_total_price,
#             'total_savings': total_savings,
#         }

#         # Отправляем уведомление в Telegram
#         if send_telegram_notification(format_telegram_message(order_details)):
#             messages.success(request, "Заказ успешно оформлен! Мы свяжемся с вами в ближайшее время.")
#         else:
#             messages.success(request, "Заказ оформлен! Примечание: не удалось отправить уведомление менеджерам.")

#         # Очищаем корзину
#         request.session['cart'] = {}
#         request.session.modified = True
        
#         return redirect('order_success')

#     return render(request, 'shop/checkout.html', {
#         'cart_items': products,
#         'total_price': total_price,
#         'total_original_price': total_original_price,
#         'total_savings': total_savings,
#     })
# # def checkout(request):
#     """Handle order checkout"""
#     cart = request.session.get('cart', {})
    
#     if not cart:
#         messages.warning(request, "Ваша корзина пуста")
#         return redirect('cart_detail')
    
#     # Prepare products for display
#     products = []
#     total_price = 0
    
#     for product_id, quantity in cart.items():
#         product = get_object_or_404(Product, id=int(product_id))
#         item_total = product.price * quantity
#         products.append({
#             'product': product,
#             'quantity': quantity,
#             'total': item_total
#         })
#         total_price += item_total
    
#     if request.method == 'POST':
#         required_fields = ['name', 'phone']
#         if not all(request.POST.get(field) for field in required_fields):
#             messages.error(request, "Пожалуйста, заполните обязательные поля")
#             return redirect('checkout')
        
#         # print(request.FILES)

#         # print(request.FILES.get('receipt', None))

#         order = Order.objects.create(
#             full_name=request.POST.get('name'),
#             phone=request.POST.get('phone'),
#             address=request.POST.get('address', ''),
#             delivery_type=request.POST.get('delivery_type', 'pickup'),
#             comment=request.POST.get('comment', ''),
#             check_file=request.FILES.get('receipt', None),
#         )

#         total_price = 0
#         for product_id, quantity in cart.items():
#             product = get_object_or_404(Product, id=int(product_id))
#             item_total = product.price * quantity
#             OrderItem.objects.create(
#                 order=order,
#                 product=product,
#                 quantity=quantity,
#                 price=product.price
#             )
#             total_price += item_total

#         order_details = {
#             'name': order.full_name,
#             'phone': order.phone,
#             'address': order.address,
#             'delivery_type': order.delivery_type,
#             'comment': order.comment,
#             'items': [{
#                 'name': item.product.name,
#                 'quantity': item.quantity,
#                 'price': item.price,
#                 'total': item.get_cost()
#             } for item in order.items.all()],
#             'total_price': total_price
#         }

#         if send_telegram_notification(format_telegram_message(order_details)):
#             messages.success(request, "Заказ успешно оформлен! Мы свяжемся с вами в ближайшее время.")
#         else:
#             messages.success(request, "Заказ оформлен! Примечание: не удалось отправить уведомление менеджерам.")

#         request.session['cart'] = {}
#         return redirect('order_success')

#     return render(request, 'shop/checkout.html', {
#         'cart_items': products,
#         'total_price': total_price
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



# def format_telegram_message(order_details):
#     """Форматирование сообщения для Telegram с учетом скидок"""
#     items_text = "\n".join(
#         f"➡ {item['name']} - {item['quantity']} шт. "
#         f"({item['original_price']} → {item['final_price']} сом) = {item['total']} сом"
#         + (f" 🔥 -{item['discount_percentage']}%" if item['has_discount'] else "")
#         for item in order_details['items']
#     )
    
#     delivery_text = (
#         f"🚚 Адрес доставки: {order_details['address']}" 
#         if order_details['delivery_type'] != 'pickup' 
#         else "🏪 Самовывоз"
#     )
    
#     savings_text = ""
#     if order_details.get('total_savings', 0) > 0:
#         savings_text = f"\n💰 Экономия: {order_details['total_savings']} сом"
    
#     return f"""
# <b>Новый заказ!</b>

# 👤 <b>Клиент:</b> {order_details['name']}
# 📞 <b>Телефон:</b> {order_details['phone']}
# {delivery_text}
# 💬 <b>Комментарий:</b> {order_details['comment'] or 'нет комментария'}

# <b>Заказ:</b>
# {items_text}

# <b>Итого к оплате:</b> {order_details['total_price']} сом{savings_text}
# """

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
# def format_telegram_message(order_details):
#     """Format order details for Telegram"""
#     items_text = "\n".join(
#         f"➡ {item['name']} - {item['quantity']} × {item['price']} сом = {item['total']} сом"
#         for item in order_details['items']
#     )
    
#     delivery_text = (
#         f"🚚 Доставка: {order_details['address']}" 
#         if order_details['delivery_type'] != 'self_pickup' 
#         else "🏪 Самовывоз"
#     )
    
#     return f"""
# <b>Новый заказ!</b>

# 👤 <b>Клиент:</b> {order_details['name']}
# 📞 <b>Телефон:</b> {order_details['phone']}
# {delivery_text}
# 💬 <b>Комментарий:</b> {order_details['comment'] or 'нет комментария'}

# <b>Заказ:</b>
# {items_text}

# <b>Итого:</b> {order_details['total_price']} сом
# """


def main_menu(request):
    # Получаем основные категории для отображения
    main_categories = MainCategory.objects.all()
    
    context = {
        'main_categories': main_categories,
    }
    return render(request, 'shop/main_menu.html', context)