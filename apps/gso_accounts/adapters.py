from allauth.exceptions import ImmediateHttpResponse
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.shortcuts import redirect


class GSOSocialAccountAdapter(DefaultSocialAccountAdapter):
    """Allow Google sign-in only when email matches an existing active account."""

    def pre_social_login(self, request, sociallogin):
        # Existing linked social account -> proceed normally.
        if sociallogin.is_existing:
            return

        email = (getattr(sociallogin.user, 'email', '') or '').strip().lower()
        if not email:
            messages.error(request, 'Google account has no email. Contact administrator.')
            raise ImmediateHttpResponse(redirect('gso_accounts:login'))

        UserModel = get_user_model()
        matched_user = UserModel.objects.filter(email__iexact=email, is_active=True).first()
        if not matched_user:
            messages.error(
                request,
                'No existing account matches this Google email. Ask admin to create your account first.',
            )
            raise ImmediateHttpResponse(redirect('gso_accounts:login'))

        # Link this Google account to the matched existing user.
        sociallogin.connect(request, matched_user)
