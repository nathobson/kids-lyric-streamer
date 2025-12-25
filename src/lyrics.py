"""Lyrics fetching from LRCLIB and LRC parsing."""

import re
import json
import hashlib
import requests
from dataclasses import dataclass, asdict
from typing import Optional, List
from pathlib import Path

from .config import CACHE_DIR


@dataclass
class LyricLine:
    """A single line of lyrics with timestamp."""
    time_ms: int  # Timestamp in milliseconds
    text: str


@dataclass
class LyricsData:
    """Complete lyrics data for a song."""
    artist: str
    title: str
    album: str
    synced: bool  # True if we have timed lyrics
    lines: List[LyricLine]
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'artist': self.artist,
            'title': self.title,
            'album': self.album,
            'synced': self.synced,
            'lines': [{'time_ms': l.time_ms, 'text': l.text} for l in self.lines]
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'LyricsData':
        """Create from dictionary."""
        return cls(
            artist=data['artist'],
            title=data['title'],
            album=data.get('album', ''),
            synced=data['synced'],
            lines=[LyricLine(l['time_ms'], l['text']) for l in data['lines']]
        )


def _get_cache_key(artist: str, title: str) -> str:
    """Generate cache key from artist and title."""
    normalized = f"{artist.lower().strip()}-{title.lower().strip()}"
    return hashlib.md5(normalized.encode('utf-8')).hexdigest()


def _get_cache_path(artist: str, title: str) -> Path:
    """Get path to cached lyrics file."""
    cache_key = _get_cache_key(artist, title)
    return CACHE_DIR / f"{cache_key}.json"


def load_cached_lyrics(artist: str, title: str) -> Optional[LyricsData]:
    """Load lyrics from cache if available.
    
    Args:
        artist: Artist name.
        title: Song title.
    
    Returns:
        LyricsData if cached, None otherwise.
    """
    cache_path = _get_cache_path(artist, title)
    
    if not cache_path.exists():
        return None
    
    try:
        with open(cache_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return LyricsData.from_dict(data)
    except (json.JSONDecodeError, KeyError, IOError):
        return None


def save_lyrics_to_cache(lyrics: LyricsData):
    """Save lyrics to cache.
    
    Args:
        lyrics: LyricsData to cache.
    """
    cache_path = _get_cache_path(lyrics.artist, lyrics.title)
    
    try:
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(lyrics.to_dict(), f, indent=2, ensure_ascii=False)
    except IOError:
        pass  # Silently fail on cache write errors


def parse_lrc(lrc_text: str) -> List[LyricLine]:
    """Parse LRC format lyrics into timestamped lines.
    
    LRC format: [mm:ss.xx] Lyric text
    
    Args:
        lrc_text: Raw LRC text.
    
    Returns:
        List of LyricLine objects sorted by timestamp.
    """
    lines = []
    # Match [mm:ss.xx] or [mm:ss] format
    pattern = r'\[(\d{1,2}):(\d{2})(?:\.(\d{1,3}))?\](.*)'
    
    for line in lrc_text.split('\n'):
        line = line.strip()
        if not line:
            continue
        
        # Handle multiple timestamps on same line (karaoke format)
        matches = list(re.finditer(pattern, line))
        
        if matches:
            for match in matches:
                minutes = int(match.group(1))
                seconds = int(match.group(2))
                hundredths = match.group(3)
                text = match.group(4).strip()
                
                # Convert to milliseconds
                time_ms = (minutes * 60 + seconds) * 1000
                if hundredths:
                    # Handle both .xx (hundredths) and .xxx (milliseconds)
                    if len(hundredths) == 2:
                        time_ms += int(hundredths) * 10
                    else:
                        time_ms += int(hundredths)
                
                if text:  # Skip empty lines
                    lines.append(LyricLine(time_ms=time_ms, text=text))
    
    # Sort by timestamp
    lines.sort(key=lambda x: x.time_ms)
    return lines


def parse_plain_lyrics(plain_text: str) -> List[LyricLine]:
    """Parse plain text lyrics (no timestamps).
    
    Args:
        plain_text: Plain lyrics text.
    
    Returns:
        List of LyricLine objects with time_ms=0 (unsynced).
    """
    lines = []
    for line in plain_text.split('\n'):
        line = line.strip()
        if line:
            lines.append(LyricLine(time_ms=0, text=line))
    return lines


def fetch_lyrics(artist: str, title: str, album: str = "") -> Optional[LyricsData]:
    """Fetch lyrics from LRCLIB API.
    
    Args:
        artist: Artist name.
        title: Song title.
        album: Album name (optional, used for caching only - not for search).
    
    Returns:
        LyricsData if found, None otherwise.
    """
    # Check cache first
    cached = load_cached_lyrics(artist, title)
    if cached:
        return cached
    
    # Build search URL - don't include album as it causes mismatches
    # (ACRCloud album names often differ from LRCLIB's database)
    base_url = "https://lrclib.net/api/search"
    params = {
        'artist_name': artist,
        'track_name': title
    }
    
    try:
        response = requests.get(base_url, params=params, timeout=10)
        response.raise_for_status()
        results = response.json()
    except requests.RequestException:
        return None
    except ValueError:
        return None
    
    if not results:
        return None
    
    # Find best match (prefer synced lyrics)
    best_match = None
    for result in results:
        if result.get('syncedLyrics'):
            best_match = result
            break
        elif result.get('plainLyrics') and not best_match:
            best_match = result
    
    if not best_match:
        return None
    
    # Parse lyrics
    synced_lrc = best_match.get('syncedLyrics', '')
    plain_text = best_match.get('plainLyrics', '')
    
    if synced_lrc:
        lines = parse_lrc(synced_lrc)
        synced = True
    elif plain_text:
        lines = parse_plain_lyrics(plain_text)
        synced = False
    else:
        return None
    
    lyrics = LyricsData(
        artist=artist,
        title=title,
        album=best_match.get('albumName', album),
        synced=synced,
        lines=lines
    )
    
    # Cache for future use
    save_lyrics_to_cache(lyrics)
    
    return lyrics


def get_current_line_index(lyrics: LyricsData, position_ms: int) -> int:
    """Find the current lyric line index for a given playback position.
    
    Args:
        lyrics: LyricsData object.
        position_ms: Current playback position in milliseconds.
    
    Returns:
        Index of current line (or -1 if before first line).
    """
    if not lyrics.lines or not lyrics.synced:
        return 0  # For unsynced, just show first line
    
    current_index = -1
    for i, line in enumerate(lyrics.lines):
        if line.time_ms <= position_ms:
            current_index = i
        else:
            break
    
    return current_index


if __name__ == "__main__":
    # Test lyrics fetching
    test_artist = "Coldplay"
    test_title = "Yellow"
    
    print(f"Fetching lyrics for: {test_artist} - {test_title}")
    lyrics = fetch_lyrics(test_artist, test_title)
    
    if lyrics:
        print(f"\n✓ Found {'synced' if lyrics.synced else 'plain'} lyrics")
        print(f"  Album: {lyrics.album}")
        print(f"  Lines: {len(lyrics.lines)}")
        print("\nFirst 5 lines:")
        for line in lyrics.lines[:5]:
            if lyrics.synced:
                mins = line.time_ms // 60000
                secs = (line.time_ms % 60000) // 1000
                print(f"  [{mins:02d}:{secs:02d}] {line.text}")
            else:
                print(f"  {line.text}")
    else:
        print("\n✗ No lyrics found")

