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

   
urlpatterns = [  
    path('admin/', admin.site.urls),
    path('', views.index, name='index'),
    
    path('catalog/', views.catalog_view, name='catalog'),
    path('catalog/<slug:main_category_slug>/', views.catalog_view, name='catalog_by_main_category'),
    path('catalog/<slug:main_category_slug>/<slug:category_slug>/', views.catalog_view, name='catalog_by_category'),
    path('product/<int:id>/<slug:slug>/', views.product_detail, name='product_detail'),
    
    path('cart/', views.cart_detail, name='cart_detail'),
    path('cart/<str:operation>/<int:product_id>/', views.cart_operations, name='cart_operations'),
    
    path('checkout/', views.checkout, name='checkout'),
    path('order_success/', views.order_success, name='order_success'),
    path('order/<int:order_id>/', views.order_confirmation, name='order_confirmation'),
    
    path('account/', views.account, name='account'),
    
    path('about/', views.about, name='about'),
    path('delivery/', views.delivery, name='delivery'),
    path('contacts/', views.contacts, name='contacts'),
    
    path('crm/<str:template>/', views.crm_view, name='crm_view'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
