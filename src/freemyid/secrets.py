"""Mailbox passwords, via the selected secrets backend. OWNER: orchestrator.

Keyring backend (default): the OS keychain, as before. Passphrase / systemd-creds backends:
an encrypted file in FREEMYID_HOME (see secret_backends). Never stored in clear text.
"""
from __future__ import annotations

from . import secret_backends
from .models import MailboxConfig


def _user(profile_id: str, mb: MailboxConfig) -> str:
    return f"{profile_id}:{mb.address}"


def set_mailbox_password(profile_id: str, mb: MailboxConfig, password: str) -> None:
    secret_backends.select().set_secret(mb.keyring_service, _user(profile_id, mb), password)


def get_mailbox_password(profile_id: str, mb: MailboxConfig) -> str | None:
    return secret_backends.select().get_secret(mb.keyring_service, _user(profile_id, mb))


def delete_mailbox_password(profile_id: str, mb: MailboxConfig) -> None:
    secret_backends.select().delete_secret(mb.keyring_service, _user(profile_id, mb))
