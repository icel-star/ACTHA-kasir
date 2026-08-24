from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):
    dependencies = [
        ('kasir', '0005_sale_deleted_at_sale_edited_at_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='saleitem',
            name='quantity',
            field=models.PositiveIntegerField(
                validators=[
                    django.core.validators.MinValueValidator(1),
                    django.core.validators.MaxValueValidator(999999),
                ],
            ),
        ),
    ]