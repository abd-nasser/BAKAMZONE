# Generated manually to handle unique uuid and defaults cleanly
import uuid
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('clients_app', '0001_initial'),
        ('demande_livraison_app', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='demandelivraison',
            name='date_acceptation',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='demandelivraison',
            name='latitude_destinataire_reelle',
            field=models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True),
        ),
        migrations.AddField(
            model_name='demandelivraison',
            name='longitude_destinataire_reelle',
            field=models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True),
        ),
        migrations.AddField(
            model_name='demandelivraison',
            name='position_destinataire_validee',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='demandelivraison',
            name='statut_destinataire',
            field=models.CharField(
                choices=[
                    ('en_attente', 'En attente de réponse (Lien PWA envoyé)'),
                    ('position_recue', 'Position reçue du destinataire'),
                    ('alerte_assistant', 'Signalé à l’assistant (Délai 3min dépassé)'),
                    ('injoignable', 'Injoignable / Échec'),
                ],
                default='en_attente',
                max_length=30,
            ),
        ),
        migrations.AddField(
            model_name='demandelivraison',
            name='whatsapp_destinataire',
            field=models.CharField(
                default='',
                help_text='Numéro WhatsApp pour le lien de géolocalisation',
                max_length=20,
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='demandelivraison',
            name='token_pwa_destinataire',
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
        migrations.AlterField(
            model_name='demandelivraison',
            name='client',
            field=models.ForeignKey(
                help_text="Le client ou l'entreprise qui initie la livraison",
                on_delete=django.db.models.deletion.PROTECT,
                related_name='demandes_livraison',
                to='clients_app.client',
            ),
        ),
        migrations.AlterField(
            model_name='demandelivraison',
            name='latitude_arrivee',
            field=models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True),
        ),
        migrations.AlterField(
            model_name='demandelivraison',
            name='longitude_arrivee',
            field=models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True),
        ),
        migrations.AlterField(
            model_name='demandelivraison',
            name='statut',
            field=models.CharField(
                choices=[
                    ('en_attente', 'En attente de livreur'),
                    ('acceptee', 'Acceptée par le livreur'),
                    ('en_cours', 'En cours de livraison'),
                    ('livree', 'Livrée'),
                    ('annulee', 'Annulée'),
                ],
                default='en_attente',
                max_length=20,
            ),
        ),
        migrations.AddIndex(
            model_name='demandelivraison',
            index=models.Index(fields=['token_pwa_destinataire'], name='idx_token_pwa'),
        ),
    ]
