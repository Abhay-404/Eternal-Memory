# Google Drive Integration Setup

This guide shows you how to set up automatic audio syncing from Google Drive.

## 🎯 What This Does:

- ✅ Syncs audio files from your Google Drive folder
- ✅ Downloads them locally
- ✅ Organizes by date (handles multiple files per day)
- ✅ Processes each day (transcribe → summarize → update memory)
- ✅ **Deletes from Drive after successful processing**
- ✅ Works even if you run it after 3-4 days (catches up on all pending audio)

---

## 📋 Prerequisites:

1. Google Account
2. Audio files uploaded to Google Drive folder

Your Drive folder: https://drive.google.com/drive/folders/15DiULoMdAweFs9_PFE5yKUAnaQSwi7JP

---

## 🔧 Setup Steps:

### Step 1: Install Required Packages

```bash
pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client pydub
```

### Step 2: Create Google Cloud Project

1. Go to **Google Cloud Console**: https://console.cloud.google.com/

2. **Create a new project:**
   - Click "Select a project" (top bar)
   - Click "New Project"
   - Name: `MY_BRAIN`
   - Click "Create"

3. **Wait** for project creation (10-20 seconds)

4. **Select your project** from the dropdown

### Step 3: Enable Google Drive API

1. In the Cloud Console, go to **"APIs & Services"** → **"Library"**

2. Search for: `Google Drive API`

3. Click on "Google Drive API"

4. Click **"Enable"**

5. Wait for API to be enabled

### Step 4: Create OAuth Credentials

1. Go to **"APIs & Services"** → **"Credentials"**

2. Click **"+ CREATE CREDENTIALS"** → **"OAuth client ID"**

3. **Configure consent screen** (if prompted):
   - Click "Configure Consent Screen"
   - User Type: **External**
   - Click "Create"

   **App information:**
   - App name: `MY_BRAIN`
   - User support email: Your email
   - Developer contact: Your email
   - Click "Save and Continue"

   **Scopes:**
   - Click "Save and Continue" (no need to add scopes)

   **Test users:**
   - Click "+ ADD USERS"
   - Add your Gmail address
   - Click "Save and Continue"

   - Click "Back to Dashboard"

4. **Create OAuth Client ID:**
   - Go back to "Credentials"
   - Click "**+ CREATE CREDENTIALS**" → "**OAuth client ID**"
   - Application type: **Desktop app**
   - Name: `MY_BRAIN Desktop`
   - Click "**Create**"

5. **Download credentials:**
   - A dialog appears with Client ID and Client secret
   - Click "**DOWNLOAD JSON**"
   - Save the file

### Step 5: Rename and Move Credentials

1. Rename the downloaded file to: **`credentials.json`**

2. Move it to: **`C:\Users\Abhay\Desktop\MY_BRAIN\credentials.json`**

### Step 6: First-Time Authentication

1. Run the sync script:
```bash
python process_drive_audio.py
```

2. **Browser opens automatically:**
   - Sign in with your Google account
   - Click "Advanced" if you see a warning
   - Click "Go to MY_BRAIN (unsafe)" (this is your own app)
   - Click "Continue"
   - **Grant permissions** to access Google Drive

3. **Browser shows:** "The authentication flow has completed. You may close this window."

4. A `token.json` file is created automatically

5. **You won't need to authenticate again!** The token is saved.

---

## 📁 Organizing Audio Files in Drive:

### Option 1: Named by Date (Recommended)

Name your files with date prefix:
```
2024-01-26_morning.mp3
2024-01-26_evening.mp3
2024-01-27_daily.mp3
```

The system will group by date automatically.

### Option 2: Upload Date

Just upload files - the system uses the upload date to organize by day.

### Multiple Files Per Day:

If you have multiple audio files for one day:
```
2024-01-26_morning.mp3
2024-01-26_afternoon.mp3
2024-01-26_evening.mp3
```

The system will:
1. Download all 3 files
2. **Combine them into one audio**
3. Process as a single day's entry

---

## 🚀 Usage:

### Manual Sync (Run Anytime):

```bash
python process_drive_audio.py
```

This will:
1. Connect to Google Drive
2. Find all audio files in your folder
3. Group by date
4. Download each day's audio
5. Process (transcribe → summarize → update memory)
6. Delete from Drive after successful processing

### Run After 3-4 Days:

No problem! The system will:
- Find all pending audio files
- Process each day separately
- Catch up on everything

