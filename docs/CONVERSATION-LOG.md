# Bharat Shorts — Development Conversation Log
**Date:** March 11, 2026

---

## Project Setup
- Created project at `/Users/admin/Desktop/Workspace/projects/adhin-cureocity/startup/automated video editor/`
- Git repo: https://github.com/Adhinc/bharat-shorts.git
- GitHub account: `Adhinc`

## Tech Stack
- **Frontend:** Next.js 16 (App Router), Tailwind CSS v4, Zustand, Remotion v4
- **Backend:** FastAPI, Faster-Whisper, FFmpeg, Celery + Redis
- **Infra:** Docker, docker-compose, AWS ap-south-1 (planned)

## What Was Built

### Frontend Pages
| Route | File | Description |
|-------|------|-------------|
| `/` | `src/app/page.tsx` | Landing page — hero, features, how-it-works, CTA |
| `/editor` | `src/app/editor/page.tsx` | Full editor — upload, transcribe, edit captions, preview, export |
| `/dashboard` | `src/app/dashboard/page.tsx` | Project management — stats, recent projects, quick actions |
| `/pricing` | `src/app/pricing/page.tsx` | 3 tiers — Free (₹0), Pro (₹2,999), Enterprise (₹4,999) |

### Frontend Components
| Component | Description |
|-----------|-------------|
| `Navbar.tsx` | Global nav with active link highlighting |
| `VideoPlayer.tsx` | Remotion Player wrapper with play/pause, time tracking |
| `VideoComposition.tsx` | Remotion composition — video + caption overlay |
| `CaptionRenderer.tsx` | Animated captions (karaoke, pop, fade, typewriter) |

### Frontend State
| Store | Description |
|-------|-------------|
| `editor-store.ts` | Zustand store for project, transcript, caption styles, playback |

### Backend API Endpoints (16 routes)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/health` | Health check |
| POST | `/api/v1/process-video` | Upload video, extract metadata |
| POST | `/api/v1/transcribe/{id}` | Whisper transcription (22+ languages) |
| GET | `/api/v1/transcript/{id}/srt` | Download SRT file |
| POST | `/api/v1/remove-silence/{id}` | Remove silent segments |
| GET | `/api/v1/video/{id}` | Stream video for preview |
| POST | `/api/v1/render/{id}` | Burn captions into video (ASS subtitles) |
| GET | `/api/v1/download/{id}` | Download rendered video |
| POST | `/api/v1/magic-clips/{id}` | AI highlight extraction |
| POST | `/api/v1/reframe/{id}` | 16:9 → 9:16 conversion |
| POST | `/api/v1/broll-suggestions/{id}` | B-roll stock footage matching |
| POST | `/api/v1/automate` | Enterprise bulk processing |

### Backend Services
| Service | File | Description |
|---------|------|-------------|
| Transcription | `services/transcription.py` | Faster-Whisper, word-level timestamps, Hinglish, SRT generation |
| Magic Clips | `services/magic_clips.py` | Heuristic highlight scoring, clip grouping (30-60s) |
| B-Roll | `services/broll.py` | Keyword extraction, Pexels API search, audio ducking FFmpeg filters |
| Reframe | `services/reframe.py` | Center crop with MediaPipe face detection (graceful fallback), auto-zoom |
| Silence | `services/silence.py` | FFmpeg silencedetect + removal |

### Infrastructure
| File | Description |
|------|-------------|
| `Dockerfile.backend` | Python 3.12 + FFmpeg |
| `Dockerfile.frontend` | Node 20 Alpine |
| `docker-compose.yml` | Backend + Frontend + Redis + Celery worker |

---

## Bugs Found & Fixed (37 total audited)

