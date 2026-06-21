# 🧠 Inner Logic — Instagram Reel Automation

**Fully automated Instagram Reels for philosophical & psychological content.**

Every day at 8 PM IST, this pipeline automatically:
1. 💡 Scrapes a unique philosophical quote from Reddit
2. 🎨 Generates a dark cinematic AI background image
3. ✍️ Writes an **AI-powered caption** (Pollinations LLM — hook + reflection + CTA + smart hashtags)
4. 🎬 Creates a 15-second reel (Ken Burns zoom + auto-fit text overlay + cinematic color grading)
5. 🎵 Attaches **Instagram's trending native music** at upload time (maximizes reach)
6. 📱 Posts the reel to Instagram with the AI caption & hashtags

**100% free. Runs on GitHub Actions. Zero manual work. No Facebook/Meta Developer account needed. No LLM API key needed.**

---

## 📋 Prerequisites

Before setting up, you need:

- [x] **Instagram account** (Creator or Personal — any type works!)
- [x] **GitHub account** (free tier is fine)
- [x] **Pexels account** (optional, for better images — free)
- [x] **Reddit account** (optional, for unique quotes — free)

### Credentials You'll Need

| Secret | Description | Required? |
|--------|-------------|-----------|
| `INSTAGRAM_USERNAME` | Your Instagram username | ✅ Yes |
| `INSTAGRAM_PASSWORD` | Your Instagram password | ✅ Yes |
| `INSTAGRAM_TOTP_SECRET` | 2FA secret key (only if 2FA is enabled) | Only if 2FA is on |
| `PEXELS_API_KEY` | Pexels API key for high-quality images | Optional |
| `REDDIT_CLIENT_ID` | Reddit app client ID for quote scraping | Optional |
| `REDDIT_CLIENT_SECRET` | Reddit app client secret | Optional |

> **No Facebook account needed!** This uses `instagrapi` which logs in directly with your Instagram credentials — no Meta Developer account, no access tokens, no token refresh headaches.
>
> **No LLM API key needed!** AI captions are generated via Pollinations.ai's free text endpoint — the same provider already used for image generation.

---

## 🚀 Setup Guide

### Step 1: Fork / Clone This Repository

```bash
git clone https://github.com/YOUR_USERNAME/innerlogic.git
cd innerlogic
```

### Step 2: Add GitHub Secrets

Go to your repository → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

**Required secrets:**

| Name | Value |
|------|-------|
| `INSTAGRAM_USERNAME` | Your Instagram username (e.g., `innerlogic`) |
| `INSTAGRAM_PASSWORD` | Your Instagram password |

**Optional secrets (for better content):**

