# 🧠 Inner Logic — Instagram Reel Automation

**Fully automated Instagram Reels for philosophical & psychological content.**

Every day at 8 PM IST, this pipeline automatically:
1. 💡 Picks a unique philosophical quote
2. 🎨 Generates a dark cinematic AI background image
3. 🎵 Downloads royalty-free cinematic music
4. 🎬 Creates a 15-second reel (Ken Burns zoom + text overlay + music)
5. 📱 Posts the reel to Instagram with captions & hashtags

**100% free. Runs on GitHub Actions. Zero manual work.**

---

## 📋 Prerequisites

Before setting up, you need:

- [x] **Instagram Creator/Business account** (connected to a Facebook Page)
- [x] **Meta Developer App** with Instagram Graph API
- [x] **GitHub account** (free tier is fine)
- [x] **Pixabay account** (optional, for music variety — free)

### Credentials You'll Need

| Secret | Description | Where to get it |
|--------|-------------|-----------------|
| `INSTAGRAM_ACCESS_TOKEN` | API access token | Graph API Explorer |
| `INSTAGRAM_BUSINESS_ACCOUNT_ID` | Your Instagram account ID | Graph API Explorer |
| `FACEBOOK_APP_ID` | Your Meta App ID | App Dashboard → Settings |
| `FACEBOOK_APP_SECRET` | Your Meta App Secret | App Dashboard → Settings |
| `PIXABAY_API_KEY` | Pixabay API key (optional) | pixabay.com/api/docs |

---

## 🚀 Setup Guide

### Step 1: Fork / Clone This Repository

```bash
git clone https://github.com/YOUR_USERNAME/innerlogic.git
cd innerlogic
```

### Step 2: Add GitHub Secrets

Go to your repository → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

Add each secret:

| Name | Value |
|------|-------|
| `INSTAGRAM_ACCESS_TOKEN` | Your access token from Graph API Explorer |
| `INSTAGRAM_BUSINESS_ACCOUNT_ID` | Your Instagram Business Account ID |
| `FACEBOOK_APP_ID` | Your Meta App ID |
| `FACEBOOK_APP_SECRET` | Your Meta App Secret |
| `PIXABAY_API_KEY` | Your Pixabay API key (optional) |

### Step 3: Exchange Short-Lived Token for Long-Lived Token

The token from Graph API Explorer is short-lived (~1 hour). Exchange it for a long-lived one:

```bash
# Run this locally
pip install requests
python3 src/token_refresh.py YOUR_SHORT_TOKEN YOUR_APP_ID YOUR_APP_SECRET
```

Copy the long-lived token and **update the `INSTAGRAM_ACCESS_TOKEN` GitHub Secret** with it.

### Step 4: Test the Pipeline

Go to **Actions** tab → **Daily Instagram Reel** → **Run workflow** → **Run workflow**

This will manually trigger the pipeline. Check the logs to verify everything works.

### Step 5: Let It Run!

The pipeline runs automatically every day at **8:00 PM IST** (2:30 PM UTC).

---

## 🏗️ Project Structure

```
innerlogic/
├── .github/
│   └── workflows/
│       └── post-reel.yml          # GitHub Actions workflow (cron schedule)
├── src/
│   ├── main.py                    # Main orchestrator — runs the full pipeline
│   ├── quote_picker.py            # Picks unused quotes from the collection
│   ├── image_generator.py         # Generates dark cinematic images (Pollinations.ai)
│   ├── video_creator.py           # Creates 15s reel with FFmpeg
│   ├── music_fetcher.py           # Downloads royalty-free music
│   ├── caption_generator.py       # Generates captions + hashtags
│   ├── uploader.py                # Uploads video to temporary hosting
│   ├── instagram.py               # Posts reel via Instagram Graph API
│   └── token_refresh.py           # Refreshes access tokens automatically
├── data/
│   ├── quotes.json                # 130+ philosophical quotes collection
│   └── used_quotes.json           # Tracks used quotes (auto-generated)
├── fonts/                         # Downloaded at runtime
├── temp/                          # Temporary files (cleaned after each run)
├── requirements.txt               # Python dependencies
├── .gitignore
└── README.md
```

---

## 🎨 How It Works

### Quote Selection
- 130+ curated quotes from Stoicism, Existentialism, Eastern Philosophy, Psychology, and more
- Tracks used quotes to avoid repetition
- Auto-resets when all quotes have been used

### Image Generation
- Uses **Pollinations.ai** — free AI image generation, no API key needed
- Generates unique dark cinematic oil paintings every time
- Different styles matched to quote categories (e.g., zen style for Eastern quotes)
- Falls back to dark gradient if AI generation fails

### Video Creation
- **FFmpeg** creates a 15-second 1080x1920 (9:16) reel
- **Ken Burns effect**: Slow zoom into the image
- **Text overlay**: Quote with fade-in/fade-out animation (ASS subtitles)
- **Music**: Fades in at start, fades out before end
- H.264 video + AAC audio, optimized for Instagram

### Music
- Primarily uses **Pixabay API** (free, requires API key)
- Falls back to pre-selected royalty-free CDN links
- Last resort: generates silent audio (Instagram requires audio track)

