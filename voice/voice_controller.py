# voice/voice_controller.py

import difflib, re, time
from .speech_to_text import SpeechToText
from .text_to_speech import TextToSpeech
from ai_core.conversation_manager import ConversationManager

class VoiceController:
    """
    Orchestrates wake-word and command flow. Reuses existing ConversationManager/Executor pipeline.
    """
    def __init__(self, stt=None, tts=None, conversation_manager=None):
        self.speech_to_text = stt or SpeechToText(debug=True)
        self.text_to_speech = tts or TextToSpeech(debug=True)
        self.conversation_manager = conversation_manager or ConversationManager()

        self.running = False
        self.activated = False
        self.state = "idle"
        self.last_listen_status = ""
        self.continuous_conversation = True
        # Wake-word aliases for stripping off any extra text
        self.wake_words = ("vyom", "व्योम", "viyom", "वियोम", "वियम", "वियॉम")

    def _log(self, msg):
        print("[VOICE] " + str(msg), flush=True)

    @staticmethod
    def _normalize(text):
        value = str(text or "").lower()
        value = re.sub(r"[^\w\s\u0900-\u097F]", " ", value, flags=re.UNICODE)
        return re.sub(r"\s+", " ", value).strip()

    def _find_wake_word(self, text):
        norm = self._normalize(text)
        for alias in self.wake_words:
            a_norm = self._normalize(alias)
            if a_norm and a_norm in norm:
                return a_norm
        # Fuzzy match short utterances (fallback)
        compact = norm.replace(" ", "")
        best, score = None, 0.0
        if len(compact) <= 24:
            for alias in self.wake_words:
                cand = self._normalize(alias).replace(" ", "")
                if not cand: continue
                ratio = difflib.SequenceMatcher(None, compact, cand).ratio()
                if ratio > score:
                    score = ratio; best = alias
            if score >= 0.72:
                return self._normalize(best)
        return None

    def _remove_wake_word(self, text):
        orig = text.strip()
        if not orig:
            return ""
        for alias in sorted(self.wake_words, key=len, reverse=True):
            pattern = re.compile(re.escape(alias), re.IGNORECASE)
            new_val = pattern.sub(" ", orig, count=1)
            if new_val != orig:
                return re.sub(r"\s+", " ", new_val).strip()
        # Try normalized removal
        norm = self._normalize(orig)
        for alias in sorted(self.wake_words, key=len, reverse=True):
            a_norm = self._normalize(alias)
            if a_norm and a_norm in norm:
                return re.sub(r"\s+", " ", norm.replace(a_norm, "", 1)).strip()
        return orig

    def _speak(self, message):
        """Use TTS to speak and log states."""
        if not message:
            self.state = "listening"
            return
        print("Vyom : " + message, flush=True)
        self.text_to_speech.speak(message)
        if self.running:
            time.sleep(0.3)
            self.state = "listening"
            self._log("READY TO LISTEN AGAIN")

    def _speak_startup(self):
        self._log("STARTUP TTS BEGIN")
        self._speak("नमस्ते, मैं व्योम हूँ। मुझे जगाने के लिए व्योम कहिए।")
        self._log("STARTUP TTS END")

    def _speak_activation(self):
        self._log("ACTIVATION TTS")
        self._speak("हाँ, बताइए।")

    def _listen_once(self, announce=False, timeout=5, phrase_time_limit=8, wake_mode=None):
        return self.speech_to_text.listen(
            timeout=timeout, phrase_time_limit=phrase_time_limit,
            announce=announce, wake_mode=wake_mode
        )

    def _recover_mic(self):
        self._log("AUDIO ERROR -> RECOVERY")
        try:
            restored = self.speech_to_text.start_session()
        except:
            restored = False
        if restored:
            self._log("MICROPHONE SESSION RESTORED")
        return restored

    def _wait_for_wake(self):
        self.state = "waiting_for_wake"
        self._log("WAITING_FOR_WAKE")
        result = self._listen_once(announce=False, timeout=2.5, phrase_time_limit=4, wake_mode=True)
        status = result.get("status","")
        if status == "device_error":
            self._recover_mic()
            return {"activated": False}

        text = result.get("text","") or ""
        wake = result.get("wake_word") or self._find_wake_word(text)
        wake_ok = result.get("success") and (status=="wake_detected" or bool(wake))
        if not wake_ok:
            self._log("Wake listen status: " + status)
            return {"activated": False}

        self._safe_print = lambda m: print(m, flush=True)  # for consistency
        print("Wake speech -> " + text, flush=True)
        print("Wake word detected -> " + (wake or "Vyom"), flush=True)
        self._activate()
        command_after = self._remove_wake_word(text)
        if command_after:
            print("Command after wake -> " + command_after, flush=True)
        return {"activated": True, "command": command_after}

    def _listen_active(self):
        self.state = "listening"
        self._log("STATE -> LISTENING")
        print("Vyom : Listening for your command...", flush=True)
        result = self._listen_once(announce=False, timeout=5, phrase_time_limit=10, wake_mode=False)
        status = result.get("status","")
        if status == "device_error":
            self._recover_mic()
            return ""
        if not result.get("success"):
            self._log("Active listen status: " + status)
            return ""
        cmd = (result.get("text","") or "").strip()
        if cmd:
            print("Command detected -> " + cmd, flush=True)
            self._log("ACTIVE COMMAND RECEIVED")
        return cmd

    def _is_exit(self, text):
        exit_words = {"exit","quit","bye","goodbye","बंद हो जाओ","रुक जाओ","बाय","अलविदा"}
        return self._normalize(text) in exit_words

    def run(self):
        print("="*60); print("Vyom AI - Voice Engine")
        self._log("VOICE ENGINE STARTING...")
        if not self.speech_to_text.is_available():
            print("Vyom : Speech-To-Text unavailable.", flush=True)
            print("Reason:", self.speech_to_text.error_message, flush=True)
            return False
        if not self.text_to_speech.speak:
            print("Vyom : Text-To-Speech unavailable; voice disabled.", flush=True)

        self.running = True; self.activated = False; self.state = "idle"
        # Startup speech
        if self.text_to_speech:
            self._speak_startup()
        if not self.speech_to_text.available:
            print("Vyom : Mic could not be initialized.", flush=True)
            return False

        print("\nVyom : Voice engine is ready.", flush=True)
        print("Vyom : Say 'Vyom' to activate.", flush=True)
        print()

        while self.running:
            if not self.activated:
                wake = self._wait_for_wake()
                if not wake.get("activated"):
                    continue

                cmd = wake.get("command","") or ""
                if cmd:
                    self._execute(cmd)
                    if self.running:
                        self.activated = True
                        self.state = "listening"
                    continue

                # Wake-only path: acknowledge and listen for the first command
                self.activated = True
                self.state = "active"
                self._log("WAKE -> ACTIVE SESSION")
                self._speak_activation()

                cmd = self._listen_active()
                if cmd:
                    self._execute(cmd)
                if self.running:
                    self.activated = True
                    self.state = "listening"
                    self._log("READY FOR NEXT COMMAND")
                continue

            # Already active: just listen and execute
            cmd = self._listen_active()
            if not cmd:
                continue
            self._execute(cmd)
            if self.running and self.continuous_conversation:
                self.activated = True
                self.state = "listening"
                self._log("CONTINUOUS SESSION -> LISTENING AGAIN")
            elif self.running:
                self.activated = False
                self.state = "waiting_for_wake"

        return True

    def _activate(self):
        self._log("WAKE WORD DETECTED")
        self._log("STATE -> ACTIVE SESSION")

    def _execute(self, command):
        command = command.strip()
        if not command:
            return
        if self._is_exit(command):
            self._log("Exit command detected.")
            self._speak("ठीक है। मैं सुनना बंद कर रहा हूँ।")
            self.running = False
            self.activated = False
            self.state = "idle"
            return

        print("Processing -> " + command, flush=True)
        result = self.conversation_manager.process_voice(command)
        response = str(result.get("response", result.get("message","")) or "").strip()
        if response:
            self._speak(response)
        else:
            print("Vyom : Command completed.", flush=True)
