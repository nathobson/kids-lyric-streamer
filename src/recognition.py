"""ACRCloud song recognition integration."""

import base64
import hashlib
import hmac
import time
import requests
from dataclasses import dataclass
from typing import Optional

from .config import ACRCLOUD_HOST, ACRCLOUD_ACCESS_KEY, ACRCLOUD_ACCESS_SECRET


@dataclass
class RecognitionResult:
    """Result from song recognition."""
    success: bool
    artist: str = ""
    title: str = ""
    album: str = ""
    duration_ms: int = 0
    play_offset_ms: int = 0
    album_art_url: str = ""
    error_message: str = ""


def _generate_signature(string_to_sign: str, access_secret: str) -> str:
    """Generate HMAC-SHA1 signature for ACRCloud API."""
    signature = hmac.new(
        access_secret.encode('utf-8'),
        string_to_sign.encode('utf-8'),
        hashlib.sha1
    ).digest()
    return base64.b64encode(signature).decode('utf-8')


def recognize_song(audio_wav_bytes: bytes) -> RecognitionResult:
    """Recognize a song from audio data using ACRCloud.
    
    Args:
        audio_wav_bytes: Audio data in WAV format as bytes.
    
    Returns:
        RecognitionResult with song info if successful.
    """
    if not ACRCLOUD_ACCESS_KEY or not ACRCLOUD_ACCESS_SECRET:
        return RecognitionResult(
            success=False,
            error_message="ACRCloud credentials not configured. Check your .env file."
        )
    
    # API parameters
    http_method = "POST"
    http_uri = "/v1/identify"
    data_type = "audio"
    signature_version = "1"
    timestamp = str(int(time.time()))
    
    # Generate signature
    string_to_sign = f"{http_method}\n{http_uri}\n{ACRCLOUD_ACCESS_KEY}\n{data_type}\n{signature_version}\n{timestamp}"
    signature = _generate_signature(string_to_sign, ACRCLOUD_ACCESS_SECRET)
    
    # Prepare request
    files = {
        'sample': ('audio.wav', audio_wav_bytes, 'audio/wav')
    }
    data = {
        'access_key': ACRCLOUD_ACCESS_KEY,
        'data_type': data_type,
        'signature_version': signature_version,
        'signature': signature,
        'sample_bytes': len(audio_wav_bytes),
        'timestamp': timestamp
    }
    
    try:
        url = f"https://{ACRCLOUD_HOST}{http_uri}"
        response = requests.post(url, files=files, data=data, timeout=15)
        response.raise_for_status()
        result = response.json()
    except requests.RequestException as e:
        return RecognitionResult(
            success=False,
            error_message=f"Network error: {str(e)}"
        )
    except ValueError as e:
        return RecognitionResult(
            success=False,
            error_message=f"Invalid response: {str(e)}"
        )
    
    # Parse response
    status = result.get('status', {})
    status_code = status.get('code', -1)
    
    if status_code != 0:
        # No match found or error
        return RecognitionResult(
            success=False,
            error_message=status.get('msg', 'Unknown error')
        )
    
    # Extract music metadata
    metadata = result.get('metadata', {})
    music_list = metadata.get('music', [])
    
    if not music_list:
        return RecognitionResult(
            success=False,
            error_message="No music found in response"
        )
    
    music = music_list[0]  # Take first (best) match
    
    # Get artist (can be array of artists)
    artists = music.get('artists', [])
    artist_name = artists[0].get('name', '') if artists else ''
    
    # Get album
    album_info = music.get('album', {})
    album_name = album_info.get('name', '')
    
    # Get album art if available
    album_art_url = ""
    external_metadata = music.get('external_metadata', {})
    if 'spotify' in external_metadata:
        spotify_album = external_metadata['spotify'].get('album', {})
        images = spotify_album.get('images', [])
        if images:
            album_art_url = images[0].get('url', '')
    
    return RecognitionResult(
        success=True,
        artist=artist_name,
        title=music.get('title', ''),
        album=album_name,
        duration_ms=music.get('duration_ms', 0),
        play_offset_ms=music.get('play_offset_ms', 0),
        album_art_url=album_art_url
    )


if __name__ == "__main__":
    # Test recognition (requires actual audio input)
    from .audio import capture_audio, audio_to_wav_bytes, check_audio_level
    
    print("Recording audio for recognition test...")
    audio = capture_audio(duration=5)
    
    if not check_audio_level(audio):
        print("Warning: Audio level is low. Make sure music is playing.")
    
    wav_bytes = audio_to_wav_bytes(audio)
    print(f"Sending {len(wav_bytes)} bytes to ACRCloud...")
    
    result = recognize_song(wav_bytes)
    
    if result.success:
        print(f"\n🎵 Recognized: {result.artist} - {result.title}")
        print(f"   Album: {result.album}")
        print(f"   Duration: {result.duration_ms // 1000}s")
        print(f"   Position: {result.play_offset_ms // 1000}s into song")
    else:
        print(f"\n❌ Recognition failed: {result.error_message}")

