import re

from django.db import models


# Match "motorpool", "motorpool-transport", "GSO Motorpool", but not hyphenated negation forms like "non-motorpool".
_CODE_MOTORPOOL_PREFIX = 'motorpool'
_NAME_MOTORPOOL_RE = re.compile(r'(?<![\w-])motorpool(?![\w-])', re.IGNORECASE)


class Unit(models.Model):
    """GSO units: Repair & Maintenance, Utility, Electrical, Motorpool."""
    name = models.CharField(max_length=120)
    code = models.SlugField(max_length=50, unique=True, help_text="Short code, e.g. repair, utility")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    @property
    def is_motorpool(self):
        """True when this unit uses motorpool trip-ticket flows (slug or display name variants)."""
        code = ((self.code or '').strip().lower().replace('_', '-'))
        if code.startswith(_CODE_MOTORPOOL_PREFIX):
            return True
        name = (self.name or '').strip()
        if not name:
            return False
        return bool(_NAME_MOTORPOOL_RE.search(name))

    def __str__(self):
        return self.name
