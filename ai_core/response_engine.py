"""
Project : Vyom AI
Version : 0.2
Module  : Response Engine

Purpose:
    Turn technical execution results into short, natural and
    context-aware replies.  This layer never executes commands.

Stage 4 foundation:
    - Hindi / English / Hinglish replies
    - Friendly conversational tone
    - No raw paths in normal success replies
    - Context-aware follow-up wording
    - Selection prompts without technical wording
    - Safe, predictable fallback when an executor returns raw text

Security:
    This module does not create, modify, or execute code.
"""

import re
from typing import Any, Dict, Optional


class ResponseEngine:

    def __init__(self):
        self.last_language = "hindi"
        self._reply_count = 0

    # =========================================================
    # LANGUAGE
    # =========================================================

    def detect_language(self, text: Any) -> str:
        value = str(text or "").strip()
        if not value:
            return self.last_language

        has_devanagari = bool(re.search(r"[\u0900-\u097F]", value))
        latin_words = re.findall(r"\b[a-zA-Z]+\b", value)

        if has_devanagari and latin_words:
            language = "hinglish"
        elif has_devanagari:
            language = "hindi"
        else:
            language = "english"

        self.last_language = language
        return language

    # =========================================================
    # HELPERS
    # =========================================================

    def _clean_target(self, target: Any) -> str:
        value = str(target or "").strip()
        value = value.replace("\\", "/")
        return value.rstrip("/").split("/")[-1] or value

    def _human_name(self, value: Any) -> str:
        name = self._clean_target(value)
        name = re.sub(r"\.(exe|lnk|bat|cmd)$", "", name, flags=re.I)
        return name.strip()

    def _item_name(self, item: Any) -> str:
        if isinstance(item, dict):
            return str(
                item.get("name")
                or item.get("display_name")
                or item.get("path")
                or "विकल्प"
            ).strip()
        return self._human_name(item)

    def _friendly_error(self, text: str, language: str) -> str:
        lowered = str(text or "").lower()

        if "no running application" in lowered:
            if language == "hindi":
                return "वह ऐप अभी चलती हुई नहीं मिली।"
            if language == "hinglish":
                return "Woh app abhi running nahi mili."
            return "That app doesn't appear to be running right now."

        if "not found" in lowered:
            if language == "hindi":
                return "मुझे वह नहीं मिला। चाहें तो मैं दूसरा तरीका आज़मा सकता हूँ।"
            if language == "hinglish":
                return "Mujhe woh nahi mila. Chahein to main doosra tareeka try kar sakta hoon."
            return "I couldn't find it. I can try another approach."

        if "timeout" in lowered or "timed out" in lowered:
            if language == "hindi":
                return "इसमें थोड़ा ज़्यादा समय लग गया। मैं फिर कोशिश कर सकता हूँ।"
            if language == "hinglish":
                return "Isme thoda zyada time lag gaya. Main phir try kar sakta hoon."
            return "That took longer than expected. I can try again."

        if language == "hindi":
            return "यह काम पूरा नहीं हो पाया। मैं दूसरा तरीका आज़मा सकता हूँ।"
        if language == "hinglish":
            return "Ye kaam complete nahi ho paya. Main doosra tareeka try kar sakta hoon."
        return "I couldn't complete that. I can try another approach."

    # =========================================================
    # SELECTION
    # =========================================================

    def selection_response(
        self,
        command: str,
        target: str,
        options,
        language: Optional[str] = None
    ) -> str:
        language = language or self.detect_language(command)
        names = [self._item_name(item) for item in (options or [])]
        names = [name for name in names if name]

        if language == "hindi":
            if names:
                details = " ".join(f"{i}. {name}" for i, name in enumerate(names, 1))
                return (
                    f"मुझे {target or 'उस नाम'} के लिए कुछ विकल्प मिले हैं: {details}। "
                    "आप नंबर या नाम बोल दें, मैं वही खोल दूँगा।"
                )
            return "मुझे एक से ज़्यादा विकल्प मिले हैं। आप नंबर या नाम बोल दें।"

        if language == "hinglish":
            if names:
                details = " ".join(f"{i}. {name}" for i, name in enumerate(names, 1))
                return (
                    f"Mujhe {target or 'us naam'} ke liye kuch options mile hain: {details}. "
                    "Aap number ya naam bol dein, main wahi open kar dunga."
                )
            return "Mujhe ek se zyada options mile hain. Aap number ya naam bol dein."

        if names:
            details = " ".join(f"{i}. {name}" for i, name in enumerate(names, 1))
            return (
                f"I found a few options for {target or 'that'}: {details}. "
                "Just say the number or name and I'll open it."
            )
        return "I found more than one option. Just say the number or name you want."

    # =========================================================
    # SUCCESS
    # =========================================================

    def success_response(
        self,
        command: str,
        intent: Optional[Dict[str, Any]],
        raw_result: Any,
        language: Optional[str] = None
    ) -> str:
        language = language or self.detect_language(command)
        text = str(raw_result or "").strip()
        lowered = text.lower()

        target = ""
        if isinstance(intent, dict):
            target = str(intent.get("target") or "").strip()

        opened = (
            "opened successfully" in lowered
            or lowered.startswith("opened ")
            or "opened:" in lowered
        )
        closed = (
            "closed successfully" in lowered
            or lowered.startswith("closed ")
        )

        self._reply_count += 1

        if opened:
            name = self._human_name(target or text)
            if language == "hindi":
                return f"हाँ, {name} खोल दिया है। अब बताइए, आगे क्या करना है?"
            if language == "hinglish":
                return f"Haan, {name} khol diya hai. Ab bataiye, aage kya karna hai?"
            return f"Done, I opened {name}. What should we do next?"

        if closed:
            name = self._human_name(target or text)
            if language == "hindi":
                return f"हाँ, {name} बंद कर दिया है।"
            if language == "hinglish":
                return f"Haan, {name} band kar diya hai."
            return f"Done, I closed {name}."

        if any(x in lowered for x in (
            "error", "failed", "failure", "could not", "unable",
            "not found", "no running application", "exception"
        )):
            return self._friendly_error(text, language)

        if language == "hindi":
            return self._naturalize_hindi(text)
        if language == "hinglish":
            return self._naturalize_hinglish(text)
        return self._naturalize_english(text)

    # =========================================================
    # FAILURE
    # =========================================================

    def failure_response(
        self,
        command: str,
        raw_result: Any,
        language: Optional[str] = None
    ) -> str:
        language = language or self.detect_language(command)
        return self._friendly_error(str(raw_result or ""), language)

    # =========================================================
    # NATURALIZATION
    # =========================================================

    def _naturalize_hindi(self, text: str) -> str:
        value = str(text or "").strip()
        if not value:
            return "ठीक है। बताइए, आगे क्या करना है?"
        if "please select a number" in value.lower():
            return "आप बस विकल्प का नंबर या नाम बोल दीजिए।"
        if "skill name is required" in value.lower():
            return "मैं उस काम के लिए सही capability तैयार नहीं कर पाया।"
        if "capability plan" in value.lower():
            return "मैंने काम को समझ लिया है और इसके लिए अगला तरीका तैयार कर रहा हूँ।"
        return value

    def _naturalize_hinglish(self, text: str) -> str:
        value = str(text or "").strip()
        if not value:
            return "Theek hai. Bataiye, aage kya karna hai?"
        if "please select a number" in value.lower():
            return "Aap bas option ka number ya naam bol dijiye."
        if "skill name is required" in value.lower():
            return "Main us kaam ke liye sahi capability prepare nahi kar paya."
        if "capability plan" in value.lower():
            return "Maine kaam samajh liya hai aur agla tareeka prepare kar raha hoon."
        return value

    def _naturalize_english(self, text: str) -> str:
        value = str(text or "").strip()
        if not value:
            return "Okay. What would you like me to do next?"
        if "please select a number" in value.lower():
            return "Just tell me the number or name you want."
        if "skill name is required" in value.lower():
            return "I couldn't prepare the right capability for that yet."
        if "capability plan" in value.lower():
            return "I understand the goal and I'm preparing the next approach."
        return value

    # =========================================================
    # CONVERSATION
    # =========================================================

    def conversation_response(
        self,
        command: str,
        conversation_type: str,
        language: Optional[str] = None
    ) -> str:
        language = language or self.detect_language(command)

        responses = {
            "greeting": {
                "hindi": "नमस्ते 😊 मैं यहीं हूँ। बताइए, आज क्या करना है?",
                "hinglish": "Namaste 😊 Main yahin hoon. Bataiye, aaj kya karna hai?",
                "english": "Hello 😊 I'm here. What would you like to do?",
            },
            "status": {
                "hindi": "मैं बढ़िया हूँ और काम के लिए तैयार हूँ। आप बताइए, क्या करना है?",
                "hinglish": "Main badhiya hoon aur kaam ke liye ready hoon. Aap bataiye, kya karna hai?",
                "english": "I'm doing well and I'm ready to help. What shall we do?",
            },
            "capabilities": {
                "hindi": "आप बस अपना काम बताइए। मैं उपलब्ध tools और capabilities में से खुद सही तरीका चुनने की कोशिश करूँगा।",
                "hinglish": "Aap bas apna kaam bataiye. Main available tools aur capabilities mein se khud sahi tareeka choose karne ki koshish karunga.",
                "english": "Just tell me the job you want done. I'll choose the most suitable available tools and capabilities.",
            },
            "thanks": {
                "hindi": "खुशी हुई 😊 जब चाहें अगला काम बता दीजिए।",
                "hinglish": "Khushi hui 😊 Jab chahein agla kaam bata dijiye.",
                "english": "You're welcome 😊 Just tell me what you'd like to do next.",
            },
            "acknowledge": {
                "hindi": "ठीक है, मैं साथ हूँ।",
                "hinglish": "Theek hai, main saath hoon.",
                "english": "Okay, I'm with you.",
            },
            "identity": {
                "hindi": "मैं Vyom हूँ। आपका personal computer assistant बनने के लिए बनाया जा रहा हूँ।",
                "hinglish": "Main Vyom hoon. Aapka personal computer assistant banne ke liye bana hoon.",
                "english": "I'm Vyom, your personal computer assistant.",
            },
            "help": {
                "hindi": "आप अपना काम सामान्य तरीके से बताइए। मैं पहले समझूँगा, फिर उपलब्ध तरीके से उसे करने की कोशिश करूँगा।",
                "hinglish": "Aap apna kaam normal tareeke se bataiye. Main pehle samjhunga, phir available tareeke se use karne ki koshish karunga.",
                "english": "Tell me the task naturally. I'll understand it first and then try to carry it out with the available tools.",
            },
        }

        group = responses.get(conversation_type, responses["acknowledge"])
        return group.get(language, group["english"])

    # =========================================================
    # MAIN FORMATTER
    # =========================================================

    def format(
        self,
        command: str,
        result: Any,
        intent: Optional[Dict[str, Any]] = None,
        selection_options=None
    ) -> str:
        language = self.detect_language(command)

        if isinstance(intent, dict) and intent.get("intent") == "conversation":
            return self.conversation_response(
                command,
                intent.get("conversation_type", "acknowledge"),
                language
            )

        if isinstance(result, dict) and result.get("conversation_type"):
            return self.conversation_response(
                command,
                result.get("conversation_type", "acknowledge"),
                language
            )

        if selection_options:
            target = ""
            if isinstance(intent, dict):
                target = str(intent.get("target") or "").strip()
            return self.selection_response(command, target, selection_options, language)

        if isinstance(result, dict):
            if result.get("success") is False:
                return self.failure_response(command, result, language)
            raw = result.get("result")
            if raw is None:
                raw = result.get("message", result)
        else:
            raw = result

        return self.success_response(command, intent, raw, language)
