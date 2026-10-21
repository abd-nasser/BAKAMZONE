from django.db import models
class Zone(models.Model):
    """
    Représente une zone géographique spécifique dans laquelle les livreurs peuvent opérer.
    Chaque zone est associée à un bloc de quartier et peut avoir des livreurs assignés.
    """

    nom = models.CharField(max_length=150, unique=True, verbose_name="Nom de la zone")
    code = models.CharField(max_length=30, unique=True, blank=True, null=True, verbose_name="Code unique")

    bloc = models.ForeignKey('blocs_app.Blocs', on_delete=models.CASCADE, related_name='zones', verbose_name="Bloc associé")

    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    def __str__(self):
        return self.nom
