from datetime import datetime

from django.test import TestCase
from django.urls import reverse

from .models import Product, Sale, SaleItem


class CashierFlowTests(TestCase):
    def setUp(self):
        self.product = Product.objects.create(name='Kopi susu', price='18000')

    def test_admin_can_login_with_hardcoded_credentials(self):
        response = self.client.post(reverse('admin_login'), {'username': 'admin', 'password': '777'})

        self.assertRedirects(response, reverse('cashier'))
        self.assertTrue(self.client.session['is_admin'])
        self.assertContains(self.client.get(reverse('cashier')), 'Admin aktif')
        self.assertContains(self.client.get(reverse('cashier')), 'Keluar admin')

    def test_admin_rejects_invalid_credentials_and_can_logout(self):
        response = self.client.post(reverse('admin_login'), {'username': 'Admin', 'password': '777'}, follow=True)

        self.assertContains(response, 'Username atau password admin salah.')
        self.client.post(reverse('admin_login'), {'username': 'admin', 'password': '777'})
        self.client.post(reverse('admin_logout'))
        self.assertNotIn('is_admin', self.client.session)
        self.assertContains(self.client.get(reverse('cashier')), 'Login sebagai admin')

    def test_checkout_saves_snapshot_and_second_precision_timestamp(self):
        response = self.client.post(reverse('create_sale'), {f'quantity_{self.product.id}': '2', 'payment_method': 'cash'})

        self.assertRedirects(response, reverse('cashier'))
        sale = Sale.objects.get()
        item = SaleItem.objects.get(sale=sale)
        self.assertEqual(sale.total, 36000)
        self.assertEqual(item.product_name, 'Kopi susu')
        self.assertEqual(item.unit_price, 18000)
        self.assertEqual(sale.payment_method, 'cash')
        self.assertIsInstance(sale.created_at, datetime)

    def test_transaction_has_no_edit_or_delete_route(self):
        sale = Sale.objects.create(total='18000')

        self.assertEqual(self.client.get(f'/transaksi/{sale.id}/edit/').status_code, 404)
        self.assertEqual(self.client.post(f'/transaksi/{sale.id}/hapus/').status_code, 404)

    def test_transaction_detail_page_shows_items(self):
        sale = Sale.objects.create(total='36000', payment_method='qr')
        SaleItem.objects.create(
            sale=sale, product=self.product, product_name=self.product.name,
            unit_price=self.product.price, quantity=2,
        )

        response = self.client.get(reverse('transaction_detail', args=[sale.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Kopi susu')
        self.assertContains(response, 'QR')

    def test_admin_can_edit_transaction_only_when_values_change(self):
        sale = Sale.objects.create(total='36000', payment_method='cash')
        item = SaleItem.objects.create(
            sale=sale, product=self.product, product_name=self.product.name,
            unit_price=self.product.price, quantity=2,
        )
        self.client.post(reverse('admin_login'), {'username': 'admin', 'password': '777'})

        unchanged = self.client.post(
            reverse('edit_transaction', args=[sale.id]),
            {'payment_method': 'cash', f'quantity_{item.id}': '2'}, follow=True,
        )
        self.assertContains(unchanged, 'Belum ada perubahan pada transaksi.')
        changed = self.client.post(
            reverse('edit_transaction', args=[sale.id]),
            {'payment_method': 'transfer', f'quantity_{item.id}': '3'},
        )
        self.assertRedirects(changed, reverse('transaction_detail', args=[sale.id]))
        sale.refresh_from_db(); item.refresh_from_db()
        self.assertEqual(sale.payment_method, 'transfer')
        self.assertEqual(item.quantity, 3)
        self.assertIsNotNone(sale.edited_at)

    def test_admin_delete_transaction_keeps_history_and_marks_payment_cancelled(self):
        sale = Sale.objects.create(total='18000', payment_method='cash')
        self.client.post(reverse('admin_login'), {'username': 'admin', 'password': '777'})

        response = self.client.post(reverse('delete_transaction', args=[sale.id]))

        self.assertRedirects(response, reverse('sales_history'))
        sale.refresh_from_db()
        self.assertEqual(sale.payment_method, Sale.PAYMENT_CANCELLED)
        self.assertIsNotNone(sale.deleted_at)
        self.assertTrue(Sale.objects.filter(pk=sale.id).exists())

    def test_product_edit_updates_name_and_price(self):
        response = self.client.post(
            reverse('edit_product', args=[self.product.id]),
            {'name': 'Kopi gula aren', 'price': '22000'},
        )

        self.assertRedirects(response, reverse('products'))
        self.product.refresh_from_db()
        self.assertEqual(self.product.name, 'Kopi gula aren')
        self.assertEqual(self.product.price, 22000)

    def test_product_name_is_case_insensitive(self):
        response = self.client.post(
            reverse('add_product'),
            {'name': 'KOPI SUSU', 'price': '20000'},
        )

        self.assertRedirects(response, reverse('products'))
        self.assertEqual(Product.objects.filter(name__iexact='kopi susu').count(), 1)
        self.assertEqual(Product.objects.get(pk=self.product.id).price, 18000)

    def test_product_price_over_limit_shows_specific_message(self):
        response = self.client.post(
            reverse('edit_product', args=[self.product.id]),
            {'name': self.product.name, 'price': '10000000000'},
            follow=True,
        )

        self.assertContains(response, 'Harga maksimal adalah Rp 9.999.999.999,99.')
        self.product.refresh_from_db()
        self.assertEqual(self.product.price, 18000)

    def test_transaction_quantity_over_limit_shows_message(self):
        sale = Sale.objects.create(total='18000', payment_method='cash')
        item = SaleItem.objects.create(
            sale=sale, product=self.product, product_name=self.product.name,
            unit_price=self.product.price, quantity=1,
        )
        self.client.post(reverse('admin_login'), {'username': 'admin', 'password': '777'})

        response = self.client.post(
            reverse('edit_transaction', args=[sale.id]),
            {'payment_method': 'cash', f'quantity_{item.id}': '999999999999999999999'},
            follow=True,
        )

        self.assertContains(response, 'Jumlah maksimal per produk adalah 999.999.')
        item.refresh_from_db()
        self.assertEqual(item.quantity, 1)