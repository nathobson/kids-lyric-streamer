# Lyrics Display

A lightweight music recognition and synced lyrics display for Raspberry Pi Zero.

Listens to ambient audio, identifies the playing song using ACRCloud, fetches synced lyrics from LRCLIB, and displays them on screen.

## Features

- **Audio fingerprinting** via ACRCloud API
- **Synced lyrics** from LRCLIB (with plain text fallback)
- **Minimal footprint** - ~50MB RAM, runs on Pi Zero
- **Simple UI** - Pygame-based, just text on black background
- **Caching** - Lyrics cached locally to reduce API calls
- **Manual offset** - Adjust sync timing with arrow keys

## Requirements

- Python 3.9+
- USB microphone
- Display (HDMI)
- ACRCloud account (free tier: 100 recognitions/day)

## Quick Start

### 1. Clone and install

```bash
git clone <repo-url> lyrics-display
cd lyrics-display
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure API credentials

```bash
cp env.example .env
# Edit .env and add your ACRCloud credentials
```

Get your ACRCloud credentials at: https://www.acrcloud.com/

### 3. Run

```bash
# Windowed mode (for testing)
python -m src.main --windowed

# Fullscreen mode
python -m src.main

# List audio devices
python -m src.main --list-devices

# Use specific audio device
python -m src.main --device 2
```

## Controls

| Key         | Action                        |
| ----------- | ----------------------------- |
| `Q` / `Esc` | Quit                          |
| `←` / `→`   | Adjust sync offset (-/+ 0.5s) |
| `R`         | Force re-recognize            |
| `F`         | Toggle fullscreen             |

## Raspberry Pi Zero Setup

### Automatic installation

```bash
chmod +x install.sh
./install.sh
```

This will:

- Install system dependencies
- Create Python virtual environment
- Install Python packages
- Set up systemd service for auto-start

### Manual service control

```bash
# Start the service
sudo systemctl start lyrics

# Stop the service
sudo systemctl stop lyrics

# View logs
journalctl -u lyrics -f

# Disable auto-start
sudo systemctl disable lyrics
```

### Hardware setup

- **Recommended**: Raspberry Pi Zero 2 W (quad-core)
- **Minimum**: Raspberry Pi Zero W (works but slower recognition)
- **Audio**: USB microphone or USB sound card
- **Display**: Any HDMI display

## Project Structure

```
lyrics-display/
├── src/
│   ├── main.py         # Entry point + main loop
│   ├── audio.py        # Audio capture (sounddevice)
│   ├── recognition.py  # ACRCloud integration
│   ├── lyrics.py       # LRCLIB + LRC parser + cache
│   ├── display.py      # Pygame rendering
│   └── config.py       # Settings management
├── cache/              # Cached lyrics (auto-created)
├── fonts/              # Custom fonts (optional)
├── .env                # API credentials (create from env.example)
├── requirements.txt
├── install.sh          # Pi installation script
└── README.md
```

## Configuration

Edit `.env` to customize:

```bash
# ACRCloud credentials (required)
ACRCLOUD_HOST=identify-eu-west-1.acrcloud.com
ACRCLOUD_ACCESS_KEY=your_key
ACRCLOUD_ACCESS_SECRET=your_secret

# Recognition interval in seconds (default: 45)
RECOGNITION_INTERVAL=45

# Manual time offset in milliseconds (default: 0)
TIME_OFFSET_MS=0
```

## Custom Fonts

Drop any `.ttf` or `.otf` font file into the `fonts/` directory to use it instead of the system font.

## Troubleshooting

### No sound detected

- Check microphone is connected: `arecord -l`
- Test recording: `arecord -d 5 test.wav && aplay test.wav`
- Try different audio device: `python -m src.main --list-devices`

### Recognition not working

- Verify ACRCloud credentials in `.env`
- Check internet connection
- Free tier has 100 calls/day limit

### Display not showing

- On Pi, ensure `DISPLAY=:0` is set
- Try with `--windowed` flag first
- Check pygame installation: `python -c "import pygame; print(pygame.ver)"`

### Lyrics out of sync

- Use `←`/`→` keys to adjust offset
- Offset is saved automatically

## API Credits

- **ACRCloud**: Song recognition - https://www.acrcloud.com/
- **LRCLIB**: Synced lyrics - https://lrclib.net/

## License

MIT
