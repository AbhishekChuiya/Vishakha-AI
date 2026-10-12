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


class ChatConversation(models.Model):
    """Owned, application-scoped chat metadata and last rendered snapshot."""
    APPLICATIONS = (("general", "General"), ("ticketing", "Service Excellence Portal"))
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="vishakha_conversations")
    chat_id = models.CharField(max_length=105, unique=True)
    application = models.CharField(max_length=24, choices=APPLICATIONS)
    title = models.CharField(max_length=160, default="New Chat")
    pinned = models.BooleanField(default=False)
    rendered_html = models.TextField(blank=True, default="")
    workflow_state = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        ordering = ["-updated_at"]
        indexes = [models.Index(fields=["user", "application", "-updated_at"],
                                name="vish_chat_user_app_idx")]


class ChatMessage(models.Model):
    """Durable server-recorded user and assistant turns."""
    conversation = models.ForeignKey(ChatConversation, on_delete=models.CASCADE,
                                     related_name="messages")
    role = models.CharField(max_length=12, choices=(("user", "User"), ("assistant", "Assistant")))
    content = models.TextField()
    response_type = models.CharField(max_length=48, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]
        indexes = [models.Index(fields=["conversation", "id"], name="vish_chat_msg_seq_idx")]