### Instagram Posting
- Uses the **Instagram Graph API** (official, safe)
- Creates a media container → waits for processing → publishes
- Supports Reels with captions and hashtags

---

## 🔑 Token Management

### Short-lived vs Long-lived Tokens

| Type | Duration | How to Get |
|------|----------|-----------|
| Short-lived | ~1 hour | Graph API Explorer |
| Long-lived | 60 days | Exchange short-lived token |

### Auto-Refresh

The pipeline automatically refreshes your token on each run by calling the exchange endpoint with the current long-lived token. This extends the token for another 60 days.

### Manual Token Refresh

If the auto-refresh fails (e.g., token expired), you need to manually regenerate:

1. Go to [Graph API Explorer](https://developers.facebook.com/tools/explorer/)
2. Select your app
3. Add permissions: `instagram_basic`, `instagram_content_publish`, `pages_show_list`, `pages_read_engagement`
4. Click **Generate Access Token**
5. Copy the token
6. Exchange it for a long-lived token:
   ```bash
   python3 src/token_refresh.py YOUR_NEW_TOKEN YOUR_APP_ID YOUR_APP_SECRET
   ```
7. Update the `INSTAGRAM_ACCESS_TOKEN` GitHub Secret

### Optional: Auto-Update GitHub Secret

If you want the pipeline to automatically update the GitHub Secret with the refreshed token:

1. Create a **Personal Access Token** (GitHub Settings → Developer settings → Personal access tokens)
2. Give it the `repo` scope
3. Add it as a GitHub Secret named `PERSONAL_ACCESS_TOKEN`

---

## 🎵 Getting a Pixabay API Key (Optional but Recommended)

1. Go to [pixabay.com/api/docs](https://pixabay.com/api/docs/)
2. Sign up for a free account
3. Find your API key in the dashboard
4. Add it as the `PIXABAY_API_KEY` GitHub Secret

Without a Pixabay API key, the pipeline uses fallback music sources which may be less varied.

---

## ⚙️ Customization

### Adding More Quotes

Edit `data/quotes.json` — add new entries in this format:

```json
{
  "text": "Your quote here",
  "author": "Author Name",
  "category": "stoicism"
}
```

Available categories: `stoicism`, `existentialism`, `eastern`, `psychology`, `classical`, `mysticism`, `transcendentalism`, `motivation`, `rationalism`, `courage`, `romanticism`, `renaissance`, `creativity`, `cosmology`

### Changing Post Time

Edit `.github/workflows/post-reel.yml` and modify the cron schedule:

```yaml
schedule:
  - cron: '30 14 * * *'  # 8:00 PM IST
```

Use [crontab.guru](https://crontab.guru/) to convert your desired time.

### Changing Video Style

Edit `src/image_generator.py` to modify:
- Image prompts (dark cinematic, nature, abstract, etc.)
- Subjects for image generation
- Category-specific style additions

Edit `src/video_creator.py` to modify:
- Ken Burns zoom speed
- Text font, size, and position
- Video duration

### Changing Hashtags

Edit `src/caption_generator.py` to modify:
- Category-specific hashtags
- Universal hashtags
- Caption templates

---

## ❓ Troubleshooting

### "Token refresh failed"
- Your token has expired. Generate a new one from Graph API Explorer and update the GitHub Secret.

### "FFmpeg not found"
- The GitHub Actions workflow installs FFmpeg automatically. If running locally, install it with:
  ```bash
  sudo apt install ffmpeg    # Ubuntu/Debian
  brew install ffmpeg         # macOS
  ```

### "Video processing failed on Instagram"
- Make sure the video meets Instagram's requirements: MP4, H.264, 9:16 ratio, 3-90 seconds
- The video URL must be publicly accessible
- Try running the workflow again — temporary hosting services can be flaky

### "No music downloaded"
- Add a Pixabay API key to the GitHub Secrets
- Or the pipeline will use fallback URLs or generate silent audio

### Pipeline runs but no reel appears
- Check the GitHub Actions logs for errors
- Verify your Instagram account is a Creator/Business account
- Verify the Instagram Business Account ID is correct
- Make sure your Instagram account accepted the tester invitation

### Want to post at a different time?
- Edit the cron schedule in `.github/workflows/post-reel.yml`
- IST = UTC + 5:30, so subtract 5 hours 30 minutes from your desired IST time to get UTC

---

## ⚠️ Important Notes

1. **Your app must stay in Development Mode** — don't submit for App Review unless you want others to use your app
2. **Token expires every 60 days** — the auto-refresh handles this, but if the pipeline stops running for 60+ days, you'll need to manually refresh
3. **Instagram's API has rate limits** — don't trigger the workflow more than 25 times per day
4. **This uses the official Instagram Graph API** — safe and approved by Meta, no risk of account ban
5. **GitHub Actions free tier** gives 2000 minutes/month — this workflow uses ~5 minutes per run, well within limits

---

## 📄 License

This project is for personal use. The quotes used are attributed to their original authors. Background music is sourced from royalty-free providers (Pixabay). AI-generated images are unique and not subject to copyright claims.

---

<p align="center">
  Built with 🧠 by <strong>Inner Logic</strong>
</p>