| Name | Value |
|------|-------|
| `INSTAGRAM_TOTP_SECRET` | Your 2FA TOTP secret (only if you have 2FA enabled) |
| `PEXELS_API_KEY` | Get from [pexels.com/api](https://www.pexels.com/api/) |
| `REDDIT_CLIENT_ID` | Get from [reddit.com/prefs/apps](https://www.reddit.com/prefs/apps) |
| `REDDIT_CLIENT_SECRET` | From your Reddit app settings |

### Step 3: Get a Pexels API Key (Optional — Recommended)

1. Go to [pexels.com/api/key](https://www.pexels.com/api/key/)
2. Sign up for a free account
3. Enter project name (e.g., `InnerlogicInstaAutomation`) and select **AI** as category
4. Copy the API key and add it as `PEXELS_API_KEY` GitHub Secret

Without Pexels, images are generated via Pollinations.ai (also free) or a dark gradient fallback.

### Step 4: Get Reddit API Credentials (Optional — For Unique Quotes)

1. Go to [reddit.com/prefs/apps](https://www.reddit.com/prefs/apps)
2. Click **"create another app..."** at the bottom
3. Fill in:
   - **name**: `innerlogic`
   - **type**: Select **script**
   - **redirect uri**: `http://localhost:8080`
4. Click **"create app"**
5. Copy the **client ID** (under the app name, looks like `aB1cD2eF3gH4iJ`) and **secret**
6. Add them as `REDDIT_CLIENT_ID` and `REDDIT_CLIENT_SECRET` GitHub Secrets

Without Reddit credentials, the pipeline uses a built-in collection of 130+ philosophical quotes.

### Step 5: Test the Pipeline

Go to **Actions** tab → **Daily Instagram Reel** → **Run workflow** → **Run workflow**

This will manually trigger the pipeline. Check the logs to verify everything works.

### Step 6: Let It Run!

The pipeline runs automatically every day at **8:00 PM IST** (2:30 PM UTC).

---

## 🏗️ Project Structure

```
innerlogic/
├── .github/
│   └── workflows/
│       └── post-reel.yml          # GitHub Actions workflow (cron schedule)
├── src/
│   ├── main.py                    # Main orchestrator — runs the full daily pipeline
│   ├── reddit_scraper.py          # Scrapes unique quotes from Reddit
│   ├── quote_picker.py            # Fallback: picks unused quotes from collection
│   ├── image_generator.py         # Generates dark cinematic images (Pexels → Pollinations.ai → gradient)
│   ├── video_creator.py           # Creates 15s reel (PIL auto-fit text + Ken Burns + color grading + watermark)
│   ├── insta_music.py             # Searches & attaches Instagram's trending native music
│   ├── caption_generator.py       # AI-powered captions (Pollinations LLM → local fallback)
│   ├── fonts_setup.py             # Downloads Cormorant Garamond + Montserrat
│   ├── instagram.py               # Posts reel via instagrapi (no API tokens!)
│   ├── scheduler.py               # Weekly schedule (Mon-Sat = Insta Day, Sun = Rest)
│   ├── smart_scheduler.py         # Picks optimal posting time based on past performance
│   └── weekly_summary.py          # Sunday auto-summary of the week's posts
├── data/
│   ├── quotes.json                # 130+ philosophical quotes collection (fallback)
│   └── used_quotes.json           # Tracks used quotes (auto-generated)
├── fonts/                         # Downloaded at runtime
├── temp/                          # Temporary files (cleaned after each run)
├── requirements.txt               # Python dependencies
├── .gitignore
└── README.md
```

---

## 🎨 How It Works

### Quote Scraping (Reddit)
- Scrapes philosophical quotes from subreddits like r/Stoicism, r/philosophy, r/Existentialism
- **MD5 deduplication** — never posts the same quote twice
- Quality filtering — only picks quotes that are deep, meaningful, and 15-150 characters
- Category detection — matches quotes to categories (stoicism, existentialism, etc.)
- **Falls back** to a built-in collection of 130+ quotes if Reddit is unreachable

### Image Generation (Three-Tier)
1. **Pexels API** — High-quality stock photos with dark/moody search terms (requires API key)
2. **Pollinations.ai** — Free AI image generation, creates unique dark cinematic paintings
3. **Dark gradient** — Fallback if both services fail

Different styles are matched to quote categories (e.g., zen style for Eastern quotes, oil painting for classical).

### Video Creation
- **FFmpeg** creates a 15-second 1080x1920 (9:16) reel
- **Ken Burns effect**: Slow zoom into the image
- **Text overlay**: Quote with fade-in/fade-out animation (ASS subtitles)
- **Music**: Fades in at start, fades out before end
- H.264 video + AAC audio, optimized for Instagram

### Music (Three-Tier)
1. **Pixabay API** — Search & download cinematic tracks (requires API key)
2. **Fallback CDN links** — 10 pre-selected royalty-free Pixabay tracks (no key needed!)
3. **Silent audio** — Last resort (Instagram requires an audio track)

### Instagram Posting (instagrapi)
- Uses **instagrapi** — unofficial Python library that logs in like the Instagram app
- Uploads video directly from local file — no public URL needed!
- No Facebook account, no Meta Developer account, no access tokens
- Session persistence — saves login session to avoid re-authenticating every time
- 2FA support — set `INSTAGRAM_TOTP_SECRET` if you have 2FA enabled

---

## 🔐 About instagrapi

`instagrapi` is an unofficial Instagram API that works by simulating the Instagram mobile app's login process. It's used by thousands of automation tools worldwide.

### Advantages over the Official Graph API
- **No Facebook account needed** — just your Instagram username & password
- **No Meta Developer account** — no app creation, no app review, no permissions
- **No token management** — no short-lived/long-lived token headaches
- **No public URL needed** — uploads video directly from the GitHub Actions runner
- **Works with personal accounts** — no need for Creator/Business account

### Security Notes
- Your credentials are stored safely in **GitHub Secrets** (encrypted, never visible in logs)
- The login session is saved to `ig_session.json` — reused on subsequent runs
- If Instagram triggers a verification challenge, you'll need to log in manually once
- For 2FA, install an authenticator app (Google Authenticator, Authy) and add the TOTP secret to GitHub Secrets

---

## ⚙️ Customization

### Adding More Built-in Quotes

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

### "Login failed" or "Challenge required"
- Instagram may flag the first login from a new device. Try logging in from your phone and approving the activity.
- If 2FA is enabled, make sure `INSTAGRAM_TOTP_SECRET` is set correctly.
- Delete the `ig_session.json` file and re-run — a fresh login may resolve the issue.

### "FFmpeg not found"
- The GitHub Actions workflow installs FFmpeg automatically. If running locally, install it with:
  ```bash
  sudo apt install ffmpeg    # Ubuntu/Debian
  brew install ffmpeg         # macOS
  ```

### "Video processing failed on Instagram"
- Make sure the video meets Instagram's requirements: MP4, H.264, 9:16 ratio, 3-90 seconds
- The pipeline creates videos that match these specs — if issues persist, re-run the workflow

### "No music downloaded"
- The pipeline always falls back to pre-selected CDN tracks — music should always work
- No Pixabay API key is needed — the fallback URLs are sufficient

### Pipeline runs but no reel appears
- Check the GitHub Actions logs for errors
- Verify your Instagram username and password are correct in GitHub Secrets
- If 2FA is enabled, make sure `INSTAGRAM_TOTP_SECRET` is set
- Try logging in to Instagram manually to check if there's a challenge/verification prompt

### Want to post at a different time?
- Edit the cron schedule in `.github/workflows/post-reel.yml`
- IST = UTC + 5:30, so subtract 5 hours 30 minutes from your desired IST time to get UTC

---

## ⚠️ Important Notes

1. **Your Instagram credentials are safe** — stored encrypted in GitHub Secrets, never visible in logs
2. **instagrapi session persistence** — login sessions are saved and reused, reducing the chance of being flagged
3. **Rate limits** — don't trigger the workflow more than a few times per day to avoid Instagram restrictions
4. **GitHub Actions free tier** gives 2000 minutes/month — this workflow uses ~5 minutes per run, well within limits
5. **First login** — the very first time instagrapi logs in, Instagram may send a "new login" notification. Just approve it.

---

## ✨ What's New (latest overhaul)

### 🎬 Text-cutoff fix
Previous reels sometimes showed truncated quote text (the dreaded `…` mid-quote). Root causes were:
- MoviePy 2.x removed the `method="caption"` API the old code relied on
- FFmpeg ASS subtitles were being given a *file path* as a font *family name* — libass couldn't resolve variable-font paths and fell back to a much wider default font, overflowing the safe area

**Fix:** Text is now rendered with **PIL** (`ImageFont.truetype` accepts file paths directly), auto-fit from 56px → 30px until the longest line fits within the 820px safe area. The result is a transparent PNG overlaid on the video — guaranteed never to clip, regardless of font or quote length.

### 🎵 Instagram-native audio only (no more synthesized music)
Previously Mon/Wed/Fri used FFmpeg-synthesized "AI music" — but Instagram's algorithm strongly favors reels that use **trending native audio**, and synthesized tracks got 3-5× less reach. The whole FFmpeg music path has been removed:
- **Every day Mon–Sat is now an Insta Day** — the pipeline searches Instagram's trending catalog and attaches a fresh trending track at upload time
- The `music_fetcher.py` module is no longer imported by `main.py` (left in the repo for reference but unused)
- Removed `PIXABAY_API_KEY` and `FREESOUND_TOKEN` from the workflow — no longer needed

### ✍️ AI-powered captions (Pollinations LLM, free, no API key)
Captions are now generated by a free LLM via Pollinations.ai (same provider already used for image generation). For each quote, the LLM produces:
- A **scroll-stopping hook** (first line, visible before "...more") — boosts tap-to-expand → boosts dwell time → boosts reach
- An **original reflection** (1–2 sentences in the brand voice — adds unique value, boosts saves)
- A **rotating CTA** (Save / Share / Comment / Follow — drives a specific engagement signal per post)
- **18–22 smart hashtags** mixing viral + niche + author + branded for balanced reach

Falls back to a curated local template system if the LLM call fails (network down / rate limited). The pipeline stays 100% free and runs on GitHub Actions with zero extra setup.

### 🎯 Other engagement boosts
- **Subtle text float animation** (±4px sinusoidal drift) — keeps the eye engaged → improves watch-time retention
- **Branded `@innerlogic.co` watermark** on every reel — builds recall → more profile visits → more follows
- **Variable caption structure** — avoids the "templated content" shadow-ban signal that hits accounts using identical caption formats

---

## 📄 License

This project is for personal use. The quotes used are attributed to their original authors. Background images are AI-generated (Pollinations.ai) or sourced from Pexels (royalty-free). Captions are AI-generated on the fly. Instagram native music is licensed through Instagram's platform.

---

<p align="center">
  Built with 🧠 by <strong>Inner Logic</strong>
</p>
