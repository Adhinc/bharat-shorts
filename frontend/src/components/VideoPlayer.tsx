"use client";

import { Player, PlayerRef } from "@remotion/player";
import { VideoComposition } from "./VideoComposition";
import { CaptionSegment, CaptionStyleProps } from "./CaptionRenderer";
import { useCallback, useRef, useEffect } from "react";

interface Props {
  videoUrl: string;
  segments: CaptionSegment[];
  captionStyle: CaptionStyleProps;
  durationInSeconds: number;
  width: number;
  height: number;
  currentTime: number;
  isPlaying: boolean;
  onTimeUpdate: (time: number) => void;
  onPlayPause: (playing: boolean) => void;
}

export const VideoPlayer: React.FC<Props> = ({
  videoUrl,
  segments,
  captionStyle,
  durationInSeconds,
  width,
  height,
  currentTime,
  isPlaying,
  onTimeUpdate,
  onPlayPause,
}) => {
  const playerRef = useRef<PlayerRef>(null);
  const fps = 30;
  const durationInFrames = Math.ceil(durationInSeconds * fps);

  // Use 9:16 for shorts, keep original for landscape
  const isPortrait = height > width;
  const compositionWidth = isPortrait ? 1080 : 1920;
  const compositionHeight = isPortrait ? 1920 : 1080;

  useEffect(() => {
    const player = playerRef.current;
    if (!player) return;

    const handleFrameUpdate = () => {
      const frame = (player as unknown as { getCurrentFrame?: () => number }).getCurrentFrame?.();
      if (typeof frame === "number") {
        onTimeUpdate(frame / fps);
      }
    };

    player.addEventListener("frameupdate", handleFrameUpdate);
    return () => player.removeEventListener("frameupdate", handleFrameUpdate);
  }, [onTimeUpdate, fps]);

  const handleTogglePlay = useCallback(() => {
    const player = playerRef.current;
    if (!player) return;
    if (isPlaying) {
      player.pause();
      onPlayPause(false);
    } else {
      player.play();
      onPlayPause(true);
    }
  }, [isPlaying, onPlayPause]);

  return (
    <div className="flex flex-col items-center gap-4">
      <div
        className="rounded-lg overflow-hidden shadow-2xl"
        style={{ maxHeight: "70vh" }}
      >
        <Player
          ref={playerRef}
          component={VideoComposition}
          inputProps={{
            videoUrl,
            segments,
            captionStyle,
          }}
          durationInFrames={durationInFrames || 1}
          fps={fps}
          compositionWidth={compositionWidth}
          compositionHeight={compositionHeight}
          style={{
            width: isPortrait ? "auto" : "100%",
            height: isPortrait ? "70vh" : "auto",
            maxWidth: "100%",
          }}
          controls={false}
          autoPlay={false}
        />
      </div>

      <div className="flex items-center gap-3">
        <button
          onClick={handleTogglePlay}
          className="rounded-full bg-orange-500 px-5 py-2 text-sm font-semibold text-white hover:bg-orange-600 transition-colors"
        >
          {isPlaying ? "Pause" : "Play"}
        </button>
        <span className="text-sm text-neutral-400 font-mono">
          {formatTime(currentTime)} / {formatTime(durationInSeconds)}
        </span>
      </div>
    </div>
  );
};

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}
