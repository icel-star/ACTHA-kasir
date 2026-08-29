from django.urls import path

from . import views

urlpatterns = [
    path('', views.cashier, name='cashier'),
    path('admin/login/', views.admin_login, name='admin_login'),
    path('admin/logout/', views.admin_logout, name='admin_logout'),
    path('transaksi/simpan/', views.create_sale, name='create_sale'),
    path('produk/', views.products, name='products'),
    path('produk/tambah/', views.save_product, name='add_product'),
    path('produk/<int:product_id>/edit/', views.save_product, name='edit_product'),
    path('produk/<int:product_id>/hapus/', views.delete_product, name='delete_product'),
    path('riwayat/', views.sales_history, name='sales_history'),
    path('riwayat/<int:sale_id>/', views.transaction_detail, name='transaction_detail'),
    path('riwayat/<int:sale_id>/edit/', views.edit_transaction, name='edit_transaction'),
    path('riwayat/<int:sale_id>/hapus/', views.delete_transaction, name='delete_transaction'),
    path('riwayat/export/', views.export_riwayat_excel, name='export_riwayat_excel'),
]
