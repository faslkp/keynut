from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

# class CustomAccountAdapter(DefaultAccountAdapter):
#     def save_user(self, request, user, form, commit=True):
#         user = super().save_user(request, user, form, commit=False)
#         # Use the email as username, truncated to 150 characters
#         user.username = user.email[:150]
#         if commit:
#             user.save()
#         return user

class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form)
        # Use the email as username, truncated to 150 characters
        user.username = user.email[:150]
        user.save()
        return user