"""Pygame display engine for lyrics rendering."""

import pygame
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
from enum import Enum

from .config import (
    DISPLAY_FPS, BACKGROUND_COLOR, TEXT_COLOR, DIM_TEXT_COLOR,
    FONT_SIZE_LARGE, FONT_SIZE_SMALL, FONTS_DIR
)
from .lyrics import LyricsData, LyricLine


class DisplayState(Enum):
    """Current state of the display."""
    LISTENING = "listening"
    RECOGNIZING = "recognizing"
    MATCHED = "matched"
    NO_MATCH = "no_match"
    NO_LYRICS = "no_lyrics"
    ERROR = "error"


@dataclass
class NowPlaying:
    """Currently playing song info."""
    artist: str
    title: str
    album: str = ""


class LyricsDisplay:
    """Pygame-based lyrics display."""
    
    def __init__(self, fullscreen: bool = True):
        """Initialize the display.
        
        Args:
            fullscreen: Whether to start in fullscreen mode.
        """
        # Initialize pygame (only display, not audio)
        pygame.init()
        pygame.display.set_caption("Lyrics Display")
        
        # Get display info
        display_info = pygame.display.Info()
        self.screen_width = display_info.current_w
        self.screen_height = display_info.current_h
        
        # Create display
        self.fullscreen = fullscreen
        if fullscreen:
            self.screen = pygame.display.set_mode(
                (self.screen_width, self.screen_height),
                pygame.FULLSCREEN
            )
        else:
            # Windowed mode at 720p
            self.screen_width = 1280
            self.screen_height = 720
            self.screen = pygame.display.set_mode(
                (self.screen_width, self.screen_height)
            )
        
        # Load fonts
        self._load_fonts()
        
        # State
        self.state = DisplayState.LISTENING
        self.now_playing: Optional[NowPlaying] = None
        self.lyrics: Optional[LyricsData] = None
        self.current_line_index = -1
        self.time_offset_ms = 0
        self.status_message = ""
        
        # Clock for FPS control
        self.clock = pygame.time.Clock()
    
    def _load_fonts(self):
        """Load fonts, falling back to system fonts if custom not found."""
        # Try to find a custom font in the fonts directory
        custom_fonts = list(FONTS_DIR.glob("*.ttf")) + list(FONTS_DIR.glob("*.otf"))
        
        if custom_fonts:
            font_path = str(custom_fonts[0])
            self.font_large = pygame.font.Font(font_path, FONT_SIZE_LARGE)
            self.font_small = pygame.font.Font(font_path, FONT_SIZE_SMALL)
        else:
            # Use system sans-serif font
            self.font_large = pygame.font.SysFont("sans-serif", FONT_SIZE_LARGE)
            self.font_small = pygame.font.SysFont("sans-serif", FONT_SIZE_SMALL)
    
    def toggle_fullscreen(self):
        """Toggle between fullscreen and windowed mode."""
        self.fullscreen = not self.fullscreen
        
        if self.fullscreen:
            display_info = pygame.display.Info()
            self.screen_width = display_info.current_w
            self.screen_height = display_info.current_h
            self.screen = pygame.display.set_mode(
                (self.screen_width, self.screen_height),
                pygame.FULLSCREEN
            )
        else:
            self.screen_width = 1280
            self.screen_height = 720
            self.screen = pygame.display.set_mode(
                (self.screen_width, self.screen_height)
            )
    
    def set_state(self, state: DisplayState, message: str = ""):
        """Update display state.
        
        Args:
            state: New display state.
            message: Optional status message.
        """
        self.state = state
        self.status_message = message
    
    def set_song(self, artist: str, title: str, album: str = ""):
        """Set currently playing song.
        
        Args:
            artist: Artist name.
            title: Song title.
            album: Album name.
        """
        self.now_playing = NowPlaying(artist=artist, title=title, album=album)
    
    def set_lyrics(self, lyrics: Optional[LyricsData]):
        """Set lyrics data.
        
        Args:
            lyrics: LyricsData object or None.
        """
        self.lyrics = lyrics
        self.current_line_index = -1
    
    def update_position(self, line_index: int):
        """Update current lyric line.
        
        Args:
            line_index: Index of current line in lyrics.
        """
        self.current_line_index = line_index
    
    def _render_centered_text(self, text: str, font: pygame.font.Font, 
                              color: tuple, y: int, max_width: int = 0):
        """Render text centered horizontally.
        
        Args:
            text: Text to render.
            font: Font to use.
            color: Text color.
            y: Y position.
            max_width: Maximum width (0 for no limit).
        """
        if max_width == 0:
            max_width = self.screen_width - 100  # 50px padding each side
        
        # Word wrap if needed
        words = text.split()
        lines = []
        current_line = ""
        
        for word in words:
            test_line = f"{current_line} {word}".strip()
            test_surface = font.render(test_line, True, color)
            
            if test_surface.get_width() <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        
        if current_line:
            lines.append(current_line)
        
        # Render each line
        line_height = font.get_linesize()
        total_height = len(lines) * line_height
        start_y = y - total_height // 2
        
        for i, line in enumerate(lines):
            surface = font.render(line, True, color)
            x = (self.screen_width - surface.get_width()) // 2
            self.screen.blit(surface, (x, start_y + i * line_height))
    
    def _render_status(self):
        """Render status screen (listening, recognizing, etc.)."""
        center_y = self.screen_height // 2
        
        if self.state == DisplayState.LISTENING:
            self._render_centered_text("Listening...", self.font_large, 
                                       DIM_TEXT_COLOR, center_y)
        elif self.state == DisplayState.RECOGNIZING:
            self._render_centered_text("Recognizing...", self.font_large,
                                       DIM_TEXT_COLOR, center_y)
        elif self.state == DisplayState.NO_MATCH:
            self._render_centered_text("No song detected", self.font_large,
                                       DIM_TEXT_COLOR, center_y)
        elif self.state == DisplayState.NO_LYRICS:
            self._render_centered_text("No lyrics available", self.font_large,
                                       DIM_TEXT_COLOR, center_y)
            if self.now_playing:
                self._render_now_playing()
        elif self.state == DisplayState.ERROR:
            self._render_centered_text(self.status_message or "Error",
                                       self.font_large, (200, 50, 50), center_y)
    
    def _render_lyrics(self):
        """Render synced lyrics display."""
        if not self.lyrics or not self.lyrics.lines:
            return
        
        center_y = self.screen_height // 2
        line_spacing = 80  # Space between lines
        
        # Get lines to display
        lines = self.lyrics.lines
        current_idx = max(0, self.current_line_index)
        
        # Render previous line (if exists)
        if current_idx > 0:
            prev_line = lines[current_idx - 1]
            self._render_centered_text(
                prev_line.text, self.font_small, DIM_TEXT_COLOR,
                center_y - line_spacing
            )
        
        # Render current line
        if current_idx < len(lines):
            current_line = lines[current_idx]
            self._render_centered_text(
                current_line.text, self.font_large, TEXT_COLOR, center_y
            )
        
        # Render next line (if exists)
        if current_idx + 1 < len(lines):
            next_line = lines[current_idx + 1]
            self._render_centered_text(
                next_line.text, self.font_small, DIM_TEXT_COLOR,
                center_y + line_spacing
            )
        
        # Render now playing info
        self._render_now_playing()
    
    def _render_now_playing(self):
        """Render now playing info at bottom of screen."""
        if not self.now_playing:
            return
        
        text = f"{self.now_playing.artist} - {self.now_playing.title}"
        y = self.screen_height - 40
        
        self._render_centered_text(text, self.font_small, DIM_TEXT_COLOR, y)
    
    def _render_offset_indicator(self):
        """Render time offset indicator if non-zero."""
        if self.time_offset_ms == 0:
            return
        
        offset_sec = self.time_offset_ms / 1000
        sign = "+" if offset_sec > 0 else ""
        text = f"Offset: {sign}{offset_sec:.1f}s"
        
        surface = self.font_small.render(text, True, DIM_TEXT_COLOR)
        self.screen.blit(surface, (20, 20))
    
    def render(self):
        """Render the current frame."""
        # Clear screen
        self.screen.fill(BACKGROUND_COLOR)
        
        # Render based on state
        if self.state == DisplayState.MATCHED and self.lyrics:
            self._render_lyrics()
        else:
            self._render_status()
        
        # Always show offset if non-zero
        self._render_offset_indicator()
        
        # Update display
        pygame.display.flip()
        
        # Control frame rate
        self.clock.tick(DISPLAY_FPS)
    
    def handle_events(self) -> dict:
        """Process pygame events.
        
        Returns:
            Dictionary with event flags:
            - 'quit': True if should quit
            - 'offset_adjust': Offset adjustment in ms (or 0)
            - 'force_recognize': True if R pressed
            - 'toggle_fullscreen': True if F pressed
        """
        result = {
            'quit': False,
            'offset_adjust': 0,
            'force_recognize': False,
            'toggle_fullscreen': False
        }
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                result['quit'] = True
            
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_q, pygame.K_ESCAPE):
                    result['quit'] = True
                
                elif event.key == pygame.K_LEFT:
                    result['offset_adjust'] = -500  # -0.5 seconds
                
                elif event.key == pygame.K_RIGHT:
                    result['offset_adjust'] = 500  # +0.5 seconds
                
                elif event.key == pygame.K_r:
                    result['force_recognize'] = True
                
                elif event.key == pygame.K_f:
                    result['toggle_fullscreen'] = True
        
        return result
    
    def cleanup(self):
        """Clean up pygame resources."""
        pygame.quit()


if __name__ == "__main__":
    # Test display
    display = LyricsDisplay(fullscreen=False)
    
    # Simulate states
    import time
    
    states = [
        (DisplayState.LISTENING, "Testing listening state...", 2),
        (DisplayState.RECOGNIZING, "Testing recognizing state...", 2),
        (DisplayState.NO_MATCH, "Testing no match state...", 2),
    ]
    
    running = True
    state_index = 0
    state_start = time.time()
    
    while running:
        # Handle events
        events = display.handle_events()
        if events['quit']:
            running = False
            continue
        
        if events['toggle_fullscreen']:
            display.toggle_fullscreen()
        
        # Update state
        current_state, msg, duration = states[state_index]
        display.set_state(current_state)
        
        if time.time() - state_start > duration:
            state_index = (state_index + 1) % len(states)
            state_start = time.time()
        
        # Render
        display.render()
    
    display.cleanup()

