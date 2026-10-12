"""Authenticated chat persistence. Browser IDs never determine ownership."""
import re
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import Http404
from .models import ChatConversation, ChatMessage

CHAT_ID_PATTERN = re.compile(r"(?:chat|gen|sep)_[a-zA-Z0-9_-]{1,100}\Z")


def validate_id(value):
    value = str(value or "").strip()
    if not CHAT_ID_PATTERN.fullmatch(value):
        raise ValueError("Invalid chat identifier")
    return value


def app_for_id(chat_id):
    return "general" if chat_id.startswith("gen_") else "ticketing"


def owned_chat(user, chat_id, application=None, create=False):
    """Never disclose, read, or take over a chat owned by someone else."""
    chat_id = validate_id(chat_id)
    existing = ChatConversation.objects.filter(chat_id=chat_id).first()
    if existing:
        if existing.user_id != user.pk:
            raise Http404("Chat not found")
        if application and existing.application != application:
            raise ValueError("Chat belongs to another application")
        return existing
    if not create:
        return None
    application = application or app_for_id(chat_id)
    if application not in ("general", "ticketing"):
        raise ValueError("Unsupported application")
    # Validate prefix if present, prevent routing general ID to SEP.
    if chat_id.startswith('gen_') and application != 'general':
        raise ValueError('Chat and application mismatch')
    if chat_id.startswith('sep_') and application != 'ticketing':
        raise ValueError('Chat and application mismatch')
    return ChatConversation.objects.create(user=user, chat_id=chat_id, application=application)


def log_turns(conversation, user_message, result):
    answer = str(result.get('message') or '')[:30000]
    message = str(user_message)[:30000]
    ChatMessage.objects.bulk_create([
        ChatMessage(conversation=conversation, role='user', content=message),
        ChatMessage(conversation=conversation, role='assistant', content=answer,
                    response_type=str(result.get('type') or '')[:48]),
    ])
    # Auto-update timestamp even when only messages are changing
    conversation.save(update_fields=['updated_at'])


def list_chats(user):
    return [serialize(c) for c in ChatConversation.objects.filter(user=user)]


def serialize(chat):
    return dict(id=chat.chat_id, application=chat.application, title=chat.title,
                pinned=chat.pinned, html=chat.rendered_html,
                createdAt=chat.created_at.isoformat(), updatedAt=chat.updated_at.isoformat())
