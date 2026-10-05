# Telegram Metadata Bot v1.0

> A tool for automatically spoofing GPS coordinates and device metadata in photos and videos.

---

## 📁 Project Structure

```
bot/
├── engine/
│   ├── geo_data.py      # City coordinates
│   ├── exif_worker.py   # EXIF handling (PIL + piexif)
│   └── video_worker.py  # Video processing (ffprobe + ffmpeg)
├── bot/
│   └── handlers.py      # Telegram handlers (aiogram)
├── temp/                # Temporary files (created automatically)
├── main.py              # CLI v1.0 entry point
├── bot_config.json      # Configuration (token)
└── requirements.txt
```

---

## 🚀 Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Install ffmpeg

Download [ffmpeg for Windows](https://ffmpeg.org/download.html) and place `ffmpeg.exe` and `ffprobe.exe` into:
- The project root (`d:\bot\`), **or**
- Add them to the system PATH

### 3. Insert bot token

Edit the `bot_config.json` file:

```json
{
  "token": "123456789:ABCdefGHI..."
}
```

### 4. Run the bot

```bash
python main.py
```

---

## 🤖 Bot Commands

| Command | Description |
|---|---|
| `/start` | Welcome message and instructions |
| `/geo` | Target city selection (menu) |
| `/status` | Current user settings |

---

## 📋 Usage

### Device calibration (donor photo)
Send an original photo from your smartphone **as a file**.  
If the photo contains EXIF with Make/Model, the bot will read and save the make and model.

> Default: `Apple iPhone 15 Pro`

### Image processing
Send a JPEG, PNG, or WEBP **as a file**.  
The bot will return a JPEG with spoofed GPS data and device metadata.

### Video processing
Send an MP4 or MOV **as a file**.  
**Limit:** up to 16 seconds. No re-encoding — container metadata only.

---

## ⚙️ Default Settings

- **City:** 🇳🇴 Trondheim, Norway (`63.4305, 10.3951`)
- **Device:** Apple iPhone 15 Pro

---

## 🔧 Technical Details

- **Framework:** aiogram 3.x (async)
- **EXIF:** piexif + Pillow (PIL)
- **Video:** ffprobe (validation) + ffmpeg (stream copy, no re-encoding)
- **Settings storage:** in-memory (`user_settings` dictionary)
- **Temporary files:** `temp/` — removed in the `finally` block
- **Architecture:** modular, ready to expand to v2.0 (GUI + EXE)

<FollowUp label="Generate full working code for all bot modules?" query="Write full working code for all files of the Telegram Metadata Bot v1.0 project"/>
