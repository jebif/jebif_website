from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('jebif_users', '0009_alter_userinfo_know_from'),
    ]

    operations = [
        migrations.CreateModel(
            name='MailSignature',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True, verbose_name='Nom')),
                ('text', models.TextField(verbose_name='Signature')),
                ('is_active', models.BooleanField(default=True, verbose_name='Active')),
                ('created', models.DateTimeField(auto_now_add=True, verbose_name='Créée le')),
                ('updated', models.DateTimeField(auto_now=True, verbose_name='Modifiée le')),
            ],
            options={
                'verbose_name': 'Signature de mail',
                'verbose_name_plural': 'Signatures de mail',
                'ordering': ['name'],
            },
        ),
    ]
