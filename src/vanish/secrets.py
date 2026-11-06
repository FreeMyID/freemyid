"""Mailbox passwords: OS keychain only. OWNER: orchestrator."""
from __future__ import annotations

import keyring

from .models import MailboxConfig


def _user(profile_id: str, mb: MailboxConfig) -> str:
    return f"{profile_id}:{mb.address}"


def set_mailbox_password(profile_id: str, mb: MailboxConfig, password: str) -> None:
    keyring.set_password(mb.keyring_service, _user(profile_id, mb), password)


def get_mailbox_password(profile_id: str, mb: MailboxConfig) -> str | None:
    return keyring.get_password(mb.keyring_service, _user(profile_id, mb))


def delete_mailbox_password(profile_id: str, mb: MailboxConfig) -> None:
    try:
        keyring.delete_password(mb.keyring_service, _user(profile_id, mb))
    except keyring.errors.PasswordDeleteError:
        pass
