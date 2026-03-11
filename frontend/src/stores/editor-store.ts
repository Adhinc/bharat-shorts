import { create } from "zustand";

export interface TranscriptWord {
  text: string;
  start: number;
  end: number;
  confidence: number;
}

export interface TranscriptSegment {
  id: string;
  words: TranscriptWord[];
  text: string;
  start: number;
  end: number;
  speaker?: string;
}

export interface CaptionStyle {
  template: string;
  fontFamily: string;
  fontSize: number;
  primaryColor: string;
  highlightColor: string;
  position: "bottom" | "center" | "top";
  animation: "pop" | "fade" | "typewriter" | "karaoke" | "bounce" | "glow" | "shake" | "emoji-pop";
}

export interface VideoProject {
  id: string;
  name: string;
  sourceUrl?: string;
  sourceFile?: string;
  duration: number;
  width: number;
  height: number;
  transcript: TranscriptSegment[];
  captionStyle: CaptionStyle;
  status: "idle" | "uploading" | "transcribing" | "editing" | "rendering" | "done" | "error";
  error?: string;
}

interface EditorState {
  project: VideoProject | null;
  currentTime: number;
  isPlaying: boolean;
  selectedSegmentId: string | null;

  setProject: (project: VideoProject) => void;
  updateTranscript: (segments: TranscriptSegment[]) => void;
  updateSegmentText: (segmentId: string, newText: string) => void;
  setCaptionStyle: (style: Partial<CaptionStyle>) => void;
  setCurrentTime: (time: number) => void;
  setIsPlaying: (playing: boolean) => void;
  setSelectedSegment: (id: string | null) => void;
  setStatus: (status: VideoProject["status"], error?: string) => void;
}

const defaultCaptionStyle: CaptionStyle = {
  template: "hormozi",
  fontFamily: "Inter",
  fontSize: 48,
  primaryColor: "#FFFFFF",
  highlightColor: "#FF6B00",
  position: "bottom",
  animation: "karaoke",
};

export const useEditorStore = create<EditorState>((set) => ({
  project: null,
  currentTime: 0,
  isPlaying: false,
  selectedSegmentId: null,

  setProject: (project) => set({ project }),

  updateTranscript: (segments) =>
    set((state) => ({
      project: state.project ? { ...state.project, transcript: segments } : null,
    })),

  updateSegmentText: (segmentId, newText) =>
    set((state) => {
      if (!state.project) return {};
      const segments = state.project.transcript.map((seg) =>
        seg.id === segmentId ? { ...seg, text: newText } : seg
      );
      return { project: { ...state.project, transcript: segments } };
    }),

  setCaptionStyle: (style) =>
    set((state) => ({
      project: state.project
        ? {
            ...state.project,
            captionStyle: { ...state.project.captionStyle, ...style },
          }
        : null,
    })),

  setCurrentTime: (time) => set({ currentTime: time }),
  setIsPlaying: (playing) => set({ isPlaying: playing }),
  setSelectedSegment: (id) => set({ selectedSegmentId: id }),

  setStatus: (status, error) =>
    set((state) => ({
      project: state.project ? { ...state.project, status, error } : null,
    })),
}));
