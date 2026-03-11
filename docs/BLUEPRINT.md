# Bharat-Shorts: Master Architecture & Implementation Blueprint

## Quick Reference

### Tech Stack
- **Frontend**: Next.js 14+ (App Router), Zustand, Remotion
- **Backend**: FastAPI (Python), Redis + Celery, PostgreSQL, Pinecone/Weaviate
- **Infra**: AWS ap-south-1, S3, CloudFront, Razorpay

### Implementation Phases
1. Video Processing Pipeline (Silence Removal, FFmpeg)
2. Multi-Lingual Transcription (Faster-Whisper, Hinglish)
3. Caption Architect UI (Remotion templates)
4. Magic Clips (Highlight extraction, Face Centering)
5. B-Roll & SFX Automation (CLIP, Pexels, Audio Ducking)
6. Scaling & API (Docker, Razorpay subscriptions)

### Priority
> Transcription-to-Remotion bridge first. Text edit → instant video update = core value prop.

### Performance Targets
| Metric | Target |
|--------|--------|
| Transcription Latency | < 20% of video duration |
| Rendering Speed (4K 60fps) | < 2.0x video duration |
| Accuracy (Hindi/Marathi) | > 97% |
| UI Startup Time | < 3 seconds |

### Pricing
- Free: 2 clips forever
- Business: ₹2,999 - ₹4,999/month
- Model: Usage-based (per minute processed)
