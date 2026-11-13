"""Registers the `scale` marker for the registry-at-scale budgets (roadmap 0.7).

They run in the normal suite (CI included). Deselect locally with `-m "not scale"`.
"""
from __future__ import annotations


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "scale: registry-at-scale time budgets on synthetic 1,000/2,000-broker "
                   "registries (CR: register in pyproject.toml)")