### Critical Fixes Applied
1. **CORS** — Changed `allow_origins=["*"]` with credentials to specific origins (`localhost:3000`, `3001`)
2. **API URLs** — Frontend was hardcoding `http://localhost:8000` causing CORS errors. Changed to relative paths via Next.js rewrites
3. **File paths** — All paths changed from relative (`Path("uploads")`) to absolute (`Path(__file__).resolve().parent.parent / "uploads"`)
4. **ASS subtitle path** — Escaped spaces/colons for FFmpeg subtitle filter (project dir has spaces)
5. **Whisper singleton** — Model now reloads when `model_size` parameter changes
6. **MediaPipe fallback** — Graceful center-crop fallback when mediapipe/opencv not installed (Python 3.14 compat)
7. **Editor layout** — Fixed 56px clipping from navbar (`h-screen` → `h-[calc(100vh-3.5rem)]`)
8. **VideoPlayer events** — Fixed `frameupdate` event handler typing
9. **Security** — Removed traceback leak from error responses
10. **silence.py** — Replaced `subprocess cp` with `shutil.copy` (cross-platform)
11. **Dead code** — Removed duplicate karaoke text builder in ASS generator
12. **Requirements** — Added `httpx`, `numpy`; made `mediapipe`/`opencv` optional
13. **Mutable default** — Fixed `BulkProcessRequest.options` with `Field(default_factory=...)`

### Known Remaining Issues (not yet fixed)
- No user authentication (Google OAuth, email signup)
- No database (PostgreSQL) — projects are lost on restart
- Razorpay payment integration is UI only
- File storage is local filesystem (needs S3 for production)
- No usage limits or credit tracking
- Whisper runs on CPU (slow) — needs GPU for production
- No automated test suite
- No rate limiting or API key auth
- Not deployed to AWS yet
- Dashboard UI is hardcoded demo data
- No localized UI toggle (Hindi/Tamil)
- `@remotion/cli` and type packages are in `dependencies` instead of `devDependencies`

---

## Dev Commands

```bash
# Backend (port 8000)
cd backend && source venv/bin/activate && uvicorn app.main:app --reload --port 8000

# Frontend (port 3001 — port 3000 may be taken by another app)
cd frontend && npm run dev -- -p 3001

# Test transcription
cd backend && source venv/bin/activate && python tests/test_transcription.py <video_path>

# Docker (full stack)
docker-compose up --build

# API docs
http://localhost:8000/docs
```

## Important Notes
- FFmpeg must be installed: `brew install ffmpeg`
- Port 3000 was occupied by another project — use port 3001
- Next.js rewrites proxy `/api/v1/*` to backend at `localhost:8000` (configured in `next.config.ts`)
- Whisper model downloads on first use (~150MB for "base")
- Backend venv uses Python 3.14 — mediapipe doesn't support it, so reframe uses center-crop fallback
- GitHub PAT was exposed in chat — should be rotated immediately

## Project Structure
```
automated video editor/
├── backend/
│   ├── app/main.py              # FastAPI app, all routes
│   ├── services/
│   │   ├── transcription.py     # Faster-Whisper
│   │   ├── magic_clips.py       # Highlight extraction
│   │   ├── broll.py             # B-Roll matching + audio ducking
│   │   ├── reframe.py           # 16:9 → 9:16 + auto-zoom
│   │   └── silence.py           # Silence removal
│   ├── workers/
│   │   ├── celery_app.py        # Celery config
│   │   └── tasks.py             # Async video processing
│   ├── tests/
│   │   └── test_transcription.py
│   ├── requirements.txt
│   ├── .env
│   └── venv/
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx       # Root layout + Navbar
│   │   │   ├── page.tsx         # Landing page
│   │   │   ├── editor/page.tsx  # Video editor
│   │   │   ├── dashboard/page.tsx
│   │   │   └── pricing/page.tsx
│   │   ├── components/
│   │   │   ├── Navbar.tsx
│   │   │   ├── VideoPlayer.tsx
│   │   │   ├── VideoComposition.tsx
│   │   │   └── CaptionRenderer.tsx
│   │   ├── stores/editor-store.ts
│   │   └── styles/globals.css
│   ├── next.config.ts           # API rewrites
│   ├── package.json
│   └── tsconfig.json
├── docs/
│   ├── BLUEPRINT.md             # Architecture reference
│   └── CONVERSATION-LOG.md      # This file
├── CLAUDE.md                    # Project context for Claude
├── .gitignore
├── Dockerfile.backend
├── Dockerfile.frontend
└── docker-compose.yml
```

---

## Session 2: Advanced Features Build (March 11, 2026 — Continued)

Audited the full codebase against a master blueprint document (6 phases). Went feature-by-feature asking user to build or skip.

