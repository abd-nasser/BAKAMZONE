import django.db.models.deletion
from django.db import migrations, models


def attach_existing_zones_to_blocks(apps, schema_editor):
    Zone = apps.get_model('zones_app', 'Zone')
    Blocs = apps.get_model('blocs_app', 'Blocs')
    zones = Zone.objects.using(schema_editor.connection.alias)

    for zone in zones.filter(nom__isnull=True).iterator():
        zone.nom = f"Zone historique {zone.pk}"
        zone.save(update_fields=['nom'])

    if zones.filter(bloc__isnull=True).exists():
        bloc, _ = Blocs.objects.using(schema_editor.connection.alias).get_or_create(
            nom='Bloc historique',
        )
        zones.filter(bloc__isnull=True).update(bloc=bloc)


class Migration(migrations.Migration):

    dependencies = [
        ('blocs_app', '0001_initial'),
        ('zones_app', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='zone',
            name='nom',
            field=models.CharField(max_length=150, null=True, verbose_name='Nom de la zone'),
        ),
        migrations.AddField(
            model_name='zone',
            name='code',
            field=models.CharField(blank=True, max_length=30, null=True, verbose_name='Code unique'),
        ),
        migrations.AddField(
            model_name='zone',
            name='bloc',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='zones',
                to='blocs_app.blocs',
                verbose_name='Bloc associé',
            ),
        ),
        migrations.AddField(
            model_name='zone',
            name='latitude',
            field=models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True),
        ),
        migrations.AddField(
            model_name='zone',
            name='longitude',
            field=models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True),
        ),
        migrations.RunPython(
            attach_existing_zones_to_blocks,
            migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name='zone',
            name='nom',
            field=models.CharField(max_length=150, unique=True, verbose_name='Nom de la zone'),
        ),
        migrations.AlterField(
            model_name='zone',
            name='code',
            field=models.CharField(blank=True, max_length=30, null=True, unique=True, verbose_name='Code unique'),
        ),
        migrations.AlterField(
            model_name='zone',
            name='bloc',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='zones',
                to='blocs_app.blocs',
                verbose_name='Bloc associé',
            ),
        ),
    ]
