from django.db import migrations, models
import django.db.models.deletion


def ensure_demande_livraison_field(apps, schema_editor):
    model = apps.get_model('avis_app', 'AvisLivreur')
    field = models.OneToOneField(
        db_column='commande_id',
        on_delete=django.db.models.deletion.CASCADE,
        related_name='avis',
        to=apps.get_model('demande_livraison_app', 'DemandeLivraison'),
    )
    field.set_attributes_from_name('demande_livraison')
    field.model = model

    with schema_editor.connection.cursor() as cursor:
        columns = {
            column.name
            for column in schema_editor.connection.introspection.get_table_description(
                cursor,
                model._meta.db_table,
            )
        }
    if field.column not in columns:
        schema_editor.add_field(model, field)


class Migration(migrations.Migration):

    dependencies = [
        ('avis_app', '0001_initial'),
        ('demande_livraison_app', '0001_initial'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(ensure_demande_livraison_field),
            ],
            state_operations=[
                migrations.AddField(
                    model_name='avislivreur',
                    name='demande_livraison',
                    field=models.OneToOneField(
                        db_column='commande_id',
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='avis',
                        to='demande_livraison_app.demandelivraison',
                    ),
                ),
            ],
        ),
    ]
