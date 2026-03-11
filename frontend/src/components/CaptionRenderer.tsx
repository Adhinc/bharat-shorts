"use client";

import { AbsoluteFill, useCurrentFrame, useVideoConfig, interpolate, spring } from "remotion";

export interface CaptionWord {
  text: string;
  start: number;
  end: number;
  confidence: number;
}

export interface CaptionSegment {
  id: string;
  words: CaptionWord[];
  text: string;
  start: number;
  end: number;
}

export interface CaptionStyleProps {
  template: string;
  fontFamily: string;
  fontSize: number;
  primaryColor: string;
  highlightColor: string;
  position: "bottom" | "center" | "top";
  animation: "pop" | "fade" | "typewriter" | "karaoke";
}

interface Props {
  segments: CaptionSegment[];
  style: CaptionStyleProps;
}

export const CaptionRenderer: React.FC<Props> = ({ segments, style }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const currentTime = frame / fps;

  // Find active segment
  const activeSegment = segments.find(
    (seg) => currentTime >= seg.start && currentTime <= seg.end
  );

  if (!activeSegment) return null;

  const positionStyle: React.CSSProperties = {
    bottom: style.position === "bottom" ? "10%" : undefined,
    top: style.position === "top" ? "10%" : style.position === "center" ? "45%" : undefined,
  };

  return (
    <AbsoluteFill>
      <div
        style={{
          position: "absolute",
          left: "5%",
          right: "5%",
          display: "flex",
          justifyContent: "center",
          flexWrap: "wrap",
          gap: "6px",
          ...positionStyle,
        }}
      >
        {activeSegment.words.map((word, i) => (
          <WordRenderer
            key={`${activeSegment.id}-${i}`}
            word={word}
            index={i}
            segmentStart={activeSegment.start}
            style={style}
            currentTime={currentTime}
            fps={fps}
            frame={frame}
          />
        ))}
      </div>
    </AbsoluteFill>
  );
};

const WordRenderer: React.FC<{
  word: CaptionWord;
  index: number;
  segmentStart: number;
  style: CaptionStyleProps;
  currentTime: number;
  fps: number;
  frame: number;
}> = ({ word, index, segmentStart, style, currentTime, fps, frame }) => {
  const isActive = currentTime >= word.start && currentTime <= word.end;
  const isPast = currentTime > word.end;
  const wordStartFrame = Math.floor(word.start * fps);

  let opacity = 1;
  let scale = 1;
  let color = style.primaryColor;

  switch (style.animation) {
    case "karaoke":
      if (isActive) {
        color = style.highlightColor;
        scale = 1.15;
      } else if (isPast) {
        color = style.primaryColor;
      } else {
        opacity = 0.5;
      }
      break;

    case "pop":
      if (isActive) {
        color = style.highlightColor;
        const s = spring({ frame: frame - wordStartFrame, fps, durationInFrames: 10 });
        scale = interpolate(s, [0, 1], [0.5, 1.2]);
      }
      break;

    case "fade":
      if (frame < wordStartFrame) {
        opacity = 0;
      } else {
        opacity = interpolate(frame, [wordStartFrame, wordStartFrame + 8], [0, 1], {
          extrapolateRight: "clamp",
        });
        if (isActive) color = style.highlightColor;
      }
      break;

    case "typewriter":
      if (frame < wordStartFrame) {
        opacity = 0;
      }
      if (isActive) color = style.highlightColor;
      break;
  }

  const templateStyles = getTemplateStyles(style.template);

  return (
    <span
      style={{
        fontFamily: style.fontFamily,
        fontSize: style.fontSize,
        color,
        opacity,
        transform: `scale(${scale})`,
        transition: "transform 0.1s, color 0.1s",
        fontWeight: "bold",
        textShadow: "2px 2px 8px rgba(0,0,0,0.8), 0 0 20px rgba(0,0,0,0.5)",
        display: "inline-block",
        ...templateStyles,
      }}
    >
      {word.text}
    </span>
  );
};

function getTemplateStyles(template: string): React.CSSProperties {
  switch (template) {
    case "hormozi":
      return {
        textTransform: "uppercase",
        letterSpacing: "2px",
      };
    case "mrbeast":
      return {
        textTransform: "uppercase",
        WebkitTextStroke: "2px black",
        letterSpacing: "1px",
      };
    case "minimal":
      return {
        fontWeight: "normal",
        textShadow: "1px 1px 4px rgba(0,0,0,0.6)",
      };
    case "hindi-pop":
      return {
        letterSpacing: "1px",
        textShadow: "3px 3px 0 #FF6B00, 0 0 20px rgba(255,107,0,0.3)",
      };
    case "news":
      return {
        backgroundColor: "rgba(0,0,0,0.75)",
        padding: "4px 12px",
        borderRadius: "4px",
        textShadow: "none",
      };
    default:
      return {};
  }
}
