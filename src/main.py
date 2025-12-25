#!/usr/bin/env python3
"""Main entry point for lyrics display application."""

import time
import threading
import argparse
from typing import Optional
from dataclasses import dataclass

from .audio import capture_audio, audio_to_wav_bytes, check_audio_level
from .recognition import recognize_song, RecognitionResult
from .lyrics import fetch_lyrics, get_current_line_index, LyricsData
from .display import LyricsDisplay, DisplayState
from .config import (
    RECOGNITION_INTERVAL, RECORD_SECONDS,
    get_time_offset, adjust_time_offset
)


@dataclass
class AppState:
    """Application state."""
    current_artist: str = ""
    current_title: str = ""
    song_start_time: float = 0.0  # Time when song started (adjusted for play_offset)
    lyrics: Optional[LyricsData] = None
    last_recognition_time: float = 0.0
    recognition_in_progress: bool = False
    force_recognize: bool = False


class LyricsApp:
    """Main application class."""
    
    def __init__(self, fullscreen: bool = True, audio_device: Optional[int] = None):
        """Initialize the application.
        
        Args:
            fullscreen: Start in fullscreen mode.
            audio_device: Audio input device index (None for default).
        """
        self.display = LyricsDisplay(fullscreen=fullscreen)
        self.audio_device = audio_device
        self.state = AppState()
        self.running = False
        
        # Recognition thread
        self._recognition_thread: Optional[threading.Thread] = None
        self._recognition_result: Optional[RecognitionResult] = None
        self._recognition_lock = threading.Lock()
    
    def _recognition_worker(self):
        """Background worker for audio recognition."""
        try:
            # Capture audio
            audio = capture_audio(duration=RECORD_SECONDS, device=self.audio_device)
            
            # Check if there's actual sound
            if not check_audio_level(audio):
                with self._recognition_lock:
                    self._recognition_result = RecognitionResult(
                        success=False,
                        error_message="No sound detected"
                    )
                return
            
            # Convert to WAV
            wav_bytes = audio_to_wav_bytes(audio)
            
            # Send to ACRCloud
            result = recognize_song(wav_bytes)
            
            with self._recognition_lock:
                self._recognition_result = result
                
        except Exception as e:
            with self._recognition_lock:
                self._recognition_result = RecognitionResult(
                    success=False,
                    error_message=str(e)
                )
    
    def _start_recognition(self):
        """Start background recognition if not already running."""
        if self.state.recognition_in_progress:
            return
        
        self.state.recognition_in_progress = True
        self.state.force_recognize = False
        self._recognition_result = None
        
        self._recognition_thread = threading.Thread(
            target=self._recognition_worker,
            daemon=True
        )
        self._recognition_thread.start()
        
        self.display.set_state(DisplayState.RECOGNIZING)
    
    def _check_recognition_complete(self):
        """Check if recognition completed and process result."""
        if not self.state.recognition_in_progress:
            return
        
        # Check if thread finished
        if self._recognition_thread and self._recognition_thread.is_alive():
            return
        
        self.state.recognition_in_progress = False
        self.state.last_recognition_time = time.time()
        
        with self._recognition_lock:
            result = self._recognition_result
        
        if result is None:
            return
        
        if not result.success:
            # No match or error
            if self.state.current_title:
                # Keep showing current song if we have one
                self.display.set_state(DisplayState.MATCHED)
            else:
                self.display.set_state(DisplayState.NO_MATCH)
            return
        
        # Check if it's a new song
        is_new_song = (
            result.artist != self.state.current_artist or
            result.title != self.state.current_title
        )
        
        if is_new_song:
            # Update current song
            self.state.current_artist = result.artist
            self.state.current_title = result.title
            
            # Calculate song start time based on play offset
            self.state.song_start_time = time.time() - (result.play_offset_ms / 1000)
            
            # Fetch lyrics
            self.display.set_song(result.artist, result.title, result.album)
            lyrics = fetch_lyrics(result.artist, result.title, result.album)
            
            if lyrics and lyrics.lines:
                self.state.lyrics = lyrics
                self.display.set_lyrics(lyrics)
                self.display.set_state(DisplayState.MATCHED)
            else:
                self.state.lyrics = None
                self.display.set_lyrics(None)
                self.display.set_state(DisplayState.NO_LYRICS)
        else:
            # Same song - just update the play position
            self.state.song_start_time = time.time() - (result.play_offset_ms / 1000)
            self.display.set_state(DisplayState.MATCHED)
    
    def _update_lyrics_position(self):
        """Update current lyric line based on playback position."""
        if not self.state.lyrics or not self.state.lyrics.synced:
            return
        
        # Calculate current position in song
        elapsed = time.time() - self.state.song_start_time
        position_ms = int(elapsed * 1000) + get_time_offset()
        
        # Find current line
        line_index = get_current_line_index(self.state.lyrics, position_ms)
        self.display.update_position(line_index)
    
    def run(self):
        """Main application loop."""
        self.running = True
        self.display.set_state(DisplayState.LISTENING)
        
        # Start initial recognition
        self._start_recognition()
        
        while self.running:
            # Handle pygame events
            events = self.display.handle_events()
            
            if events['quit']:
                self.running = False
                continue
            
            if events['toggle_fullscreen']:
                self.display.toggle_fullscreen()
            
            if events['offset_adjust'] != 0:
                new_offset = adjust_time_offset(events['offset_adjust'])
                self.display.time_offset_ms = new_offset
            
            if events['force_recognize']:
                self.state.force_recognize = True
            
            # Check if recognition thread completed
            self._check_recognition_complete()
            
            # Start new recognition if needed
            time_since_last = time.time() - self.state.last_recognition_time
            should_recognize = (
                self.state.force_recognize or
                (not self.state.recognition_in_progress and 
                 time_since_last >= RECOGNITION_INTERVAL)
            )
            
            if should_recognize:
                self._start_recognition()
            
            # Update lyrics position if we have synced lyrics
            if self.display.state == DisplayState.MATCHED:
                self._update_lyrics_position()
            
            # Render frame
            self.display.render()
        
        # Cleanup
        self.display.cleanup()


def main():
    """Entry point."""
    parser = argparse.ArgumentParser(
        description="Lyrics Display - Music recognition and synced lyrics"
    )
    parser.add_argument(
        "--windowed", "-w",
        action="store_true",
        help="Run in windowed mode instead of fullscreen"
    )
    parser.add_argument(
        "--device", "-d",
        type=int,
        default=None,
        help="Audio input device index"
    )
    parser.add_argument(
        "--list-devices", "-l",
        action="store_true",
        help="List available audio devices and exit"
    )
    
    args = parser.parse_args()
    
    if args.list_devices:
        from .audio import list_audio_devices
        print("Available audio input devices:")
        for device in list_audio_devices():
            print(f"  [{device['index']}] {device['name']}")
        return
    
    app = LyricsApp(
        fullscreen=not args.windowed,
        audio_device=args.device
    )
    
    try:
        app.run()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()

