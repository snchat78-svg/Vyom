# voice/text_to_speech.py

import pyttsx3

class TextToSpeech:
    """
    Handles TTS via Windows SAPI. Each speak() creates a fresh engine.
    """
    def __init__(self, rate=165, volume=1.0, debug=True):
        self.rate = rate
        self.volume = volume
        self.debug = debug

    def _log(self, msg):
        if self.debug:
            print("[TTS] " + str(msg), flush=True)

    def speak(self, text):
        """
        Speak the given text synchronously using SAPI.
        We create a new engine per call to avoid blocking.
        """
        self._log("speak() called.")
        try:
            engine = pyttsx3.init()
            engine.setProperty("rate", self.rate)
            engine.setProperty("volume", self.volume)
            self._log("Fresh SAPI engine created for speech turn.")
            # (Optional) select language/voice here if needed
            voices = engine.getProperty("voices")
            # Example: pick default or Indian English if available
            for voice in voices:
                if "english" in voice.languages or "English" in voice.name:
                    engine.setProperty("voice", voice.id)
                    self._log(f"Speech voice selected: {voice.name}")
                    break
            engine.say(text)
            self._log("engine.say() called.")
            engine.runAndWait()
            self._log("Engine runAndWait() complete; releasing engine.")
            return {"success": True, "message": ""}
        except Exception as e:
            self._log("TTS error: " + str(e))
            return {"success": False, "message": str(e)}
