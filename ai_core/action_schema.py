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
    risk_level: str = "normal"
    requires_confirmation: bool = False
    confirmation_reason: str = ""
    reversible: Optional[bool] = None

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

        risk_level = str(self.risk_level or "normal").strip().lower()
        allowed_risk_levels = {"low", "normal", "medium", "high", "critical", "irreversible"}
        if risk_level not in allowed_risk_levels:
            raise ActionSchemaError(
                "'risk_level' must be one of: low, normal, medium, high, critical, irreversible."
            )
        object.__setattr__(self, "risk_level", risk_level)

        if not isinstance(self.requires_confirmation, bool):
            raise ActionSchemaError("'requires_confirmation' must be a boolean.")
        if self.reversible is not None and not isinstance(self.reversible, bool):
            raise ActionSchemaError("'reversible' must be a boolean when supplied.")
        object.__setattr__(self, "confirmation_reason", str(self.confirmation_reason or "").strip())

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
            risk_level=raw.get("risk_level", "normal"),
            requires_confirmation=raw.get("requires_confirmation", False),
            confirmation_reason=raw.get("confirmation_reason", ""),
            reversible=raw.get("reversible"),
        )

    def to_dict(self) -> Dict[str, Any]:
        result = {
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
        # Preserve historical output for default-risk actions; emit only
        # non-default risk fields so legacy plan comparisons remain stable.
        if self.risk_level != "normal":
            result["risk_level"] = self.risk_level
        if self.requires_confirmation:
            result["requires_confirmation"] = True
        if self.confirmation_reason:
            result["confirmation_reason"] = self.confirmation_reason
        if self.reversible is not None:
            result["reversible"] = self.reversible
        return result
