import uuid
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model

User = get_user_model()

@receiver(post_save, sender=User)
def generate_referral_key(sender, instance, created, **kwargs):
    """Generate and save referral key for every new user."""
    if created and not instance.referral_key:  # Only for new users
        instance.referral_key = uuid.uuid4()
        instance.save()
