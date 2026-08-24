from decimal import Decimal

from django.db import migrations, models
import django.core.validators


MAX_PRODUCT_PRICE = Decimal('9999999999.99')


def repair_product_prices(apps, schema_editor):
    Product = apps.get_model('kasir', 'Product')
    Product.objects.filter(price__gt=MAX_PRODUCT_PRICE).update(price=MAX_PRODUCT_PRICE)
    Product.objects.filter(price__lt=0).update(price=Decimal('0'))


class Migration(migrations.Migration):
    dependencies = [
        ('kasir', '0002_product_unique_product_name_ci'),
    ]

    operations = [
        migrations.RunPython(repair_product_prices, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='product',
            name='price',
            field=models.DecimalField(
                decimal_places=2,
                max_digits=12,
                validators=[
                    django.core.validators.MinValueValidator(0),
                    django.core.validators.MaxValueValidator(Decimal('9999999999.99')),
                ],
            ),
        ),
    ]