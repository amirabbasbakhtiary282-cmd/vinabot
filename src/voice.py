import os
import sys
import json
import queue
import threading
import time


class VinaVoice:

    def __init__(self):
        self.recognizer = None
        self.tts_engine = None
        self.audio_queue = queue.Queue()
        self.isListening = False
        self.wake_word_active = False
        self.is_android = self._check_android()
        self._init_stt()

    def _check_android(self):
        try:
            return os.path.exists('/system/build.prop')
        except Exception:
            return False

    def _init_stt(self):
        try:
            from vosk import Model, KaldiRecognizer, SetLogLevel
            SetLogLevel(-1)

            model_paths = [
                os.path.join(os.path.dirname(os.path.dirname(__file__)), 'models', 'vosk-model-small-fa'),
                '/data/data/org.vinabot/files/models/vosk-model-small-fa',
                os.path.expanduser('~/.vin/models/vosk-model-small-fa'),
            ]

            model_path = None
            for p in model_paths:
                if os.path.exists(p):
                    model_path = p
                    break

            if model_path:
                self.vosk_model = Model(model_path)
                self.recognizer = KaldiRecognizer(self.vosk_model, 16000)
            else:
                self.vosk_model = None
                self.recognizer = None
        except ImportError:
            self.vosk_model = None
            self.recognizer = None
        except Exception:
            self.vosk_model = None
            self.recognizer = None

    def speak(self, text):
        if not text:
            return
        print(f"[وینا]: {text}")

    def listen(self, timeout=10):
        try:
            if self.recognizer and not self.is_android:
                return self._listen_vosk(timeout)
            else:
                return self._listen_text_fallback()
        except Exception as e:
            print(f"خطای تشخیص صدا: {e}")
            return None

    def _listen_vosk(self, timeout=10):
        try:
            import sounddevice as sd

            self.isListening = True

            def audio_callback(indata, frames, time_info, status):
                self.audio_queue.put(bytes(indata))

            with sd.RawInputStream(samplerate=16000, blocksize=8000, dtype='int16',
                                   channels=1, callback=audio_callback):
                start_time = time.time()
                while time.time() - start_time < timeout:
                    try:
                        data = self.audio_queue.get(timeout=0.5)
                        if self.recognizer.AcceptWaveform(data):
                            result = json.loads(self.recognizer.Result())
                            text = result.get('text', '')
                            if text:
                                self.isListening = False
                                return text
                    except queue.Empty:
                        continue

                final = json.loads(self.recognizer.FinalResult())
                self.isListening = False
                return final.get('text', '')
        except ImportError:
            self.isListening = False
            return self._listen_text_fallback()
        except Exception:
            self.isListening = False
            return None

    def _listen_text_fallback(self):
        try:
            text = input("پیام خود را بنویسید: ")
            return text.strip() if text.strip() else None
        except (EOFError, KeyboardInterrupt):
            return None

    def listen_for_wake_word(self, wake_word="هی وینا"):
        return False

    def stop_speaking(self):
        pass

    def get_audio_levels(self):
        return [0] * 30