### Features Built (9 total)

#### 1. AI Video Translator & Dubbing
- **Service:** `services/translator.py`
- **Deps:** `deep-translator>=1.11.4`, `edge-tts>=6.1.0`
- 24 languages: Hindi, Tamil, Marathi, Telugu, Bengali, Kannada, Malayalam, Gujarati, Punjabi, Urdu, English, Arabic, Spanish, French, German, Portuguese, Japanese, Korean, Chinese, Indonesian, Thai, Vietnamese, Russian, Turkish
- Edge TTS voices: male/female for each language (Indian English uses en-IN voices)
- Translation preserves word-level timing; word count mismatch handled via even distribution
- FFmpeg audio replacement or mixing (keep original at configurable volume)
- **Endpoints:** `GET /api/v1/languages`, `POST /api/v1/translate/{id}`, `POST /api/v1/dub/{id}`, `GET /api/v1/download-dubbed/{id}/{lang}`
- **Frontend:** Translate & Dub panel in editor right sidebar — language dropdown, translate button, gender selector, keep-original checkbox, dub button, download link

#### 2. URL Ingestion (YouTube, Podcast, Direct)
- **Service:** `services/ingest.py`
- **Deps:** `yt-dlp>=2024.0`
- Detects source type: youtube, podcast, direct
- Downloads up to 1080p, max 2GB, max 2 hours
- Podcast audio auto-converted to video with dark background (1080x1920, 1fps ultrafast)
- Metadata from yt-dlp info.json + ffprobe fallback
- **Endpoint:** `POST /api/v1/ingest` — accepts `{ url, max_duration }`
- **Frontend:** URL input + "Import" button on upload screen with "or paste a link" divider

#### 3. Automated Assembly (B-Roll + Transitions + Music)
- **Service:** `services/assembly.py`
- Downloads stock clips from Pexels via `select_best_clip_url()` (prefers 720p SD)
- `insert_broll_overlays()` — cuts B-Roll into timeline at keyword timestamps, scales/pads to match main video, keeps original speech audio during B-Roll
- `add_background_music()` — loops music, applies speech-aware ducking via `compute_duck_regions()` from broll.py
- `auto_assemble()` — full pipeline: download B-Roll → insert → add music → output
- Min gap between B-Roll: configurable (default 10s), max 5 clips, B-Roll max 5s each
- **Endpoints:** `POST /api/v1/assemble/{id}`, `GET /api/v1/download-assembled/{id}`
- **Frontend:** "Auto Assemble" button (indigo) + download link + info (clips inserted, music status)

#### 4. AI Eye Contact Correction
- **Service:** `services/eye_contact.py`
- **Deps:** `mediapipe>=0.10.0`, `opencv-python-headless>=4.8.0`
- **Model:** `models/face_landmarker.task` (downloaded from Google Storage, 3.6MB)
- MediaPipe FaceLandmarker (Tasks API, v0.10.32) with 478 landmarks including 10 iris points
- Iris indices: LEFT_IRIS [468-472], RIGHT_IRIS [473-477]
- Eye region indices: 16 landmarks per eye for bounding box
- Gaze detection: iris center vs eye center offset
- Iris warp: affine transform shifts iris toward center, Gaussian-blended circular mask (radius = 1.8x iris)
- Configurable: `correction_strength` (0.0-1.0, default 0.7), `process_every_n` (frame skip)
- Two-pass: OpenCV frame-by-frame → FFmpeg merge with original audio
- **Endpoints:** `POST /api/v1/eye-contact/{id}`, `GET /api/v1/download-eye-contact/{id}`
- **Frontend:** "Eye Contact Fix" button (cyan) + stats + download

