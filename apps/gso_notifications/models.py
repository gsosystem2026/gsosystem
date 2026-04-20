from django.conf import settings
from django.db import models


class Notification(models.Model):
    """In-app notification for requestors and staff (new request, status updates, etc.)."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
    )
    title = models.CharField(max_length=255)
    message = models.TextField(blank=True)
    link = models.CharField(max_length=500, blank=True, help_text='URL to open when notification is clicked')
    read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.user})"


class DeviceToken(models.Model):
    """FCM device token for push notifications. One user can have multiple devices."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='device_tokens',
    )
    token = models.CharField(max_length=500)
    platform = models.CharField(max_length=50, blank=True)  # android, ios, web
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [['user', 'token']]
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.user} ({self.platform})"
