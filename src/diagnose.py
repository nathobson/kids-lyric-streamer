#!/usr/bin/env python3
"""Diagnostic script to test each component individually."""

import sys
import os

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_config():
    """Test configuration loading."""
    print("=" * 50)
    print("1. CONFIGURATION TEST")
    print("=" * 50)
    
    from src.config import (
        ACRCLOUD_HOST, ACRCLOUD_ACCESS_KEY, ACRCLOUD_ACCESS_SECRET,
        SAMPLE_RATE, RECORD_SECONDS
    )
    
    print(f"   Sample rate: {SAMPLE_RATE} Hz")
    print(f"   Record duration: {RECORD_SECONDS} seconds")
    print(f"   ACRCloud host: {ACRCLOUD_HOST}")
    
    if ACRCLOUD_ACCESS_KEY:
        print(f"   ACRCloud key: {ACRCLOUD_ACCESS_KEY[:8]}...{ACRCLOUD_ACCESS_KEY[-4:]}")
    else:
        print("   ❌ ACRCloud key: NOT SET")
        print("      → Copy env.example to .env and add your credentials!")
        return False
    
    if ACRCLOUD_ACCESS_SECRET:
        print(f"   ACRCloud secret: {ACRCLOUD_ACCESS_SECRET[:4]}...{ACRCLOUD_ACCESS_SECRET[-4:]}")
    else:
        print("   ❌ ACRCloud secret: NOT SET")
        return False
    
    print("   ✓ Configuration OK")
    return True


def test_audio_devices():
    """Test audio device listing."""
    print()
    print("=" * 50)
    print("2. AUDIO DEVICES TEST")
    print("=" * 50)
    
    from src.audio import list_audio_devices, get_default_input_device
    
    devices = list_audio_devices()
    if not devices:
        print("   ❌ No audio input devices found!")
        return False
    
    print(f"   Found {len(devices)} input device(s):")
    for d in devices:
        print(f"      [{d['index']}] {d['name']} ({d['channels']} ch)")
    
    default = get_default_input_device()
    print(f"   Default input device: {default}")
    print("   ✓ Audio devices OK")
    return True


def test_audio_capture():
    """Test audio capture."""
    print()
    print("=" * 50)
    print("3. AUDIO CAPTURE TEST")
    print("=" * 50)
    
    from src.audio import capture_audio, check_audio_level, audio_to_wav_bytes
    from src.config import RECORD_SECONDS
    
    print(f"   Recording {RECORD_SECONDS} seconds of audio...")
    print("   (Play some music near your microphone!)")
    
    try:
        audio = capture_audio()
        print(f"   Captured {len(audio)} samples")
        
        # Check audio level
        import numpy as np
        rms = np.sqrt(np.mean(audio.astype(np.float32) ** 2))
        print(f"   Audio RMS level: {rms:.1f}")
        
        if rms < 100:
            print("   ⚠️  Audio level is VERY LOW - might be silence")
            print("      → Check microphone permissions in System Preferences")
            print("      → Make sure music is playing loudly")
        elif rms < 500:
            print("   ⚠️  Audio level is LOW - might not recognize well")
        else:
            print("   ✓ Audio level looks good!")
        
        # Check if it converts to WAV OK
        wav_bytes = audio_to_wav_bytes(audio)
        print(f"   WAV size: {len(wav_bytes)} bytes")
        
        return rms >= 100
        
    except Exception as e:
        print(f"   ❌ Audio capture failed: {e}")
        return False


def test_recognition():
    """Test ACRCloud recognition."""
    print()
    print("=" * 50)
    print("4. SONG RECOGNITION TEST")
    print("=" * 50)
    
    from src.audio import capture_audio, audio_to_wav_bytes
    from src.recognition import recognize_song
    
    print("   Recording audio for recognition...")
    print("   (Make sure music is playing!)")
    
    audio = capture_audio()
    wav_bytes = audio_to_wav_bytes(audio)
    
    print(f"   Sending {len(wav_bytes)} bytes to ACRCloud...")
    result = recognize_song(wav_bytes)
    
    if result.success:
        print(f"   ✓ Recognized: {result.artist} - {result.title}")
        print(f"     Album: {result.album}")
        print(f"     Position: {result.play_offset_ms // 1000}s into song")
        return True
    else:
        print(f"   ❌ Recognition failed: {result.error_message}")
        if "credentials" in result.error_message.lower():
            print("      → Check your .env file has correct ACRCloud credentials")
        elif "No sound detected" in result.error_message:
            print("      → Make sure music is playing and microphone can hear it")
        return False


def test_lyrics():
    """Test lyrics fetching."""
    print()
    print("=" * 50)
    print("5. LYRICS FETCH TEST")
    print("=" * 50)
    
    from src.lyrics import fetch_lyrics
    
    print("   Fetching lyrics for 'Coldplay - Yellow'...")
    lyrics = fetch_lyrics("Coldplay", "Yellow")
    
    if lyrics:
        print(f"   ✓ Found {len(lyrics.lines)} lines (synced: {lyrics.synced})")
        if lyrics.lines:
            print(f"     First line: '{lyrics.lines[0].text}'")
        return True
    else:
        print("   ❌ Could not fetch lyrics")
        print("      → Check internet connection")
        return False


def main():
    """Run all diagnostics."""
    print()
    print("🔍 LYRICS DISPLAY DIAGNOSTICS")
    print("=" * 50)
    print()
    
    results = {}
    
    # Test 1: Config
    results['config'] = test_config()
    
    # Test 2: Audio devices
    results['devices'] = test_audio_devices()
    
    # Test 3: Audio capture (only if devices OK)
    if results['devices']:
        results['capture'] = test_audio_capture()
    else:
        results['capture'] = False
    
    # Test 4: Recognition (only if config and capture OK)
    if results['config'] and results['capture']:
        print()
        input("   Press Enter to test recognition (make sure music is playing)...")
        results['recognition'] = test_recognition()
    else:
        results['recognition'] = False
        print()
        print("=" * 50)
        print("4. SONG RECOGNITION TEST")
        print("=" * 50)
        print("   ⏭️  Skipped (fix config/audio first)")
    
    # Test 5: Lyrics
    results['lyrics'] = test_lyrics()
    
    # Summary
    print()
    print("=" * 50)
    print("SUMMARY")
    print("=" * 50)
    
    all_ok = all(results.values())
    for test, passed in results.items():
        status = "✓" if passed else "❌"
        print(f"   {status} {test}")
    
    print()
    if all_ok:
        print("🎉 All tests passed! The app should work.")
    else:
        print("⚠️  Some tests failed. Fix the issues above and try again.")
    
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())

