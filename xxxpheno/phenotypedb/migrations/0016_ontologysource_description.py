# -*- coding: utf-8 -*-
# Generated by Django 1.9.7 on 2016-09-13 17:02
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('phenotypedb', '0015_auto_20160912_1401'),
    ]

    operations = [
        migrations.AddField(
            model_name='ontologysource',
            name='description',
            field=models.TextField(null=True),
        ),
    ]