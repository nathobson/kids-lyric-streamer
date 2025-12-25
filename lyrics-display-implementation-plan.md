# Lyrics Display Software - Implementation Plan

A structured plan for building a music recognition and synced lyrics display system.

---

## Phase 1: Basic Audio Recognition (Day 1)

**Goal**: Capture audio and identify songs

1. **Set up project structure**
   - Create virtual environment
   - Install dependencies: `pyaudio`, `requests`, `python-dotenv`
   - Create config file for API keys

2. **Implement audio capture**
   - List available audio input devices
   - Record 10-second audio samples
   - Save to temporary buffer (don't need to write files)

3. **Integrate song recognition API**
   - Sign up for ACRCloud or AudD (free tier)
   - Write function to send audio fingerprint
   - Parse response to extract: artist, title, album
   - Test with known songs playing

**Deliverable**: Script that prints "Now playing: Artist - Song Title"

---

## Phase 2: Lyrics Retrieval (Day 2)

**Goal**: Fetch synced lyrics for identified songs

1. **Implement LRCLIB integration**
   - API endpoint: `https://lrclib.net/api/search`
   - Search by artist + title from Phase 1
   - Handle "no lyrics found" gracefully

2. **Build LRC parser**
   - Parse timestamp format `[mm:ss.xx]`
   - Convert to milliseconds/seconds
   - Create data structure: `[(timestamp, lyric_line), ...]`
   - Handle plain text fallback (unsynced lyrics)

3. **Add caching layer**
   - Cache lyrics locally (JSON/pickle file)
   - Key by artist-title hash
   - Avoid redundant API calls for same song

**Deliverable**: Function that returns timestamped lyrics array for any song

---

## Phase 3: Display Engine (Day 3-4)

**Goal**: Show lyrics synced to music playback

1. **Build basic display window**
   - Start with `tkinter` (simplest) or `pygame`
   - Fullscreen or resizable window
   - Dark background, readable font (large, white text)

2. **Implement lyrics synchronization**
   - Track elapsed time since song detected
   - Find current lyric line based on timestamp
   - Highlight/display current line prominently
   - Show previous/next lines for context

3. **Handle time offset calibration**
   - Add manual offset adjustment (+/- seconds)
   - This compensates for recognition delay
   - Save offset per song or globally

**Deliverable**: Window that displays synced lyrics for a playing song

---

## Phase 4: Integration & Main Loop (Day 4-5)

**Goal**: Combine all components into working system

1. **Build main application loop**
   ```python
   - Initialize audio capture
   - Start display window
   - Loop:
     - Capture audio sample (every 15-30 seconds)
     - Recognize song
     - If new song detected:
       - Fetch lyrics
       - Reset playback timer
       - Update display
     - Update lyrics display with current timestamp
   ```

2. **Add state management**
   - Track current song
   - Handle song changes smoothly
   - Detect when music stops (silence detection)

3. **Error handling**
   - Network failures (API down)
   - No lyrics available
   - Audio device disconnected
   - Rate limiting

**Deliverable**: Fully working laptop application

---

## Phase 5: Polish & Features (Day 6-7)

**Goal**: Improve UX and reliability

1. **UI improvements**
   - Smooth transitions between lyrics
   - Show album art (if available from API)
   - Display song metadata
   - Add visual feedback during recognition

2. **Performance optimization**
   - Reduce recognition frequency once song identified
   - Background threading for API calls
   - Memory management for long sessions

3. **Configuration options**
   - Font size/style
   - Color themes
   - Recognition sensitivity
   - Time offset defaults

**Deliverable**: Polished desktop application

---

## Phase 6: Raspberry Pi Port (Day 8-9)

**Goal**: Deploy to hardware

1. **Set up Pi environment**
   - Flash Raspberry Pi OS Lite
   - Install Python + dependencies
   - Configure auto-start on boot

2. **Hardware integration**
   - Configure USB mic as default input
   - Set up HDMI display
   - Test audio levels

3. **Adapt for headless operation**
   - Full-screen kiosk mode
   - Remove debug output
   - Add logging to file
   - Create systemd service for auto-start

4. **Optimize for Pi**
   - Lower resolution if needed
   - Reduce recognition frequency if CPU-bound
   - Test thermal performance

**Deliverable**: Self-contained hardware unit

---

## Phase 7: Testing & Refinement (Ongoing)

1. **Test with various scenarios**
   - Different music sources (Spotify, radio, live)
   - Background noise levels
   - Song transitions
   - Long running sessions

2. **Fine-tune timing**
   - Calibrate offset for accuracy
   - Test with fast/slow songs
   - Handle live performances (might not work)

3. **Document setup**
   - Installation instructions
   - API key setup
   - Troubleshooting guide

---

## Recommended File Structure

```
lyrics-display/
├── src/
│   ├── audio_capture.py      # Phase 1
│   ├── song_recognition.py   # Phase 1
│   ├── lyrics_fetcher.py     # Phase 2
│   ├── lrc_parser.py          # Phase 2
│   ├── display.py             # Phase 3
│   └── main.py                # Phase 4
├── config/
│   ├── .env                   # API keys
│   └── settings.json          # User preferences
├── cache/
│   └── lyrics/                # Cached lyrics files
├── requirements.txt
└── README.md
```

---

## Dependencies List

```
pyaudio>=0.2.13
requests>=2.31.0
python-dotenv>=1.0.0
# Choose one:
pygame>=2.5.0  # OR
# tkinter (built-in)
```

---

## Timeline Estimate

**Total estimated time**: 7-9 days of focused work, probably 2-3 weeks realistically with testing and iteration.

---

## Key Technical Considerations

- **Time sync accuracy**: You'll need to calibrate the offset between when you detect the song and where it actually is in playback
- **Continuous recognition**: Decide if you run recognition continuously or just on startup/change
- **Lyrics availability**: Not all songs have synced lyrics available
- **API rate limits**: Free tiers have daily limits, plan accordingly
- **Cross-platform compatibility**: Keep code portable from laptop to Raspberry Pi

---

## Useful Resources

- **LRCLIB API**: https://lrclib.net/docs
- **ACRCloud**: https://www.acrcloud.com/
- **AudD**: https://audd.io/
- **LRC Format Spec**: Standard format for timestamped lyrics
