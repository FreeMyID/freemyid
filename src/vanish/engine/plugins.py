"""Submitter lookup (order from interfaces.Submitter):

1. broker.submitter 'vanish.submitters.<module>:<Class>' (namespace enforced by the model)
2. entry point group 'vanish.submitters' keyed by broker id
3. module vanish.submitters.<broker_id> with a class named `Submitter`
4. generic by tier: AUTOMATIC -> WebFormSubmitter, EMAIL -> EmailSubmitter,
   ASSISTED -> AssistedSubmitter

v1 ships no per-broker modules (PLAN_V1 D1). Steps 1-3 stay for later exceptions.
"""
from __future__ import annotations

import importlib
import logging
from importlib.metadata import entry_points

from ..interfaces import Submitter
from ..models import Broker, Tier

log = logging.getLogger(__name__)

_GENERIC_NAMES = {"base", "assisted", "email", "web_form"}


def _instantiate(obj: object) -> Submitter | None:
    if isinstance(obj, type) and issubclass(obj, Submitter):
        return obj()
    return None


def custom_submitter(broker: Broker) -> Submitter | None:
    if broker.submitter:
        mod, _, cls = broker.submitter.partition(":")
        try:
            return _instantiate(getattr(importlib.import_module(mod), cls))
        except (ImportError, AttributeError) as e:
            log.warning("custom submitter for %s unavailable: %s", broker.id, type(e).__name__)
    try:
        for ep in entry_points(group="vanish.submitters"):
            if ep.name == broker.id:
                return _instantiate(ep.load())
    except Exception as e:  # noqa: BLE001 - a broken plugin must not stop the run
        log.warning("entry point for %s failed: %s", broker.id, type(e).__name__)
    if broker.id not in _GENERIC_NAMES:
        try:
            mod = importlib.import_module(f"vanish.submitters.{broker.id}")
            return _instantiate(getattr(mod, "Submitter", None))
        except ImportError:
            pass
    return None


def generic_submitter(tier: Tier) -> Submitter:
    if tier == Tier.AUTOMATIC:
        from ..submitters.web_form import WebFormSubmitter
        return WebFormSubmitter()
    if tier == Tier.EMAIL:
        from ..submitters.email import EmailSubmitter
        return EmailSubmitter()
    from ..submitters.assisted import AssistedSubmitter
    return AssistedSubmitter()


def get_submitter(broker: Broker, tier: Tier) -> Submitter:
    """Custom submitters only apply to the Automatic tier; others use the generic path."""
    if tier == Tier.AUTOMATIC and (custom := custom_submitter(broker)):
        return custom
    return generic_submitter(tier)
