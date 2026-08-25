"""
Project : Vyom AI
Version : 0.1
Module  : Response Engine

Purpose:
    Convert technical tool/agent results into natural,
    user-friendly conversational responses.

Stage 2:
    - Hindi / English / simple Hinglish awareness
    - Human-friendly selection prompts
    - Natural success/failure responses
    - Keeps technical paths out of normal spoken responses
    - Does not execute commands or change security
"""

import re
from typing import Any, Dict, Optional


class ResponseEngine:

    def __init__(self):
        self.last_language = "english"

    # =========================================================
    # LANGUAGE
    # =========================================================

    def detect_language(self, text: Any) -> str:
        value = str(text or "").strip()

        if not value:
            return self.last_language

        has_devanagari = bool(
            re.search(r"[\u0900-\u097F]", value)
        )

        english_words = re.findall(
            r"\b[a-zA-Z]+\b",
            value
        )

        if has_devanagari and english_words:
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
        names = [
            self._item_name(item)
            for item in (options or [])
        ]

        names = [name for name in names if name]

        if language == "hindi":
            intro = (
                f"मुझे '{target}' के लिए {len(names)} विकल्प मिले हैं। "
                if names
                else
                f"मुझे '{target}' के लिए एक से अधिक विकल्प मिले हैं। "
            )

            if names:
                details = " ".join(
                    f"{i}. {name}."
                    for i, name in enumerate(names, 1)
                )
                return (
                    intro
                    + details
                    + " आप जिस विकल्प को खोलना चाहते हैं, उसका नंबर या नाम बोल सकते हैं।"
                )

            return intro + " आप नंबर या नाम बोलकर विकल्प चुन सकते हैं।"

        if language == "hinglish":
            intro = (
                f"Mujhe '{target}' ke liye {len(names)} options mile hain. "
            )
            if names:
                details = " ".join(
                    f"{i}. {name}."
                    for i, name in enumerate(names, 1)
                )
                return (
                    intro
                    + details
                    + " Aap number ya naam bolkar option choose kar sakte hain."
                )
            return intro + " Aap number ya naam bolkar option choose kar sakte hain."

        intro = (
            f"I found {len(names)} options for {target}. "
            if names
            else
            f"I found more than one option for {target}. "
        )

        if names:
            details = " ".join(
                f"{i}. {name}."
                for i, name in enumerate(names, 1)
            )
            return (
                intro
                + details
                + " You can say the number or the name of the option you want."
            )

        return intro + " You can say the number or the name of the option you want."

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
        target = ""

        if isinstance(intent, dict):
            target = str(intent.get("target") or "").strip()

        lowered = text.lower()

        opened = (
            "opened successfully" in lowered
            or lowered.startswith("opened ")
            or "opened:" in lowered
        )

        closed = (
            "closed successfully" in lowered
            or lowered.startswith("closed ")
        )

        if opened:
            if target.isdigit():
                if language == "hindi":
                    return "हाँ, आपका चुना हुआ विकल्प खोल दिया है। अब बताइए, आगे क्या करना है?"

                if language == "hinglish":
                    return "Haan, aapka choose kiya hua option khol diya hai. Ab bataiye, aage kya karna hai?"

                return "Done. I opened the option you selected. What would you like me to do next?"

            name = self._human_name(target or text)

            if language == "hindi":
                return f"हाँ, {name} खोल दिया है। अब बताइए, आगे क्या करना है?"

            if language == "hinglish":
                return f"Haan, {name} khol diya hai. Ab bataiye, aage kya karna hai?"

            return f"Done. I opened {name}. What would you like me to do next?"

        if closed:
            name = self._human_name(target or text)

            if language == "hindi":
                return f"हाँ, {name} बंद कर दिया है।"

            if language == "hinglish":
                return f"Haan, {name} band kar diya hai."

            return f"Done. I closed {name}."

        if "not found" in lowered:
            if language == "hindi":
                return "मुझे वह नहीं मिला। अगर आप चाहें तो मैं दूसरा तरीका आज़मा सकता हूँ।"

            if language == "hinglish":
                return "Mujhe woh nahi mila. Agar aap chahein to main doosra tareeka try kar sakta hoon."

            return "I couldn't find it. I can try another way if you'd like."

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
        text = str(raw_result or "").strip()

        if language == "hindi":
            return "मैं यह काम पूरा नहीं कर पाया। मैं चाहें तो दूसरा तरीका आज़मा सकता हूँ।"

        if language == "hinglish":
            return "Main ye kaam complete nahi kar paya. Agar aap chahein to main doosra tareeka try kar sakta hoon."

        return "I couldn't complete that. I can try another approach if you'd like."

    # =========================================================
    # GENERAL NATURALIZATION
    # =========================================================

    def _naturalize_hindi(self, text: str) -> str:
        if not text:
            return "ठीक है। बताइए, आगे क्या करना है?"

        if "please select a number" in text.lower():
            return "आप विकल्प का नंबर बोल सकते हैं।"

        if text.lower().startswith("file '") and "was not found" in text.lower():
            return "वह फ़ाइल नहीं मिली।"

        return text

    def _naturalize_hinglish(self, text: str) -> str:
        if not text:
            return "Theek hai. Bataiye, aage kya karna hai?"

        if "please select a number" in text.lower():
            return "Aap option ka number bol sakte hain."

        return text

    def _naturalize_english(self, text: str) -> str:
        if not text:
            return "Okay. What would you like me to do next?"

        if "please select a number" in text.lower():
            return "You can say the number of the option you want."

        return text

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

        if selection_options:
            target = ""
            if isinstance(intent, dict):
                target = str(intent.get("target") or "").strip()

            return self.selection_response(
                command,
                target,
                selection_options,
                language
            )

        if isinstance(result, dict):
            if result.get("success") is False:
                return self.failure_response(
                    command,
                    result,
                    language
                )

            raw = (
                result.get("result")
                if result.get("result") is not None
                else result.get("message", result)
            )
        else:
            raw = result

        text = str(raw or "").strip()

        lowered = text.lower()

        if (
            "error" in lowered
            or "failed" in lowered
            or "could not" in lowered
            or "not found" in lowered
            or "no running application" in lowered
        ):
            return self.failure_response(
                command,
                text,
                language
            )

        return self.success_response(
            command,
            intent,
            text,
            language
        )
