import threading

class LLMCancelled(Exception):
    """Raised when the user stops an active LLM request."""
    pass

# Stores cancellation signals for currently running chats.
_active_requests = {}

# Protects the dictionary because Django can process
# chat and stop requests on different threads.
_lock = threading.Lock()


def register_request(chat_id):

    if not chat_id:
        return None

    cancel_event = threading.Event()

    with _lock:
        _active_requests[chat_id] = cancel_event

    return cancel_event


def get_request(chat_id):

    if not chat_id:
        return None

    with _lock:
        return _active_requests.get(chat_id)


def cancel_request(chat_id):

    if not chat_id:
        return False

    with _lock:
        cancel_event = _active_requests.get(chat_id)

    if not cancel_event:
        return False

    cancel_event.set()

    return True


def unregister_request(chat_id, cancel_event=None):
    if not chat_id:
        return

    with _lock:
        current_event = _active_requests.get(chat_id)

        # Only remove the request that is actually finishing.
        # Do not accidentally remove a newer request for the same chat.
        if (
            cancel_event is None
            or current_event is cancel_event
        ):
            _active_requests.pop(chat_id, None)