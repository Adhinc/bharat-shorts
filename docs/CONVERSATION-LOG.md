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

## Next Steps (Priority Order)
1. Auth (Google OAuth + email)
2. PostgreSQL database for persistent projects
3. S3 file storage
4. Razorpay payment integration
5. GPU deployment for Whisper
6. Automated tests
7. Deploy to AWS ap-south-1
