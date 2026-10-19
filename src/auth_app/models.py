from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin

class UserManager(BaseUserManager):
    def create_user(self, telephone, password=None, **extra_field):
        if not telephone:
            raise ValueError("Le numéro de téléphone est obligatoire.")
        
        user = self.model(telephone=telephone, **extra_field)
        user.set_password(password)
        user.save(using=self.db)
        return user
    
    def create_superuser(self, telephone,  password=None, **extra_fields):
        #1. on force les permission du superuser
        extra_fields.setdefault('is_staff', True),
        extra_fields.setdefault('is_superuser', True),
        extra_fields.setdefault('is_active', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Le superuser doit avoir is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Le superuser doit avoir is_superuser=True.')
        
        #2. On appelle create_user avec telephone
        return self.create_user(telephone, password ,extra_fields)
    

class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = [
        ('client', 'Client'),
        ('livreur', 'Livreur'),
        ('administrateur', 'administrateur'),
        ('entreprise', 'Entreprise')
    ]
    
    username = models.CharField(max_length=30, unique=True, null=True, blank=True)
    telephone = models.CharField(max_length=20, unique=True)
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    email = models.EmailField(blank=True, null=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='client')

    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    objects = UserManager()

    # Indique à Django quel champ sert d'identifiant unique
    USERNAME_FIELD = 'telephone'
    
    # Champs demandés lors de la commande python manage.py createsuperuser
    REQUIRED_FIELDS = ['first_name', 'last_name']
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"

    def __str__(self):
        return f"{self.get_full_name()} ({self.telephone})"
    