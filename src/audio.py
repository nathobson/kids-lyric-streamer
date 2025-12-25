"""Audio capture module using sounddevice."""

import sounddevice as sd
import numpy as np
from io import BytesIO
import wave
import struct
from typing import List, Dict, Optional

from .config import SAMPLE_RATE, CHANNELS, RECORD_SECONDS


def list_audio_devices() -> List[Dict]:
    """List all available audio input devices.
    
    Returns:
        List of device info dictionaries with 'index', 'name', and 'channels'.
    """
    devices = sd.query_devices()
    input_devices = []
    
    for i, device in enumerate(devices):
        if device['max_input_channels'] > 0:
            input_devices.append({
                'index': i,
                'name': device['name'],
                'channels': device['max_input_channels'],
                'sample_rate': device['default_samplerate']
            })
    
    return input_devices


def get_default_input_device() -> Optional[int]:
    """Get the default input device index.
    
    Returns:
        Device index or None if no input device available.
    """
    try:
        device_info = sd.query_devices(kind='input')
        return sd.default.device[0]  # Input device index
    except sd.PortAudioError:
        return None


def capture_audio(duration: float = RECORD_SECONDS, 
                  device: Optional[int] = None,
                  sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Capture audio from microphone.
    
    Args:
        duration: Recording duration in seconds.
        device: Audio device index (None for default).
        sample_rate: Sample rate in Hz.
    
    Returns:
        Audio data as numpy array (mono, int16).
    """
    # Record audio
    audio_data = sd.rec(
        int(duration * sample_rate),
        samplerate=sample_rate,
        channels=CHANNELS,
        dtype=np.int16,
        device=device
    )
    sd.wait()  # Wait for recording to complete
    
    return audio_data.flatten()


def audio_to_wav_bytes(audio_data: np.ndarray, 
                       sample_rate: int = SAMPLE_RATE) -> bytes:
    """Convert numpy audio array to WAV bytes for API submission.
    
    Args:
        audio_data: Audio data as numpy array (mono, int16).
        sample_rate: Sample rate in Hz.
    
    Returns:
        WAV file as bytes.
    """
    buffer = BytesIO()
    
    with wave.open(buffer, 'wb') as wav_file:
        wav_file.setnchannels(CHANNELS)
        wav_file.setsampwidth(2)  # 16-bit = 2 bytes
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio_data.tobytes())
    
    buffer.seek(0)
    return buffer.read()


def check_audio_level(audio_data: np.ndarray, threshold: float = 500) -> bool:
    """Check if audio has significant sound (not silence).
    
    Args:
        audio_data: Audio data as numpy array.
        threshold: RMS threshold for detecting sound.
    
    Returns:
        True if audio level is above threshold.
    """
    rms = np.sqrt(np.mean(audio_data.astype(np.float32) ** 2))
    return rms > threshold


if __name__ == "__main__":
    # Test audio capture
    print("Available audio input devices:")
    for device in list_audio_devices():
        print(f"  [{device['index']}] {device['name']} ({device['channels']} channels)")
    
    print(f"\nRecording {RECORD_SECONDS} seconds of audio...")
    audio = capture_audio()
    print(f"Captured {len(audio)} samples")
    
    # Check audio level
    if check_audio_level(audio):
        print("Audio level: Good (sound detected)")
    else:
        print("Audio level: Low (mostly silence)")
    
    # Convert to WAV bytes
    wav_bytes = audio_to_wav_bytes(audio)
    print(f"WAV size: {len(wav_bytes)} bytes")

