# context_processors.py
def cart_context(request):
    """Добавляет информацию о корзине в контекст всех шаблонов"""
    cart = request.session.get('cart', {})
    cart_items_count = sum(cart.values())
    
    return {
        'cart_items_count': cart_items_count,
    }