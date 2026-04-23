from django.db import models


class Unit(models.Model):
    """GSO units: Repair & Maintenance, Utility, Electrical, Motorpool."""
    name = models.CharField(max_length=120)
    code = models.SlugField(max_length=50, unique=True, help_text="Short code, e.g. repair, utility")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name
