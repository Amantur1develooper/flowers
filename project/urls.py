"""
URL configuration for project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from django.conf import settings 
from django.conf.urls.static import static
from core import views

  


 
   
urlpatterns = [  path('admin/', admin.site.urls),
    path('', views.index, name='index'),

    path('product/<int:id>/<slug:slug>/', views.product_detail, name='product_detail'),
    
    
    # path('catalog/<slug:category_slug>/', views.catalog_view, name='catalog_by_category'),
    # path('catalog/<slug:main_category_slug>/', views.catalog_view, name='main_category'),
    # path('catalog/<slug:main_category_slug>/<slug:category_slug>/', views.catalog_view, name='catalog_by_category'),

    path('catalog/', views.catalog_view, name='catalog'),
    path('catalog/<slug:main_category_slug>/', views.catalog_view, name='catalog_by_main_category'),
    path('catalog/<slug:main_category_slug>/<slug:category_slug>/', views.catalog_view, name='catalog_by_category'),
    # path('catalog/', views.catalog_view, name='catalog'),
    # path('catalog/<slug:main_category_slug>/', views.catalog_by_main_category, name='catalog_by_main_category'),
    # path('catalog/<slug:main_category_slug>/<slug:category_slug>/', views.catalog_by_category, name='catalog_by_category'),
    path('product/<int:id>/<slug:slug>/', views.product_detail, name='product_detail'),

    # path('cart/', views.cart_detail, name='cart_detail'),
    # path('cart/add/<int:product_id>/', views.cart_add, name='cart_add'),
    # path('cart/remove/<int:product_id>/', views.cart_remove, name='cart_remove'),
    
    path('cart/', views.cart_detail, name='cart_detail'),
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/remove/<int:product_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/update/<int:product_id>/', views.update_cart_item, name='update_cart_item'),
    
    path('checkout/', views.checkout, name='checkout'),
    path('order/<int:order_id>/', views.order_confirmation, name='order_confirmation'),
    
    path('account/', views.account, name='account'),
    
    path('order_success',views.order_success, name='order_success'),
    path('about/', views.about, name='about'),
    path('delivery/', views.delivery, name='delivery'),
    path('contacts/', views.contacts, name='contacts'),
    
    # CRM URLs (только для админов)
    path('crm/customers/', views.customer_list, name='customer_list'),
    path('crm/birthdays/', views.birthday_reminders, name='birthday_reminders'),
    path('crm/orders/', views.order_management, name='order_management'),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
