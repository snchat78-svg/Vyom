"""
Project : Vyom AI
Version : 1.0
Module  : Generic Action Schema

Purpose:
    Define the provider-agnostic action protocol used between reasoning
    and execution capabilities.

Safety:
    - Data only. No execution is performed here.
    - No Windows commands, Python callables, or tool objects are stored.
    - Action names are generic identifiers, not a fixed intent list.

Compatibility:
    Existing legacy intents remain outside this protocol and can be
    translated by a compatibility layer when required.
"""

from __future__ import annotations

import copy
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


_IDENTIFIER = re.compile(r"^[a-z][a-z0-9_.:-]{0,63}$")


class ActionSchemaError(ValueError):
    """Raised when an action does not satisfy the structural contract."""


def _json_safe(value: Any, path: str = "value") -> Any:
    """Return a deep-copied JSON-like value or raise on executable objects."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, list):
        return [_json_safe(item, f"{path}[{index}]") for index, item in enumerate(value)]
    if isinstance(value, tuple):
        return [_json_safe(item, f"{path}[{index}]") for index, item in enumerate(value)]
    if isinstance(value, dict):
        clean: Dict[str, Any] = {}
        for key, item in value.items():
            clean[str(key)] = _json_safe(item, f"{path}.{key}")
        return clean
    raise ActionSchemaError(f"{path} contains a non-serializable/executable object.")


def validate_identifier(value: Any, field_name: str) -> str:
    text = str(value or "").strip().lower()
    if not text or not _IDENTIFIER.fullmatch(text):
        raise ActionSchemaError(
            f"'{field_name}' must be a lowercase identifier using letters, numbers, '.', ':', '_' or '-'."
        )
    return text


def normalize_string_list(value: Any, field_name: str) -> List[str]:
    if value is None:
        return []
    if not isinstance(value, (list, tuple)):
        raise ActionSchemaError(f"'{field_name}' must be a list of strings.")
    result: List[str] = []
    for index, item in enumerate(value):
        text = str(item or "").strip()
        if not text:
            raise ActionSchemaError(f"'{field_name}[{index}]' must not be empty.")
        result.append(text)
    return result


@dataclass(frozen=True)
class ActionSchema:
    """Canonical provider-agnostic action record."""

    action: str
    capability: str
    target: str = ""
    args: Dict[str, Any] = field(default_factory=dict)
    preconditions: List[str] = field(default_factory=list)
    postconditions: List[str] = field(default_factory=list)
    depends_on: List[str] = field(default_factory=list)
    step_id: str = ""
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        object.__setattr__(self, "action", validate_identifier(self.action, "action"))
        object.__setattr__(self, "capability", validate_identifier(self.capability, "capability"))
        object.__setattr__(self, "target", str(self.target or "").strip())
        object.__setattr__(self, "args", copy.deepcopy(_json_safe(self.args, "args")))
        object.__setattr__(self, "preconditions", normalize_string_list(self.preconditions, "preconditions"))
        object.__setattr__(self, "postconditions", normalize_string_list(self.postconditions, "postconditions"))
        object.__setattr__(self, "depends_on", normalize_string_list(self.depends_on, "depends_on"))
        object.__setattr__(self, "step_id", str(self.step_id or "").strip())
        object.__setattr__(self, "description", str(self.description or "").strip())
        object.__setattr__(self, "metadata", copy.deepcopy(_json_safe(self.metadata, "metadata")))

    @classmethod
    def from_dict(cls, raw: Dict[str, Any], index: int = 1) -> "ActionSchema":
        if not isinstance(raw, dict):
            raise ActionSchemaError(f"Action step {index} must be an object.")

        return cls(
            action=raw.get("action", ""),
            capability=raw.get("capability", ""),
            target=raw.get("target", ""),
            args=raw.get("args", {}) if raw.get("args") is not None else {},
            preconditions=raw.get("preconditions", []),
            postconditions=raw.get("postconditions", []),
            depends_on=raw.get("depends_on", []),
            step_id=raw.get("id", raw.get("step_id", f"action_{index}")),
            description=raw.get("description", ""),
            metadata=raw.get("metadata", {}) if raw.get("metadata") is not None else {},
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action,
            "capability": self.capability,
            "target": self.target,
            "args": copy.deepcopy(self.args),
            "preconditions": list(self.preconditions),
            "postconditions": list(self.postconditions),
            "depends_on": list(self.depends_on),
            "id": self.step_id,
            "description": self.description,
            "metadata": copy.deepcopy(self.metadata),
        }
