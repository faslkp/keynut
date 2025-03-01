from django.db import models
from django.contrib.auth.models import AbstractUser

class Customer(AbstractUser):
    phone = models.CharField(max_length=15)
    is_blocked = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return self.username