import os
import platform
import wave
from pathlib import Path
import threading
import time

class AudioManager:
    def __init__(self):
        self.is_playing = False
        self.current_audio = None
        self.volume = 0.5
        self.audio_thread = None
        self.stop_signal = False
        self.fade_duration = 5000
        self.audio_available = True
        self.pygame_initialized = False
        self.platform_name = platform.system()
        
        self.assets_path = Path(__file__).parent.parent / "assets" / "audio"
        self.om_path = self._find_audio_file("om")
        self.eyes_closed_path = self._find_audio_file("eyes_closed")
        self.eyes_open_path = self._find_audio_file("eyes_open")
        
        self._configure_audio_backend()
        self._ensure_audio_files()
    
    def _find_audio_file(self, audio_type):
        """Find audio file in assets/audio folder"""
        self.assets_path.mkdir(parents=True, exist_ok=True)
        
        for filename in [f"{audio_type}.mp3", f"{audio_type}.wav", f"{audio_type}.MP3", f"{audio_type}.WAV"]:
            file_path = self.assets_path / filename
            if file_path.exists():
                print(f"[v0] Found {audio_type} audio: {file_path}")
                return file_path
        
        return None
    
    def _configure_audio_backend(self):
        """Configure SDL audio backend for Raspberry Pi and similar Linux ARM devices."""
        if self.platform_name == "Linux" and platform.machine().startswith(("arm", "aarch")):
            os.environ.setdefault("SDL_AUDIODRIVER", "alsa")
            os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

    def _init_pygame_mixer(self):
        """Initialize pygame mixer once and track availability."""
        if self.pygame_initialized:
            return self.audio_available

        try:
            import pygame
            pygame.init()
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=22050, size=-16, channels=2)
            self.pygame_initialized = True
            self.audio_available = True
        except Exception as e:
            self.audio_available = False
            self.pygame_initialized = False
            print(f"[v0] pygame init failed: {e}")
        return self.audio_available

    def _ensure_audio_files(self):
        """Create placeholder audio files if they don't exist."""
        self.assets_path.mkdir(parents=True, exist_ok=True)

        if not self.eyes_closed_path or not self.eyes_closed_path.exists():
            self._create_beep_wav(self.assets_path / "eyes_closed.wav", frequency=800, duration=0.5)
            self.eyes_closed_path = self.assets_path / "eyes_closed.wav"

        if not self.eyes_open_path or not self.eyes_open_path.exists():
            self._create_beep_wav(self.assets_path / "eyes_open.wav", frequency=600, duration=0.3)
            self.eyes_open_path = self.assets_path / "eyes_open.wav"

        # Initialize mixer if audio is available
        self._init_pygame_mixer()
        print("[v0] Audio files ready")
    
    def _create_beep_wav(self, filepath, frequency=440, duration=0.5, sample_rate=22050):
        """Create a simple beep sound as WAV file"""
        try:
            import math
            
            num_samples = int(sample_rate * duration)
            frames = []
            
            for i in range(num_samples):
                sample = int(32767 * 0.3 * math.sin(2.0 * math.pi * frequency * i / sample_rate))
                frames.append(sample.to_bytes(2, 'little', signed=True))
            
            with wave.open(str(filepath), 'wb') as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(b''.join(frames))
            
            print(f"[v0] Created beep sound: {filepath}")
        except Exception as e:
            print(f"[v0] Error creating beep: {e}")
    
    def _play_audio_loop(self, audio_path):
        """Background thread for audio playback."""
        if not self._init_pygame_mixer():
            print("[v0] Audio loop aborted: mixer unavailable")
            return

        try:
            import pygame
            sound = pygame.mixer.Sound(str(audio_path))
            sound.set_volume(self.volume)

            # Play sound on a dedicated channel and loop until stop_signal
            channel = sound.play(-1)
            if channel is None:
                channel = pygame.mixer.find_channel(True)

            while not self.stop_signal:
                try:
                    busy = channel.get_busy() if channel is not None else False
                except Exception:
                    busy = False

                if not busy:
                    channel = sound.play(-1)
                    if channel is None:
                        channel = pygame.mixer.find_channel(True)

                time.sleep(0.1)

            try:
                if channel is not None:
                    channel.stop()
            except Exception:
                pass
        except Exception as e:
            print(f"[v0] Audio thread error: {e}")
    
    def play_om(self):
        """Start Om meditation sound in background thread."""
        if not self.audio_available:
            print("[v0] Audio unavailable: cannot play Om")
            return False

        if not self.om_path or not self.om_path.exists():
            print(f"[v0] ERROR: Om audio file not found")
            return False
        
        if self.is_playing and self.current_audio == "om":
            return False
        
        self.stop_om()
        
        self.is_playing = True
        self.current_audio = "om"
        self.stop_signal = False
        self.audio_thread = threading.Thread(target=self._play_audio_loop, args=(self.om_path,), daemon=True)
        self.audio_thread.start()
        print("[v0] OM PLAYING")
        return True
    
    def play_eyes_closed_alert(self):
        """Play alert when eyes are detected as closed."""
        if not self.audio_available:
            return False

        if not self.eyes_closed_path or not self.eyes_closed_path.exists():
            return False
        
        if not self._init_pygame_mixer():
            return False

        try:
            import pygame
            sound = pygame.mixer.Sound(str(self.eyes_closed_path))
            sound.set_volume(self.volume)
            sound.play()
            print("[v0] EYES CLOSED ALERT PLAYED")
            return True
        except Exception as e:
            print(f"[v0] Error playing eyes closed alert: {e}")
            return False
    
    def play_eyes_open_alert(self):
        """Play alert when eyes are open."""
        if not self.audio_available:
            return False

        if not self.eyes_open_path or not self.eyes_open_path.exists():
            return False
        
        if not self._init_pygame_mixer():
            return False

        try:
            import pygame
            sound = pygame.mixer.Sound(str(self.eyes_open_path))
            sound.set_volume(self.volume)
            sound.play()
            print("[v0] EYES OPEN ALERT PLAYED")
            return True
        except Exception as e:
            print(f"[v0] Error playing eyes open alert: {e}")
            return False
    
    def stop_om(self):
        """Stop Om sound."""
        if self.is_playing:
            self.stop_signal = True
            self.is_playing = False
            self.current_audio = None
            time.sleep(0.2)
            
            try:
                import pygame
                if pygame.mixer.get_init():
                    pygame.mixer.stop()
            except Exception:
                pass
            
            print("[v0] OM STOPPED")
    
    def set_volume(self, level):
        """Set volume level (0.0 to 1.0)"""
        self.volume = max(0, min(1, level))
