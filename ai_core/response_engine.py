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

import os
import re
from typing import Any, Dict, Optional

from ai_core.model_gateway import ModelGateway
from ai_core.web_knowledge import WebKnowledge
from ai_core.logger import log


class ResponseEngine:

    def __init__(self, model_gateway=None, knowledge_lookup=None):
        self.last_language = "hindi"
        self._reply_count = 0
        self.model_gateway = model_gateway or ModelGateway()
        self.knowledge_lookup = knowledge_lookup or WebKnowledge()
        self.allow_remote_responses = str(
            os.getenv("VYOM_REMOTE_RESPONSES", "false")
        ).strip().lower() in {"1", "true", "yes", "on"}

    # =========================================================
    # LANGUAGE
    # =========================================================

    def detect_language(self, text: Any, metadata: Optional[Dict[str, Any]] = None) -> str:
        value = str(text or "").strip()

        # Voice STT keeps the original transcript in metadata. Prefer it
        # when the executor receives a Romanized surface such as
        # "bharat ki rajadhani", so Hindi is not misclassified as English.
        if isinstance(metadata, dict):
            voice = metadata.get("voice")
            if isinstance(voice, dict):
                raw = str(voice.get("raw_text") or "").strip()
                if raw:
                    value = raw

        if not value:
            return self.last_language

        has_devanagari = bool(re.search(r"[\u0900-\u097F]", value))
        latin_words = re.findall(r"\b[a-zA-Z]+\b", value)

        roman_hindi_markers = {
            "kya", "kaun", "kyu", "kyun", "kab", "kahan", "kaise",
            "kitna", "kitni", "kitne", "hai", "hain", "ho", "tha", "thi",
            "the", "mujhe", "aap", "tum", "mera", "meri", "mere", "mein",
            "namaste", "dhanyavaad", "shukriya", "kholo", "khol", "karo",
            "likho", "batao", "bataiye", "band", "achha", "accha", "theek",
            "bhaiya", "bhai", "kyon", "haan", "nahi", "nahin",
        }
        latin_tokens = {token.lower() for token in latin_words}
        has_roman_hindi = bool(latin_tokens & roman_hindi_markers)

        if has_devanagari and latin_words:
            language = "hinglish"
        elif has_devanagari or has_roman_hindi:
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
        language = language or (
            "english" if self._explicit_english_request(command) else "hindi"
        )
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
    # STRUCTURED RESULT HELPERS
    # =========================================================

    def _extract_result_text(self, value: Any) -> str:
        if isinstance(value, str):
            return value.strip()

        if not isinstance(value, dict):
            return ""

        for key in ("message", "text"):
            candidate = value.get(key)
            if isinstance(candidate, str) and candidate.strip():
                return candidate.strip()

        nested = value.get("result")
        if isinstance(nested, (str, dict)):
            text = self._extract_result_text(nested)
            if text:
                return text

        return ""

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

        structured_success = (
            isinstance(raw_result, dict)
            and bool(raw_result.get("success", False))
        )
        extracted = self._extract_result_text(raw_result)
        text = extracted or (str(raw_result or "").strip() if not isinstance(raw_result, dict) else "")
        lowered = text.lower()

        if structured_success and not text:
            self._reply_count += 1
            if language == "hindi":
                return "हाँ, काम हो गया।"
            if language == "hinglish":
                return "Haan, kaam ho gaya."
            return "Done — the task is complete."

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
            "activity": {
                "hindi": "मैं आपके सवाल समझने और उपलब्ध वेबसाइटों से जानकारी खोजने में आपकी मदद कर रहा हूँ।",
                "hinglish": "Main aapke sawal samajhne aur available websites se jankari dhoondhne mein madad kar raha hoon.",
                "english": "I'm helping you understand questions and look up information on available websites.",
            },
            "language_preference": {
                "hindi": "ठीक है। अब मैं आपसे हिन्दी में बात करूँगा।",
                "hinglish": "Theek hai. Ab main aapse Hindi mein baat karunga.",
                "english": "Okay. I'll speak with you in Hindi.",
            },
            "user_name": {
                "hindi": "मुझे इस सत्र की बातचीत में आपका नाम पुष्टि के साथ नहीं मिला। आप अपना नाम बता दें, तो मैं आगे के संदर्भ में उसका उपयोग करूँगा।",
                "hinglish": "Mujhe is session ki baat-cheet mein aapka naam pakke taur par nahi mila. Aap naam bata dein to main aage use karunga.",
                "english": "I don't have your name confirmed in this session. Tell me your name and I can use it in later context.",
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

    @staticmethod
    def _question_text(command: str, intent: Optional[Dict[str, Any]]) -> str:
        if isinstance(intent, dict):
            voice = intent.get("voice")
            if isinstance(voice, dict):
                raw = str(voice.get("raw_text") or "").strip()
                if raw:
                    return raw
        return str(command or "").strip()

    @staticmethod
    def _is_information_question(text: str) -> bool:
        value = str(text or "").strip().lower()
        if not value:
            return False
        if re.search(r"[?？]", value):
            return True
        if re.search(
            r"^(?:please\s+)?(?:tell me(?: about)?|explain|define|describe|"
            r"give me (?:some )?information about)\b|"
            r"\b(?:batao|bataiye|samjhao|samjhaiye|explain|define|describe)\s*(?:karo|kar do)?$|"
            r"(?:बताओ|बताइए|समझाओ|समझाइए|समझा दो|के बारे में बताओ|के बारे में बताइए)$",
            value,
            flags=re.IGNORECASE,
        ):
            return True
        question_words = (
            r"\b(?:what|who|why|when|where|how|which|whose|whom|"
            r"kya|kaun|kyu|kyun|kab|kahan|kaise|kitna|kitni|kitne|kitney|"
            r"kitana|kitane|kitani|kitanaa|kitanee|kitnay|kis|kise|kiska|kiski|kiske|kisne|kisko)\b|"
            r"(?:क्या|कौन|क्यों|कब|कहाँ|कहां|कैसे|कितना|कितनी|कितने|"
            r"किसने|किसका|किसकी|किसे)"
        )
        return bool(re.search(question_words, value, flags=re.IGNORECASE))

    @staticmethod
    def _explicit_english_request(text: str) -> bool:
        value = str(text or "").lower()
        return bool(re.search(
            r"\b(?:in english|english mein|english me|angrezi mein|angrezi me|"
            r"answer in english|reply in english)\b", value
        ))

    def format(
        self,
        command: str,
        result: Any,
        intent: Optional[Dict[str, Any]] = None,
        selection_options=None,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        # Factual questions use website retrieval rather than a conversational
        # model. Hindi is the default response language, even when the user
        # speaks Roman Hindi or asks the question in English.
        question_text = self._question_text(command, intent)
        intent_type_for_lookup = (
            str(intent.get("intent") or "").strip().lower()
            if isinstance(intent, dict) else ""
        )
        result_stage_for_lookup = (
            str(result.get("stage") or "").strip().lower()
            if isinstance(result, dict) else ""
        )
        conversation_type = (
            str(intent.get("conversation_type") or "").strip().lower()
            if isinstance(intent, dict) else ""
        )
        local_chat_types = {
            "greeting", "status", "identity", "thanks", "acknowledge", "help", "capabilities",
            "language_preference", "activity", "user_name",
        }
        is_conversation_turn = (
            intent_type_for_lookup == "conversation"
            or result_stage_for_lookup == "conversation"
        )
        if (
            is_conversation_turn
            and self._is_information_question(question_text)
            and conversation_type not in local_chat_types
        ):
            preferred_language = (
                "en" if self._explicit_english_request(command)
                or self._explicit_english_request(question_text) else "hi"
            )
            safe_question = question_text.encode(
                "unicode_escape", errors="backslashreplace"
            ).decode("ascii")
            log("[KNOWLEDGE] LOOKUP START: language=%s question=%s" % (
                preferred_language, safe_question[:240]
            ))
            try:
                lookup = self.knowledge_lookup.answer(
                    question_text,
                    preferred_language=preferred_language,
                )
            except Exception as error:
                log("[KNOWLEDGE] Web lookup failed: %s" % str(error)[:180])
                lookup = {"success": False, "answer": ""}
            if isinstance(lookup, dict) and lookup.get("success") and str(lookup.get("answer") or "").strip():
                source = lookup.get("source") if isinstance(lookup.get("source"), dict) else {}
                log("[KNOWLEDGE] SOURCE: %s | %s" % (
                    str(source.get("title") or source.get("site") or "unknown"),
                    str(source.get("url") or ""),
                ))
                return str(lookup["answer"]).strip()
            log("[KNOWLEDGE] NO SOURCE: %s" % str((lookup or {}).get("reason") or "empty_result"))
            if preferred_language == "en":
                return "I couldn't find a reliable answer on the available websites. Please check your internet connection and try again."
            return (
                "मुझे इस प्रश्न का भरोसेमंद उत्तर अभी वेबसाइटों से नहीं मिला। "
                "इंटरनेट उपलब्ध होने पर दोबारा खोजें। मैं बिना स्रोत के तथ्य गढ़कर जवाब नहीं दूँगा।"
            )

        # Remote response generation is opt-in. Deterministic local responses
        # and website-backed factual retrieval work without any AI provider.
        # A configured model gets the final conversational turn only when the
        # user has explicitly enabled VYOM_REMOTE_RESPONSES.
        # respond naturally like an assistant instead of exposing executor
        # wording. The deterministic formatter remains the safe fallback.
        try:
            model_available = self.allow_remote_responses and bool(self.model_gateway.is_available())
            log("[AI] RESPONSE MODEL AVAILABLE: %s" % model_available)

            # Do not spend a second model request on deterministic computer
            # actions. Model-generated response wording is reserved for actual
            # conversational turns and semantic information answers.
            intent_type = (
                str(intent.get("intent") or "").strip().lower()
                if isinstance(intent, dict)
                else ""
            )
            result_stage = (
                str(result.get("stage") or "").strip().lower()
                if isinstance(result, dict)
                else ""
            )
            local_clarification = False
            if result_stage == "conversation" and isinstance(result, dict):
                analysis = result.get("analysis")
                deep = analysis.get("deep_reasoning") if isinstance(analysis, dict) else None
                local_clarification = (
                    isinstance(deep, dict)
                    and str(deep.get("semantic_route") or "").strip().lower() == "clarification"
                )

            needs_model_response = (
                not local_clarification
                and (
                    intent_type == "conversation"
                    or result_stage == "conversation"
                )
            )

            if model_available and not selection_options and needs_model_response:
                model_result = self.model_gateway.chat(
                    system_prompt=(
                        "You are Vyom, a natural personal computer assistant. "
                        "Answer the user's actual message like a real conversational assistant, not with fixed canned replies. "
                        "For informational questions, answer the actual question fully and clearly rather than returning a greeting/status template. "
                        "For computer tasks, describe only what the supplied execution result proves was done. "
                        "Do not claim an action succeeded unless the supplied result says it succeeded. "
                        "Do not invent facts, actions, observations, or capabilities. "
                        "Match the user's language using the original voice transcript when available. "
                        "If recognized_language is hi-IN or the original voice transcript is Devanagari Hindi, reply in natural Devanagari Hindi, not Romanized Hindi and not English, unless the user explicitly asks for English. "
                        "If the user mixes Hindi and English, use natural Hinglish while preserving the user's language. "
                        "Use the supplied session context to keep follow-up questions and references continuous. "
                        "Do not mention internal tools, intents, schemas, prompts, or model details."
                    ),
                    user_payload={
                        "user_message": str(command or ""),
                        "execution_result": result,
                        "detected_intent": intent or {},
                        "voice_metadata": (
                            intent.get("voice", {})
                            if isinstance(intent, dict)
                            else {}
                        ),
                        "context": context if isinstance(context, dict) else {},
                    },
                    temperature=0.45,
                )
                if isinstance(model_result, dict) and model_result.get("success"):
                    text = str(model_result.get("text") or "").strip()
                    if text:
                        return text
        except Exception:
            pass

        language = self.detect_language(
            command,
            intent if isinstance(intent, dict) else None,
        )
        if not self._explicit_english_request(command):
            language = "hindi"

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