#### 5. AI Actors Studio (Avatar Videos)
- **Service:** `services/avatar.py`
- 5 avatar presets: Priya (Professional Female), Arjun (Professional Male), Ananya (Casual Female), Rahul (Casual Male), Corporate
- 6 backgrounds: studio_dark, studio_blue, studio_warm, studio_green, gradient_purple, gradient_sunset
- Pipeline: script → Edge TTS audio → extract audio energy (RMS per frame) → render frames with mouth animation → burn captions → FFmpeg merge
- Lip-sync: audio energy drives `mouth_open` (0.0-1.0), smoothed with 0.3/0.7 blend
- Breathing animation: gentle scale oscillation via sine wave
- Caption overlay: word-by-word with orange-bordered background bar, highlighted current word
- Custom face image upload supported (scales to 60% width, positioned upper area)
- **Endpoints:** `GET /api/v1/avatar-presets`, `GET /api/v1/avatar-backgrounds`, `POST /api/v1/avatar-video`, `POST /api/v1/avatar-video-with-image`, `GET /api/v1/download-avatar/{id}`
- **Frontend:** `/avatar` page — script textarea, language, gender, speech rate, avatar source (preset/upload), background grid, generate + download

#### 6. Content Ideation AI Tools
- **Service:** `services/ideation.py`
- **Video Idea Generator:** 5 categories (listicle, story, tutorial, controversial, trending), India-focused templates with ₹ values, Hinglish support, engagement estimates
- **Video Hook Generator:** 16+ patterns, 4 styles (question, statistic, story, controversial), retention estimates, platform fit
- **Video Script Generator:** hook → body → CTA structure, 5 tones (energetic, calm, professional, funny, dramatic), duration targeting (30/60/90s)
- All pure Python — no external LLM API needed
- **Endpoints:** `POST /api/v1/tools/ideas`, `POST /api/v1/tools/hooks`, `POST /api/v1/tools/script`
- **Frontend:** `/tools` page with tabbed interface (3 tabs initially)

#### 7. Platform-Specific Generators
- **Service:** `services/platform_tools.py`
- **YouTube Title Generator:** 15 English + 7 Hinglish patterns, char count, SEO score
- **YouTube Description Generator:** timestamps, key points, resources, social links, tags
- **Hashtag Generator:** 30 tags for Instagram/TikTok/YouTube, broad/niche/specific breakdown, auto-detects niche
- **Instagram Caption Generator:** emoji-rich with CTA, 30 hashtags auto-appended
- **TikTok Caption Generator:** <150 chars, trending hashtags
- **LinkedIn Post Generator:** professional tone, structured format
- **Endpoints:** `POST /api/v1/tools/youtube-titles`, `youtube-description`, `hashtags`, `instagram-caption`, `tiktok-caption`, `linkedin-post`
- **Frontend:** 3 new tabs on `/tools` page (YT Titles, Hashtags, Captions)

#### 8. Dynamic Face-Tracking Reframe
- Added `reframe_video_dynamic()` to `services/reframe.py`
- Two-pass pipeline:
  - Pass 1: Sample frames every N (default 3), detect face via FaceLandmarker nose tip (landmark 1)
  - Interpolate missing frames (linear between nearest detections)
  - Exponential Moving Average smoothing (default α=0.85) for smooth camera pan
  - Pass 2: OpenCV per-frame crop centered on smoothed position → resize to target
  - FFmpeg merge with original audio
- **Endpoints:** `POST /api/v1/reframe-dynamic/{id}`, `GET /api/v1/download-reframed/{id}`
- **Frontend:** "Dynamic Reframe" button (amber) + stats + download

#### 9. Collaborative Workspaces — SKIPPED
- User chose not to build multi-user team features

### Navbar Updated
Links: Home, Dashboard, Editor, AI Avatar, AI Tools, Pricing

### Updated Project Structure
```
backend/services/
├── transcription.py    # (existing)
├── magic_clips.py      # (existing)
├── broll.py            # (existing)
├── reframe.py          # UPDATED: added reframe_video_dynamic()
├── silence.py          # (existing)
├── translator.py       # NEW: translation + dubbing
├── ingest.py           # NEW: URL download
├── assembly.py         # NEW: auto-assembly
├── eye_contact.py      # NEW: eye contact correction
├── avatar.py           # NEW: avatar video generation
├── ideation.py         # NEW: idea/hook/script generators
└── platform_tools.py   # NEW: platform-specific generators

backend/models/
└── face_landmarker.task  # NEW: MediaPipe model (3.6MB)

frontend/src/app/
├── avatar/page.tsx     # NEW: AI Avatar Studio
├── tools/page.tsx      # NEW: AI Tools (6 tabs)
├── editor/page.tsx     # UPDATED: URL input, translate/dub, action buttons
└── (existing pages unchanged)
```

