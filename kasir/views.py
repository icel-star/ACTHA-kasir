from django.http import HttpResponse
import openpyxl
from django.utils.timezone import localtime
from decimal import Decimal, InvalidOperation
from secrets import compare_digest

from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .models import Product, Sale, SaleItem

MAX_PRODUCT_PRICE = Decimal('9999999999.99')
MAX_SALE_QUANTITY = 999999
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = '777'


def admin_required(request):
    if not request.session.get('is_admin'):
        messages.error(request, 'Login sebagai admin diperlukan untuk tindakan ini.')
        return redirect('admin_login')
    return None


def cashier(request):
    products = Product.objects.all()
    return render(request, 'kasir/cashier.html', {'products': products})


@require_http_methods(['GET', 'POST'])
def admin_login(request):
    if request.method == 'POST':
        username = request.POST.get('username', '')
        password = request.POST.get('password', '')
        if compare_digest(username, ADMIN_USERNAME) and compare_digest(password, ADMIN_PASSWORD):
            request.session['is_admin'] = True
            messages.success(request, 'Berhasil login sebagai admin.')
            return redirect('cashier')
        messages.error(request, 'Username atau password admin salah.')
    return render(request, 'kasir/admin_login.html')


@require_http_methods(['POST'])
def admin_logout(request):
    request.session.pop('is_admin', None)
    messages.success(request, 'Berhasil logout dari akun admin.')
    return redirect('cashier')


@require_http_methods(['POST'])
def create_sale(request):
    payment_method = request.POST.get('payment_method', '')
    valid_payment_methods = {choice[0] for choice in Sale.PAYMENT_CHOICES if choice[0] != Sale.PAYMENT_CANCELLED}
    if payment_method not in valid_payment_methods:
        messages.error(request, 'Pilih metode pembayaran terlebih dahulu.')
        return redirect('cashier')

    quantities = {}
    for key, value in request.POST.items():
        if not key.startswith('quantity_'):
            continue
        try:
            product_id = int(key.removeprefix('quantity_'))
            quantity = int(value)
        except (TypeError, ValueError):
            continue
        if quantity > MAX_SALE_QUANTITY:
            messages.error(request, 'Jumlah maksimal per produk adalah 999.999.')
            return redirect('cashier')
        if quantity > 0:
            quantities[product_id] = quantity

    products = Product.objects.filter(id__in=quantities)
    if not quantities or products.count() != len(quantities):
        messages.error(request, 'Pilih minimal satu produk dengan jumlah yang valid.')
        return redirect('cashier')

    total = sum((product.price * quantities[product.id] for product in products), Decimal('0'))
    if total > MAX_PRODUCT_PRICE:
        messages.error(request, 'Total transaksi melebihi batas maksimal Rp 9.999.999.999,99.')
        return redirect('cashier')

    with transaction.atomic():
        sale = Sale.objects.create(payment_method=payment_method)
        for product in products:
            quantity = quantities[product.id]
            SaleItem.objects.create(
                sale=sale,
                product=product,
                product_name=product.name,
                unit_price=product.price,
                quantity=quantity,
            )
        sale.total = total
        sale.save(update_fields=['total'])

    messages.success(request, f'Transaksi #{sale.id} berhasil disimpan.')
    return redirect('cashier')


def products(request):
    return render(request, 'kasir/products.html', {'products': Product.objects.all()})


@require_http_methods(['POST'])
def save_product(request, product_id=None):
    product = get_object_or_404(Product, id=product_id) if product_id else Product()
    name = request.POST.get('name', '').strip()
    raw_price = request.POST.get('price', '').strip().replace(',', '.')
    try:
        price = Decimal(raw_price)
    except InvalidOperation:
        messages.error(request, 'Harga harus berupa angka yang valid.')
        return redirect('products')

    if not name:
        messages.error(request, 'Nama produk wajib diisi.')
        return redirect('products')
    if price < 0:
        messages.error(request, 'Harga tidak boleh kurang dari Rp 0.')
        return redirect('products')
    if price > MAX_PRODUCT_PRICE:
        messages.error(request, 'Harga maksimal adalah Rp 9.999.999.999,99.')
        return redirect('products')
    if Product.objects.filter(name__iexact=name).exclude(pk=product.pk).exists():
        messages.error(request, 'Nama produk sudah digunakan, tanpa membedakan huruf besar-kecil.')
        return redirect('products')
    product.name = name
    product.price = price
    try:
        product.save()
    except Exception:
        messages.error(request, 'Produk gagal disimpan. Pastikan nama produk belum digunakan.')
    else:
        messages.success(request, 'Produk berhasil diperbarui.' if product_id else 'Produk berhasil ditambahkan.')
    return redirect('products')


@require_http_methods(['POST'])
def delete_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    try:
        product.delete()
    except Exception:
        messages.error(request, 'Produk tidak dapat dihapus karena sudah dipakai dalam transaksi.')
    else:
        messages.success(request, 'Produk berhasil dihapus.')
    return redirect('products')