Example output:
```
================================================================================
MY_BRAIN - Google Drive Audio Sync
================================================================================

[Authenticating with Google Drive...]
[Listing audio files from Drive...]
[OK] Found 8 audio files in Drive

[OK] Organized into 3 days:
  2024-01-24: 2 audio file(s)
  2024-01-25: 3 audio file(s)
  2024-01-26: 3 audio file(s)

================================================================================
Processing Audio by Day
================================================================================

[Day: 2024-01-24] Processing 2 file(s)...
  >> Downloading: 2024-01-24_morning.mp3
     [OK] Downloaded
  >> Downloading: 2024-01-24_evening.mp3
     [OK] Downloaded
  >> Processing audio for 2024-01-24...
    [Combining 2 audio files...]
    [OK] Combined into single file
    [Processing 2 audio file(s) for 2024-01-24]
    [Running full processing pipeline...]
      1/5 Transcribing...
      [OK] Transcribed (523 words, Hindi-English mix)
      2/5 Creating daily summary...
      [OK] Daily summary created (387 words)
      3/5 Updating primary context...
      [OK] Primary context updated
      4/5 Updating short-term memory...
      [OK] Short-term memory updated
      5/5 Embedding in vector database...
      [OK] Embedded in vector database
    [OK] 2024-01-24 processing complete!
  >> Deleting from Drive...
     [OK] Deleted: 2024-01-24_morning.mp3
     [OK] Deleted: 2024-01-24_evening.mp3

[Day: 2024-01-25] Processing 3 file(s)...
...

================================================================================
SUCCESS! Audio Processing Complete
================================================================================

✓ Processed 3 days
✓ Downloaded 8 files
✓ Deleted 8 files from Drive

You can now query your memories:
  python query.py
```

---

## 🔄 Automated Daily Sync:

### Add to Daily Scheduler:

Edit `scheduler_daily.py` to add Drive sync:

```python
def run_drive_sync():
    """Sync and process audio from Google Drive"""
    print(f"\n[{datetime.now()}] Running Drive Sync")
    subprocess.run([sys.executable, "process_drive_audio.py"])

# Add to schedule
schedule.every().day.at("10:00").do(run_drive_sync)
```

---

## 🗂️ File Organization:

```
MY_BRAIN/
├── credentials.json          # OAuth credentials (you create this)
├── token.json               # Auto-generated on first auth
├── process_drive_audio.py   # Main sync script
├── data/
│   ├── drive_audio/         # Downloaded audio (temporary)
│   │   ├── 2024-01-24/
│   │   │   ├── morning.mp3
│   │   │   └── combined_audio.mp3
│   │   └── 2024-01-25/
│   ├── summaries/
│   │   └── daily/
│   │       ├── 2024-01-24.json  # Created from Drive audio
│   │       └── 2024-01-25.json
│   └── vector_store/            # Searchable memories
```

---

## 🐛 Troubleshooting:

### "credentials.json not found"
- Make sure you downloaded the JSON from Google Cloud Console
- Rename it to exactly `credentials.json`
- Place it in `C:\Users\Abhay\Desktop\MY_BRAIN\`

### "Access blocked: This app's request is invalid"
- Make sure you added your email as a test user in OAuth consent screen
- Try again with the email you added

### "Permission denied"
- Make sure you granted all permissions during authentication
- Delete `token.json` and run again to re-authenticate

### "No audio files found"
- Check your Drive folder: https://drive.google.com/drive/folders/15DiULoMdAweFs9_PFE5yKUAnaQSwi7JP
- Make sure audio files are directly in this folder (not in subfolders)
- Supported formats: .mp3, .wav, .m4a

### Audio combination fails
- Make sure `pydub` is installed: `pip install pydub`
- For non-mp3 files, you may need ffmpeg:
  - Download: https://www.gyan.dev/ffmpeg/builds/
  - Add to PATH

### Files not deleted from Drive
- This happens when processing fails
- Fix the error, then run again
- The system will skip already-processed days

---

## 🔐 Security Notes:

- **credentials.json**: Contains OAuth client ID (not secret)
- **token.json**: Contains your access token (keep private!)
- Add both to `.gitignore` if using git
- Only you can access your Drive files
- The app only reads/deletes from the specified folder

---

## 📌 Quick Reference:

**Your Drive folder:**
https://drive.google.com/drive/folders/15DiULoMdAweFs9_PFE5yKUAnaQSwi7JP

**Folder ID (in code):**
`15DiULoMdAweFs9_PFE5yKUAnaQSwi7JP`

**Run sync:**
```bash
python process_drive_audio.py
```

**File naming for date organization:**
```
YYYY-MM-DD_description.mp3
```

Example: `2024-01-26_daily_thoughts.mp3`

---

## ✅ Summary:

1. **Setup** (one-time):
   - Create Google Cloud project
   - Enable Drive API
   - Create OAuth credentials
   - Download credentials.json
   - Place in MY_BRAIN folder
   - Run once to authenticate

2. **Daily use**:
   - Upload audio to Drive folder
   - Run: `python process_drive_audio.py`
   - Audio is processed and deleted from Drive

3. **Automated**:
   - Add to scheduler for daily auto-sync
   - Runs at specified time every day

**You're done!** 🎉 Audio files will now sync from Drive automatically!
