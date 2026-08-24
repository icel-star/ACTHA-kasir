from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models.functions import Lower


class Product(models.Model):
    name = models.CharField(max_length=120, unique=True)
    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(Decimal('9999999999.99'))],
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(Lower('name'), name='unique_product_name_ci'),
        ]

    def __str__(self):
        return self.name


class Sale(models.Model):
    PAYMENT_CASH = 'cash'
    PAYMENT_QR = 'qr'
    PAYMENT_TRANSFER = 'transfer'
    PAYMENT_CANCELLED = 'cancelled'
    PAYMENT_CHOICES = [
        (PAYMENT_CASH, 'Cash'),
        (PAYMENT_QR, 'QR'),
        (PAYMENT_TRANSFER, 'Transfer'),
        (PAYMENT_CANCELLED, 'Dibatalkan'),
    ]

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_CHOICES, default=PAYMENT_CASH)
    edited_at = models.DateTimeField(null=True, blank=True, editable=False)
    deleted_at = models.DateTimeField(null=True, blank=True, editable=False)

    class Meta:
        ordering = ['-created_at', '-id']

    def __str__(self):
        return f'Transaksi #{self.pk}'


class SaleItem(models.Model):
    sale = models.ForeignKey(Sale, related_name='items', on_delete=models.PROTECT)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    product_name = models.CharField(max_length=120)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    quantity = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(999999)],
    )

    @property
    def subtotal(self):
        return self.unit_price * self.quantity