### Python Dependencies (requirements.txt)
```
fastapi==0.135.1
uvicorn==0.41.0
python-multipart==0.0.22
celery==5.6.2
redis==7.3.0
python-dotenv==1.2.2
pydantic==2.12.5
faster-whisper==1.2.1
httpx>=0.28.0
numpy>=2.0.0
mediapipe>=0.10.0
opencv-python-headless>=4.8.0
deep-translator>=1.11.4
edge-tts>=6.1.0
yt-dlp>=2024.0
```

### All Changes Are UNCOMMITTED
Run `git add` and `git commit` when ready.

---

---

## Session 3: Advanced Transcription Enhancement

### Feature: Advanced Transcription (COMPLETED)
**File:** `backend/services/transcription.py` — Full rewrite

**What was added:**
- **Audio preprocessing pipeline** via FFmpeg: highpass (80Hz), lowpass (8kHz), EBU R128 loudnorm, noise gate (threshold=-30dB)
- **Auto-model selection** per language: `LANGUAGE_MODEL_MAP` maps Indian languages to optimal Whisper model sizes (e.g. Telugu→medium, Hindi→small, English→base)
- **Hinglish detection**: regex-based code-switching detection (Hindi+English mix) with ratio analysis
- **Optimized beam search**: `INDIAN_LANGUAGES` dict with per-language beam_size (5-8) and best_of (3-5)
- **Temperature fallback**: `[0.0, 0.2, 0.4]` for better accuracy on difficult audio
- **Multi-model retry**: If confidence < 0.6 with base/small, automatically retries with larger model
- **Regional dialect post-processing**: Corrections for common Whisper misrecognitions (Hindi, Tamil, Marathi)
- **Lower VAD threshold** (0.35): Better detection for soft-spoken Indian speakers
- **WebVTT export**: New `generate_vtt()` function

**API changes (`backend/app/main.py`):**
- `TranscriptResponse` now includes: `language_probability`, `is_hinglish`, `model_used`, `preprocessed`
- New endpoint: `GET /api/v1/transcript/{project_id}/vtt` — WebVTT download

---

## Session 3 (cont): Remotion Export Engine

### Feature: Remotion Export Engine (COMPLETED)

**New files created:**
- `frontend/src/remotion/Root.tsx` — Remotion composition entry point (portrait + landscape)
- `frontend/src/remotion/index.ts` — registerRoot entry for bundling
- `frontend/render-server.ts` — Express server using `@remotion/renderer` + `@remotion/bundler`
- `backend/services/remotion_render.py` — Python service calling Node render server

**Enhanced files:**
- `frontend/src/components/CaptionRenderer.tsx` — Added 4 new animations:
  - **bounce**: Spring overshoot with translateY bounce
  - **glow**: Pulsing neon glow effect using sin wave
  - **shake**: Rapid shake on word hit with rotation
  - **emoji-pop**: Keyword-triggered emoji overlay (36 mappings: fire, money, subscribe, India, etc.)
- `frontend/src/stores/editor-store.ts` — Updated animation type union
- `frontend/src/app/editor/page.tsx` — "Export HD" + "Quick Export" buttons, 8 animations in dropdown
- `backend/app/main.py` — Render endpoint tries Remotion first, falls back to FFmpeg-ASS
  - RenderRequest now accepts `renderer` ("auto"/"remotion"/"ffmpeg") and `quality` ("high"/"fast")
  - RenderResponse includes `renderer` field showing which engine was used
  - Download endpoint serves Remotion output preferentially

**New npm packages:** `@remotion/renderer`, `@remotion/bundler`, `express`, `@types/express`, `tsx`

**How to use:**
1. Start render server: `cd frontend && npm run render-server` (port 3100)
2. "Export HD" button uses Remotion (if server running), "Quick Export" uses FFmpeg-ASS
3. Remotion Studio: `cd frontend && npm run remotion:studio`

---

## Session 3 (cont): Automated SFX & Music

### Feature: Automated SFX & Music (COMPLETED)
**File:** `backend/services/sfx.py` — NEW

