# Bharat Shorts - AI Video Automation Platform

## Project Structure
- `frontend/` - Next.js 14+ (App Router), Zustand, Tailwind CSS, Remotion (pending)
- `backend/` - FastAPI, Celery + Redis, FFmpeg pipelines
- `docs/` - Architecture docs and blueprint
- `shared/` - Shared types/contracts between frontend and backend

## Dev Commands
- Frontend: `cd frontend && npm run dev` (port 3000)
- Backend: `cd backend && source venv/bin/activate && uvicorn app.main:app --reload` (port 8000)
- Frontend proxies `/api/v1/*` to backend via next.config.ts rewrites

## Key Decisions
- Monorepo structure (no workspace manager yet — add turborepo/nx if needed later)
- Zustand for state (lightweight, no boilerplate)
- FFmpeg for all video processing (silence removal, trimming, concatenation)
- Placeholder transcription endpoint until Whisper integration (Phase 2)
- India-first: AWS ap-south-1, Razorpay, regional font support, Hinglish

## Implementation Priority
1. Transcription → Remotion bridge (core value prop)
2. Silence removal pipeline
3. Caption templates with Devanagari/Tamil support
4. Magic Clips (highlight extraction)
5. B-Roll automation
