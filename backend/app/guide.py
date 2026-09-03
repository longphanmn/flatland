"""Living guide — merged into app.wiki.

All guide features, markdown tables, and schemas are now maintained in app.wiki.
This module re-exports them for backward compatibility.
"""

from __future__ import annotations

from typing import Any

from .wiki import (
    _api_table,
    _god_laws_table,
    _md_to_html,
    CODEBASE_MAP_MD,
    CONFIG_OPS_MD,
    DATA_MODEL_MD,
    HOW_IT_WORKS_MD,
    build_wiki_html,
    get_wiki_json,
)

# Backward-compatibility alias
def build_guide_html(app: Any) -> str:
    """Merged with build_wiki_html."""
    return build_wiki_html(app, lang="en")


__all__ = [
    "_md_to_html",
    "_god_laws_table",
    "_api_table",
    "HOW_IT_WORKS_MD",
    "CODEBASE_MAP_MD",
    "DATA_MODEL_MD",
    "CONFIG_OPS_MD",
    "build_wiki_html",
    "build_guide_html",
    "get_wiki_json",
]