def sales_history(request):
    sales = Sale.objects.prefetch_related('items').all()
    total_penjualan_sah = sum(sale.total for sale in sales if not sale.deleted_at)
    return render(request, 'kasir/sales_history.html', {'sales': sales, 'total_penjualan_sah': total_penjualan_sah,})


def transaction_detail(request, sale_id):
    sale = get_object_or_404(Sale.objects.prefetch_related('items'), id=sale_id)
    return render(request, 'kasir/transaction_detail.html', {'sale': sale})


@require_http_methods(['POST'])
def edit_transaction(request, sale_id):
    access = admin_required(request)
    if access:
        return access
    sale = get_object_or_404(Sale.objects.prefetch_related('items'), id=sale_id)
    if sale.deleted_at:
        messages.error(request, 'Transaksi yang sudah dibatalkan tidak dapat diedit.')
        return redirect('transaction_detail', sale_id=sale.id)

    payment_method = request.POST.get('payment_method', '')
    valid_payment_methods = {choice[0] for choice in Sale.PAYMENT_CHOICES if choice[0] != Sale.PAYMENT_CANCELLED}
    quantities = {}
    for item in sale.items.all():
        try:
            quantity = int(request.POST.get(f'quantity_{item.id}', item.quantity))
            if quantity > MAX_SALE_QUANTITY:
                messages.error(request, 'Jumlah maksimal per produk adalah 999.999.')
                return redirect('transaction_detail', sale_id=sale.id)
            quantities[item.id] = quantity
        except (TypeError, ValueError):
            messages.error(request, 'Jumlah produk harus berupa angka yang valid.')
            return redirect('transaction_detail', sale_id=sale.id)
    if payment_method not in valid_payment_methods or any(quantity < 0 for quantity in quantities.values()):
        messages.error(request, 'Data perubahan transaksi tidak valid.')
        return redirect('transaction_detail', sale_id=sale.id)
    changed = payment_method != sale.payment_method or any(
        quantities[item.id] != item.quantity for item in sale.items.all()
    )
    if not changed:
        messages.error(request, 'Belum ada perubahan pada transaksi.')
        return redirect('transaction_detail', sale_id=sale.id)
    if all(quantity == 0 for quantity in quantities.values()):
        messages.error(request, 'Transaksi harus memiliki minimal satu produk.')
        return redirect('transaction_detail', sale_id=sale.id)
    total = sum((item.unit_price * quantities[item.id] for item in sale.items.all()), Decimal('0'))
    if total > MAX_PRODUCT_PRICE:
        messages.error(request, 'Total transaksi melebihi batas maksimal Rp 9.999.999.999,99.')
        return redirect('transaction_detail', sale_id=sale.id)

    with transaction.atomic():
        for item in sale.items.all():
            quantity = quantities[item.id]
            if quantity == 0:
                item.delete()
                continue
            item.quantity = quantity
            item.save(update_fields=['quantity'])
            total += item.unit_price * quantity
        sale.payment_method = payment_method
        sale.total = total
        sale.edited_at = timezone.now()
        sale.save(update_fields=['payment_method', 'total', 'edited_at'])
    messages.success(request, f'Transaksi #{sale.id} berhasil diedit.')
    return redirect('transaction_detail', sale_id=sale.id)


@require_http_methods(['POST'])
def delete_transaction(request, sale_id):
    access = admin_required(request)
    if access:
        return access
    sale = get_object_or_404(Sale, id=sale_id)
    if sale.deleted_at:
        messages.error(request, 'Transaksi ini sudah dibatalkan.')
        return redirect('transaction_detail', sale_id=sale.id)
    sale.payment_method = Sale.PAYMENT_CANCELLED
    sale.deleted_at = timezone.now()
    sale.save(update_fields=['payment_method', 'deleted_at'])
    messages.success(request, f'Transaksi #{sale.id} berhasil dibatalkan.')
    return redirect('sales_history')

def export_riwayat_excel(request):
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    tanggal_hari_ini = timezone.now().strftime("%d-%m-%Y")
    response['Content-Disposition'] = f'attachment; filename="Riwayat_Transaksi_ACTHA_{tanggal_hari_ini}.xlsx"'

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Riwayat Transaksi"

    headers = ['ID Transaksi', 'Waktu Simpan', 'Metode Pembayaran', 'Status', 'Total (Rp)', 'Detail Produk (Nama - Qty - Subtotal)']
    ws.append(headers)

    sales = Sale.objects.prefetch_related('items').all()
    
    for sale in sales:
        waktu_lokal = localtime(sale.created_at).strftime("%d/%m/%Y %H:%M:%S")
        
        status = "Dibatalkan" if sale.deleted_at else "Sukses"
    
        detail_items = []
        for item in sale.items.all():
            detail_items.append(f"{item.product_name} ({item.quantity}x) - Rp {item.subtotal:,.0f}")
        detail_teks = " | ".join(detail_items)

        row = [
            f"#{sale.id}",
            waktu_lokal,
            sale.get_payment_method_display(),
            status,
            float(sale.total),
            detail_teks
        ]
        ws.append(row)

    wb.save(response)
    return response