# WhatsApp Number Extractor (PC Tool)

Extract all phone numbers from your WhatsApp database using a rooted Android phone connected via USB.

## Features

- ✅ Extracts phone numbers from WhatsApp chats
- ✅ Extracts phone numbers from group participants
- ✅ Extracts phone numbers from messages
- ✅ Supports Iraqi phone formats (+964, 07XX)
- ✅ Exports to CSV file

## Requirements

### Phone:
- Rooted Android phone (root required)
- USB Debugging enabled
- WhatsApp installed

### Computer:
- Python 3.6+
- ADB (Android Debug Bridge) installed
- USB cable to connect phone

## Installation

```bash
# Install Python dependencies
pip install -r requirements.txt
```

## Phone Preparation

1. **Root your phone** (required - without root you cannot access WhatsApp database)

2. **Enable USB Debugging**:
   - Go to Settings → About Phone
   - Tap "Build Number" 7 times
   - Go to Settings → Developer Options
   - Enable "USB Debugging"

3. **Connect phone to PC via USB**

4. **Allow USB debugging** on your phone screen when prompted

## Usage

```bash
# Run the extractor
python extract_whatsapp.py
```

### What it does:

1. Checks if phone is connected via ADB
2. Extracts encrypted WhatsApp database from phone
3. Decrypts the database using the WhatsApp key
4. Reads phone numbers from:
   - `chat` table (all chat JIDs)
   - `messages` table (all message sender JIDs)
   - `group_participants` table (all group member JIDs)
5. Normalizes phone numbers (Iraqi format)
6. Exports to `whatsapp_numbers.csv`

## Manual Extraction (if auto-decrypt fails)

If the script cannot decrypt automatically:

1. Install a file manager with root access on your phone (like File Manager Plus)
2. Navigate to: `/data/data/com.whatsapp/databases/`
3. Copy these files to `/sdcard/`:
   - `msgstore.db.crypt14`
   - `key` (from `/data/data/com.whatsapp/files/key`)
4. Pull to computer:
   ```bash
   adb pull /sdcard/msgstore.db.crypt14 .
   adb pull /sdcard/key .
   ```
5. Use wa-crypt-tools to decrypt:
   ```bash
   wa-crypt-tools decrypt msgstore.db.crypt14 key msgstore.db
   ```
6. Open `msgstore.db` with SQLite browser to extract numbers

## Output

The script creates `whatsapp_numbers.csv` with:
```csv
phone,name
07701234567,
07891234568,
...
```

## Troubleshooting

### "No device connected"
- Make sure USB debugging is enabled
- Try a different USB cable
- Check if phone shows "USB debugging authorized" popup

### "Key not found"
- The key file is required to decrypt
- It should be at: `/data/data/com.whatsapp/files/key`
- You need root access to get it

### "Permission denied"
- Make sure your phone is rooted
- The script uses `su` to gain root access

## Disclaimer

This tool is for personal use only. Extract your own WhatsApp data. Respect privacy laws and WhatsApp Terms of Service.
