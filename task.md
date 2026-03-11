# Bharat-Shorts Implementation Roadmap

We've discovered that the core foundation (transcription, basic editing, backend API) is already built. Below are the advanced features remaining to make this a true Submagic competitor.

## Phase 1: AI Precision (Current Focus)
- [/] **Smart Face-Centric Reframe** <!-- id: 10 -->
    - [/] Integrate MediaPipe face detection in `backend/services/reframe.py`
    - [ ] Implement dynamic cropping that follows the speaker
- [ ] **AI Eye Contact Correction** <!-- id: 11 -->
    - [ ] Research/Integrate GAN-based model for focal point correction
- [ ] **Advanced Transcription** <!-- id: 12 -->
    - [ ] Fine-tune IndicWhisper for better regional dialect handling

## Phase 2: High-End Aesthetics
- [ ] **Remotion Export Engine** <!-- id: 13 -->
    - [ ] Replace FFmpeg-ASS rendering with Remotion-based high-fidelity rendering
    - [ ] Support complex animations (pop, bounce, emoji-swaps)
- [ ] **Automated SFX & Music** <!-- id: 14 -->
    - [ ] Auto-generate transitions with "Whoosh" sounds
    - [ ] Auto-duck music using the implemented ducking logic in `broll.py`
- [ ] **AI Stock Integration** <!-- id: 15 -->
    - [ ] Connect Pexels/Pixabay specifically for Indian landscape/city stock

## Phase 3: Commercial & Scale
- [/] **Payment Integration** <!-- id: 16 -->
    - [ ] Razorpay hooks for subscription management
- [ ] **Celery/Redis Scale** <!-- id: 17 -->
    - [ ] Setup production workers for high-res 4K renders

## Project Status
- **Backend:** Functional MVP (FastAPI)
- **Frontend:** Functional Editor (Next.js + Remotion Player)
- **Git:** Synced
