from django.conf import settings
from django.db import models


class RememberedAccount(models.Model):
    """Opt-in device login credential. Only its SHA-256 digest is persisted."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="darpan_remembered_accounts")
    token_hash = models.CharField(max_length=64, unique=True, db_index=True)
    auth_hash = models.CharField(max_length=128)  # invalidated by password change
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(db_index=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Remembered account {self.user_id} ({self.pk})"