**SFX catalog (8 types, synthesized via FFmpeg lavfi — no external files):**
- whoosh, swoosh, pop, ding, bass_drop, rise, click, reveal
- Each auto-generated on first use, cached in `assets/sfx/`

**Music presets (5 ambient loops, 30s each):**
- chill_lo_fi, upbeat_energy, cinematic_pad, news_intro, bollywood_vibe
- Cached in `assets/music/`

**Auto-placement strategies:**
- `transitions` — SFX at gaps between transcript segments
- `all_segments` — SFX at start of every segment
- `long_pauses` — SFX only at pauses > 1 second

**SFX mixing:** FFmpeg adelay positions each SFX at correct timestamp, amix combines

**API endpoints:**
- `GET /api/v1/sfx-catalog` — list all SFX types
- `GET /api/v1/music-presets` — list all music presets
- `POST /api/v1/sfx/{project_id}` — auto-add SFX to video
- `GET /api/v1/download-sfx/{project_id}` — download video with SFX
- `POST /api/v1/generate-music/{preset}` — download generated music loop

**Assembly integration:** `AssembleRequest` now accepts `add_sfx`, `sfx_type`, `sfx_volume`, `music_preset`. Assembly pipeline adds whoosh SFX at transitions by default.

**Frontend:** "Add SFX" button (pink) + download link + info display

---

## Session 3 (cont): AI Stock Integration

### Feature: AI Stock Integration (COMPLETED)
**File:** `backend/services/stock.py` — NEW

**Providers:** Pexels + Pixabay dual-provider search with auto-fallback

**India keyword enhancement (70 mappings):**
- food → "Indian street food thali", city → "India city skyline Mumbai Delhi"
- cricket, bollywood, chai, bazaar, namaste, yoga, etc.
- Hinglish keywords mapped (desh, ghar, paani, gaadi, etc.)
- Auto-appends "India" to generic queries if no India terms detected

**12 curated Indian categories:**
- Cities: Mumbai, Delhi, Bangalore, Jaipur, Varanasi, Kerala
- Themes: Street Food, Festivals, Indian Nature, Daily Life, Business & Tech, Spirituality
- Each category has 4-5 pre-built search queries

**API endpoints:**
- `GET /api/v1/stock/search?query=...&india_focus=true` — multi-provider search
- `GET /api/v1/stock/categories` — list curated categories
- `GET /api/v1/stock/browse/{category_id}` — browse category
- `POST /api/v1/stock/match/{project_id}` — India-enhanced B-Roll matching

---

## Session 3 (cont): Celery/Redis Production Scale

### Feature: Celery/Redis Production Scale (COMPLETED)

**Files modified/created:**
- `backend/workers/celery_app.py` — Rewritten: 4 priority queues, task routing, rate limiting, crash recovery
- `backend/workers/tasks.py` — Rewritten: 10 individual tasks for all heavy operations
- `backend/app/main.py` — Added task status, async dispatch, queue stats endpoints
- `docker-compose.yml` — Rewritten: separate GPU/default workers, Flower, render server
- `backend/requirements.txt` — Added flower>=2.0.0

**10 Celery tasks:** transcribe_video, render_video, render_video_4k, assemble_video, eye_contact_fix, dynamic_reframe, generate_avatar, generate_dub, add_sfx, process_video_full

**4 queues:** critical → gpu → default → low

**API:** `GET /task/{id}`, `POST /async/dispatch`, `GET /queue/stats`

**Docker:** GPU worker (1 concurrency, 8GB), default worker (2 concurrency, 4GB), Flower on :5555

---

## Remaining Features To Build (Priority Order)
1. ~~**Advanced Transcription**~~ ✅ DONE
2. ~~**Remotion Export Engine**~~ ✅ DONE
3. ~~**Automated SFX & Music**~~ ✅ DONE
4. ~~**AI Stock Integration**~~ ✅ DONE
5. **Razorpay Payment Integration** — SKIPPED
6. ~~**Celery/Redis Production Scale**~~ ✅ DONE
7. **User Authentication** — Login/signup, user accounts
8. **PostgreSQL Database** — Persistent project storage
9. **AWS S3 Storage** — Cloud file storage
10. **GPU Deployment** — Faster Whisper + video processing
