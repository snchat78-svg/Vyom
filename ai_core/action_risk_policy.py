"""
Conservative pre-dispatch risk classification for generic and legacy mission steps.

This policy never executes actions. It intentionally does not inspect free-form
typed text, clipboard contents, or other user payloads: only action semantics,
target labels, descriptions, and structured risk metadata are considered.
"""

import re
from typing import Any, Dict, List


class ActionRiskPolicy:
    """Detect common hard-to-reverse side effects before a mission starts."""

    ALLOWED_RISK_LEVELS = {"low", "normal", "medium", "high", "critical", "irreversible"}
    HIGH_RISK_LEVELS = {"high", "critical", "irreversible"}
    NON_ACTION_KEYWORDS = {
        "send key", "send keys", "keypress", "key press", "press key",
        "hotkey", "type text", "write text",
    }

    _OPERATION_PATTERN = re.compile(
        r"\b(?:delete|erase|wipe|format|uninstall|overwrite|truncate|destroy|purge|drop|remove|"
        r"reset|submit|publish|purchase|buy|pay|payment|make payment|charge card|transfer|withdraw|revoke|"
        r"grant access|revoke access|change password|close account|account closure|delete account|disable account|factory reset|format disk|format drive|"
        r"send email|send message|send document|send file|send request|send order|send notification|send invite|invite user|"
        r"share publicly|make public|publish publicly|post publicly|unpublish|cancel subscription|cancel order|place order|confirm order|revoke token|disconnect integration|delete user|block user|ban user|unsubscribe|issue refund|refund|hatao|hatana|hata do|mitao|mitana|mita do|"
        r"bhejo|bhejna|bhej do|jama karo|kharido|khareedo|paise transfer|paise bhejo|bhugtan|bhugtan karo|"
        r"डिलीट|हटाओ|हटाना|हटा दो|हटाएं|हटाएँ|मिटाओ|मिटाना|मिटा दो|भेजो|भेजना|भेज दो|"
        r"जमा करो|खरीदो|खरीदना|भुगतान|भुगतान करो|पैसे ट्रांसफर|पैसे भेजो|रकम भेजो|"
        r"खाता बंद|खाता हटाओ|पासवर्ड बदलो|फैक्टरी रीसेट|फॉर्मैट ड्राइव|प्रकाशित करो|पब्लिश करो|सबमिट करो|सदस्यता रद्द|ऑर्डर रद्द|सार्वजनिक करो|एक्सेस हटाओ|टोकन रद्द करो|इंटीग्रेशन डिस्कनेक्ट करो)(?=$|\W)",
        re.IGNORECASE,
    )
    _TARGET_PATTERN = re.compile(
        r"\b(?:delete|erase|wipe|format|uninstall|overwrite|remove|submit|send|publish|post|"
        r"purchase|buy|pay|payment|transfer|withdraw|reset|trash|recycle bin|close account|account closure|"
        r"change password|grant access|revoke access|share publicly|make public|charge card|cancel subscription|cancel order|delete account|disable account|revoke token|disconnect integration|delete user|block user|ban user|unsubscribe|"
        r"hatao|hatana|hata do|mitao|mita do|bhejo|bhej do|"
        r"डिलीट|हटाओ|हटाना|हटा दो|हटाएं|हटाएँ|मिटाओ|मिटाना|मिटा दो|भेजो|भेजना|भेज दो|"
        r"भुगतान|भुगतान करो|खाता बंद|खाता हटाओ|पासवर्ड बदलो|प्रकाशित करो|सदस्यता रद्द|ऑर्डर रद्द|सार्वजनिक करो|एक्सेस हटाओ|टोकन रद्द करो|पब्लिश करो|सबमिट|ट्रांसफर करो)(?=$|\W)",
        re.IGNORECASE,
    )

    @staticmethod
    def _surface(value: Any) -> str:
        return re.sub(r"[_-]+", " ", str(value or "").strip().lower())

    @classmethod
    def _classify_step(cls, step: Dict[str, Any], index: int) -> Dict[str, Any] | None:
        if not isinstance(step, dict):
            return None

        metadata = step.get("metadata")
        metadata = metadata if isinstance(metadata, dict) else {}
        intent = step.get("intent")
        if isinstance(intent, dict):
            intent_name = str(intent.get("intent") or intent.get("action") or "")
            intent_target = str(intent.get("target") or "")
        else:
            intent_name = str(intent or "")
            intent_target = ""

        action_name = str(step.get("action") or step.get("operation") or "")
        target = str(step.get("target") or intent_target or step.get("label") or "").strip()
        step_id = str(step.get("id") or step.get("step_id") or f"step_{index}").strip()
        reasons: List[str] = []

        flag_values = (
            step.get("requires_confirmation"),
            metadata.get("requires_confirmation"),
        )
        for value in flag_values:
            if value is True:
                reasons.append("explicit_confirmation_required")
            elif value not in (None, False, ""):
                reasons.append("invalid_confirmation_flag")

        risk_values = (step.get("risk_level"), metadata.get("risk_level"))
        normalized_levels = []
        for raw_level in risk_values:
            if raw_level is None or str(raw_level).strip() == "":
                continue
            level = str(raw_level).strip().lower()
            normalized_levels.append(level)
            if level in cls.HIGH_RISK_LEVELS:
                reasons.append("explicit_high_risk_level")
            elif level not in cls.ALLOWED_RISK_LEVELS:
                reasons.append("unknown_risk_level")

        for raw_value in (step.get("irreversible"), metadata.get("irreversible")):
            if raw_value is True:
                reasons.append("explicitly_irreversible")
            elif raw_value not in (None, False, ""):
                reasons.append("invalid_irreversibility_flag")

        for raw_value in (step.get("reversible"), metadata.get("reversible")):
            if raw_value is False:
                reasons.append("explicitly_not_reversible")
            elif raw_value is not None and not isinstance(raw_value, bool):
                reasons.append("invalid_reversibility_flag")

        action_surface = cls._surface(action_name)
        intent_surface = cls._surface(intent_name)
        operation_fields = [action_surface, intent_surface]
        if action_surface in cls.NON_ACTION_KEYWORDS:
            operation_fields.remove(action_surface)
        if intent_surface in cls.NON_ACTION_KEYWORDS:
            operation_fields.remove(intent_surface)
        operation_fields.extend([
            cls._surface(step.get("operation")),
            cls._surface(step.get("effect")),
            cls._surface(metadata.get("effect")),
        ])
        operation_text = " ".join(value for value in operation_fields if value)
        target_text = cls._surface(target)
        description_text = cls._surface(step.get("description") or step.get("confirmation_reason"))
        if cls._OPERATION_PATTERN.search(operation_text):
            reasons.append("potentially_irreversible_operation")
        if cls._TARGET_PATTERN.search(target_text):
            reasons.append("high_impact_target")
        if cls._OPERATION_PATTERN.search(description_text):
            reasons.append("high_impact_effect_description")

        if not reasons:
            return None

        unique_reasons = list(dict.fromkeys(reasons))
        action_label = cls._surface(action_name or intent_name or step.get("type") or "action")
        target_label = target[:80]
        risk_level = "critical" if any(
            value in {"critical", "irreversible"} for value in normalized_levels
        ) else "high"
        return {
            "step_id": step_id,
            "action": action_label[:80],
            "target": target_label,
            "risk_level": risk_level,
            "reasons": unique_reasons,
        }

    @classmethod
    def assess_plan(cls, plan: Any) -> Dict[str, Any]:
        """Return risk findings for the plan without exposing action payloads."""
        findings = []
        if isinstance(plan, list):
            for index, step in enumerate(plan, start=1):
                finding = cls._classify_step(step, index)
                if finding is not None:
                    findings.append(finding)

        summaries = []
        for item in findings:
            label = item.get("action") or "high-impact action"
            target = item.get("target")
            summaries.append(f"{label} ({target})" if target else label)
        return {
            "requires_confirmation": bool(findings),
            "risk_level": max(
                (item["risk_level"] for item in findings),
                key=lambda value: {"normal": 0, "high": 1, "critical": 2}.get(value, 1),
                default="normal",
            ),
            "findings": findings,
            "step_ids": [item["step_id"] for item in findings],
            "summary": "; ".join(dict.fromkeys(summaries))[:240],
        }
