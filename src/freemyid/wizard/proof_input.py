"""Optional proof the person adds when they mark a hand step done: a short note about a phone
call (PHONE_CALL_NOTE) or a photo/scan of a mailing receipt (POSTAL_RECEIPT). Stored encrypted
through Store.save_evidence like all other evidence. Nothing here blocks a to-do on its own:
the caller decides what to do with the error text."""
from __future__ import annotations

import logging

from ..models import EvidenceKind, Todo, TodoKind, utcnow
from ..storage import Store
from ..submitters import base

log = logging.getLogger(__name__)

MAX_NOTE_CHARS = 1000
MAX_RECEIPT_BYTES = 10 * 1024 * 1024
BAD_RECEIPT = "That file can't be used. Please attach a PDF, JPG or PNG up to 10 MB."


def sniff(data: bytes) -> str | None:
    """File extension from the first bytes (the browser's file name and type are not trusted)."""
    if data.startswith(b"%PDF-"):
        return "pdf"
    if data.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    return None


def wants_note(t: Todo) -> bool:
    return t.kind == TodoKind.PHONE_CALL


def wants_receipt(t: Todo) -> bool:
    return t.kind == TodoKind.POSTAL_LETTER


def check_receipt(data: bytes) -> str | None:
    """Error text, or None when the file is acceptable."""
    if len(data) > MAX_RECEIPT_BYTES or sniff(data) is None:
        return BAD_RECEIPT
    return None


def save_call_note(store: Store, t: Todo, note: str) -> bool:
    note = " ".join(note.split())[:MAX_NOTE_CHARS]
    if not note or not t.broker_id:
        return False
    text = (f"Note about the phone call, written by the person on "
            f"{utcnow().isoformat(timespec='seconds')}.\n\nTheir note: {note}\n\n"
            f"What Free My ID asked them to do:\n{t.title}\n{t.body}\n")
    ev = base.evidence(t.profile_id, t.broker_id, EvidenceKind.PHONE_CALL_NOTE, "txt",
                       request_id=t.request_id, caption="your note about the call")
    store.save_evidence(ev, text.encode())
    return True


def save_receipt(store: Store, t: Todo, data: bytes) -> bool:
    ext = sniff(data)
    if ext is None or not t.broker_id or len(data) > MAX_RECEIPT_BYTES:
        return False
    ev = base.evidence(t.profile_id, t.broker_id, EvidenceKind.POSTAL_RECEIPT, ext,
                       request_id=t.request_id, caption="mailing receipt you attached")
    store.save_evidence(ev, data)
    return True
