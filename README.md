# Telegram Metadata Bot v1.0

> A tool for automatically spoofing GPS coordinates and device metadata in photos and videos.

---

## 📁 Project Structure


bot/
├── engine/
│   ├── geo_data.py      # City coordinates
│   ├── exif_worker.py   # EXIF manipulation (PIL + piexif)
│   └── video_worker.py  # Video processing (ffprobe + ffmpeg)
├── bot/
│   └── handlers.py      # Telegram handlers (aiogram)
├── temp/                # Temporary files (created automatically)
├── main.py              # CLI v1.0 entry point
├── bot_config.json      # Configuration (token)
└── requirements.txt

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt

2. Install ffmpeg
Download ffmpeg for Windows and place ffmpeg.exe and ffprobe.exe into:
 * The project root (d:\bot\), or
 * Add them to your system PATH
3. Add Bot Token
Edit bot_config.json:
{
  "token": "123456789:ABCdefGHI..."
}

4. Run the Bot
python main.py

🤖 Bot Commands
| Command | Description |
|---|---|
| /start | Welcome message and instructions |
| /geo | Select target city (interactive menu) |
| /status | View current user settings |
📋 Usage
Device Calibration (Donor Photo)
Send an original photo taken with your smartphone as a file (document).
If the photo contains EXIF Make/Model tags, the bot will parse and store your device profile.
> Default: Apple iPhone 15 Pro
> 
Image Processing
Send a JPEG, PNG, or WEBP image as a file (document).
The bot returns a JPEG with replaced GPS coordinates and device metadata.
Video Processing
Send an MP4 or MOV video as a file (document).
Limit: Up to 16 seconds. No re-encoding — container-level metadata modification only.
⚙️ Default Settings
 * City: 🇳🇴 Trondheim, Norway (63.4305, 10.3951)
 * Device: Apple iPhone 15 Pro
🔧 Technical Details
 * Framework: aiogram 3.x (async)
 * EXIF: piexif + Pillow (PIL)
 * Video: ffprobe (validation) + ffmpeg (stream copy, zero quality loss)
 * Storage: In-memory (user_settings dict)
 * Temp Files: temp/ folder — cleaned up in finally blocks
 * Architecture: Modular, ready for v2.0 expansion (GUI + standalone EXE)

<FollowUp label="Сгенерировать полный рабочий код для всех модулей бота?" query="Напиши полный рабочий код для всех файлов проекта Telegram Metadata Bot v1.0"/>

