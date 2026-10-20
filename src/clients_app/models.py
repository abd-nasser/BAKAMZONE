from django.db import models


class Client(models.Model):
    user = models.OneToOneField('auth_app.User', on_delete=models.CASCADE, related_name='client_profil')
    photo_profil = models.ImageField(upload_to='client_photos/', blank=True, null=True)
    ville = models.CharField(max_length=100, blank=True, null=True)
    quartier = models.CharField(max_length=100, blank=True, null=True)
    
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    
    # Ajoutez d'autres champs spécifiques au client si nécessaire
    
    @property
    def google_maps_url(self):
        """Raccourci pour le DG / Commercial afin d'ouvrir le lieu directement dans Google Maps"""
        if self.latitude and self.longitude:
            return f"https://www.google.com/maps?q={self.latitude},{self.longitude}"
        return None
    def __str__(self):
        return f"Client: {self.user.username}"
