Here is the cleanly formatted README.md translated into English:
# Telegram Metadata Bot v1.0

> An automated tool for modifying GPS coordinates and device metadata in photos and videos via a Telegram bot.

---

## 📁 Project Structure

```text
bot/
├── engine/
│   ├── __init__.py
│   ├── geo_data.py       # City coordinates database
│   ├── exif_worker.py    # EXIF manipulation (Pillow + piexif)
│   └── video_worker.py   # Video processing (ffprobe + ffmpeg)
├── bot/
│   ├── __init__.py
│   └── handlers.py       # Telegram event handlers (aiogram 3.x)
├── temp/                 # Temporary files directory (created automatically)
├── main.py               # Application entry point
├── bot_config.json       # Configuration file (bot token)
└── requirements.txt      # Python dependencies

🚀 Quick Start
1. Install Dependencies
Ensure Python 3.10+ is installed, then run:
pip install -r requirements.txt

2. Install FFmpeg
Video processing requires the ffmpeg and ffprobe binaries:
 * Option A: Download the package for your OS and add the binaries to your system PATH.
 * Option B (Windows): Place ffmpeg.exe and ffprobe.exe directly in the project root next to main.py.
3. Configure Bot Token
Create or edit bot_config.json:
{
  "token": "123456789:ABCdefGHIjkLmNoPqRsTuVwXyZ"
}

4. Run the Bot
python main.py

🤖 Bot Commands
| Command | Description |
|---|---|
| /start | Welcome message, usage guide, and initialization |
| /geo | Interactive menu to select target city |
| /status | View current user preferences (selected city, device profile) |
📋 Usage Guide
1. Device Calibration (Donor Photo)
Send an original, uncompressed photo taken by your target smartphone as a file (document).
 * If the image contains Make and Model tags, the bot extracts and saves this camera profile for your session.
 * Default device profile: Apple iPhone 15 Pro.
2. Image Processing
Send any image in JPEG, PNG, or WEBP format as a document.
 * The bot converts the image to JPEG, applies the chosen GPS coordinates, and injects the calibrated device metadata.
3. Video Processing
Send a video in MP4 or MOV format as a document.
 * Limit: Up to 16 seconds duration.
 * Lossless Processing: Metadata injection occurs at the container level (-c copy) without re-encoding, preserving full audio and video quality.
⚙️ Default Settings
 * City: 🇳🇴 Trondheim, Norway (63.4305, 10.3951)
 * Device: Apple iPhone 15 Pro
🔧 Technical Details
 * Framework: aiogram 3.x (asynchronous event loop)
 * Image Processing: Pillow + piexif
 * Video Processing: ffprobe (metadata/duration validation) + ffmpeg (stream copy)
 * Session Storage: In-memory dictionary (user_settings)
 * Data Cleanup: Files in temp/ are automatically deleted inside finally blocks immediately after dispatch
 * Architecture: Modular structure ready for packaging into a standalone executable (PyInstaller) or upgrading to a v2.0 GUI