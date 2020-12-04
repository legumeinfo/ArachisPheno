# -*- coding: utf-8 -*-
# Generated by Django 1.9.7 on 2016-08-05 12:01
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('phenotypedb', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='PhenotypeCuration',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('field', models.CharField(max_length=255)),
                ('correct', models.BooleanField()),
                ('message', models.TextField(blank=True, null=True)),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('phenotype', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='phenotypedb.Phenotype')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='StudyCuration',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('field', models.CharField(max_length=255)),
                ('correct', models.BooleanField()),
                ('message', models.TextField(blank=True, null=True)),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Submission',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('status', models.PositiveSmallIntegerField(choices=[(0, 'Submitted'), (1, 'Curation'), (2, 'Published')], default=0)),
                ('submission_date', models.DateTimeField(auto_now_add=True)),
                ('update_date', models.DateTimeField(blank=True, null=True)),
            ],
        ),
        migrations.AddField(
            model_name='study',
            name='update_date',
            field=models.DateTimeField(blank=True, default=None, null=True),
        ),
        migrations.AddField(
            model_name='submission',
            name='study',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='phenotypedb.Study'),
        ),
        migrations.AddField(
            model_name='studycuration',
            name='study',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='phenotypedb.Study'),
        ),
    ]