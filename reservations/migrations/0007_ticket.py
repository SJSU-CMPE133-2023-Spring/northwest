# Generated by Django 4.0.5 on 2023-05-06 00:26

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('reservations', '0006_passenger_dob'),
    ]

    operations = [
        migrations.CreateModel(
            name='Ticket',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('total_cost', models.DecimalField(decimal_places=2, max_digits=8)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('paid', models.BooleanField(default=False)),
                ('depart_flight', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='depart', to='reservations.flight')),
                ('passengers', models.ManyToManyField(to='reservations.passenger')),
                ('return_flight', models.ForeignKey(default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='return_ticket', to='reservations.flight')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
