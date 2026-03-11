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
  animation: "pop" | "fade" | "typewriter" | "karaoke" | "bounce" | "glow" | "shake" | "emoji-pop";
}

// Emoji map for emoji-pop animation — maps keywords to emojis
const EMOJI_MAP: Record<string, string> = {
  fire: "\u{1F525}", hot: "\u{1F525}", amazing: "\u{1F525}",
  love: "\u{2764}\u{FE0F}", heart: "\u{2764}\u{FE0F}",
  money: "\u{1F4B0}", rich: "\u{1F4B0}", earn: "\u{1F4B0}", paisa: "\u{1F4B0}",
  wow: "\u{1F62E}", shocked: "\u{1F62E}", omg: "\u{1F62E}",
  laugh: "\u{1F602}", funny: "\u{1F602}", lol: "\u{1F602}", haha: "\u{1F602}",
  cry: "\u{1F62D}", sad: "\u{1F62D}",
  win: "\u{1F3C6}", trophy: "\u{1F3C6}", champion: "\u{1F3C6}",
  rocket: "\u{1F680}", launch: "\u{1F680}", grow: "\u{1F680}",
  star: "\u{2B50}", best: "\u{2B50}",
  india: "\u{1F1EE}\u{1F1F3}", bharat: "\u{1F1EE}\u{1F1F3}", desh: "\u{1F1EE}\u{1F1F3}",
  food: "\u{1F35B}", khana: "\u{1F35B}",
  music: "\u{1F3B5}", song: "\u{1F3B5}", gana: "\u{1F3B5}",
  think: "\u{1F914}", soch: "\u{1F914}",
  clap: "\u{1F44F}", bravo: "\u{1F44F}", shabash: "\u{1F44F}",
  stop: "\u{1F6D1}", danger: "\u{26A0}\u{FE0F}",
  subscribe: "\u{1F514}", bell: "\u{1F514}",
  like: "\u{1F44D}", accha: "\u{1F44D}",
  no: "\u{274C}", nahi: "\u{274C}",
  yes: "\u{2705}", haan: "\u{2705}",
  secret: "\u{1F92B}", shhh: "\u{1F92B}",
  strong: "\u{1F4AA}", power: "\u{1F4AA}",
  time: "\u{23F0}", jaldi: "\u{23F0}",
  eyes: "\u{1F440}", dekho: "\u{1F440}", look: "\u{1F440}",
};

function getEmojiForWord(word: string): string | null {
  const lower = word.toLowerCase().replace(/[^a-z]/g, "");
  return EMOJI_MAP[lower] || null;
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
  let translateY = 0;
  let rotate = 0;
  let extraShadow = "";
  let emojiOverlay: string | null = null;

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

    case "bounce": {
      if (isActive) {
        color = style.highlightColor;
        const elapsed = frame - wordStartFrame;
        // Spring bounce: overshoot then settle
        const s = spring({
          frame: elapsed,
          fps,
          durationInFrames: 15,
          config: { damping: 8, stiffness: 200, mass: 0.5 },
        });
        scale = interpolate(s, [0, 1], [0.3, 1.1]);
        // Bounce up then down
        translateY = interpolate(s, [0, 0.5, 1], [-30, -50, 0], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        });
      } else if (!isPast) {
        opacity = 0.4;
        scale = 0.8;
      }
      break;
    }

    case "glow": {
      if (isActive) {
        color = style.highlightColor;
        scale = 1.1;
        // Pulsing glow effect
        const pulse = Math.sin((frame - wordStartFrame) * 0.4) * 0.5 + 0.5;
        const glowIntensity = Math.floor(10 + pulse * 25);
        extraShadow = `, 0 0 ${glowIntensity}px ${style.highlightColor}, 0 0 ${glowIntensity * 2}px ${style.highlightColor}40`;
      } else if (isPast) {
        color = style.primaryColor;
      } else {
        opacity = 0.6;
      }
      break;
    }

    case "shake": {
      if (isActive) {
        color = style.highlightColor;
        scale = 1.15;
        // Rapid shake on word hit, then settle
        const elapsed = frame - wordStartFrame;
        if (elapsed < 6) {
          const shakeAmount = interpolate(elapsed, [0, 6], [4, 0], {
            extrapolateRight: "clamp",
          });
          translateY = Math.sin(elapsed * 3) * shakeAmount;
          rotate = Math.cos(elapsed * 2.5) * shakeAmount * 0.8;
        }
      } else if (!isPast) {
        opacity = 0.5;
      }
      break;
    }

    case "emoji-pop": {
      if (isActive) {
        color = style.highlightColor;
        const s = spring({ frame: frame - wordStartFrame, fps, durationInFrames: 12 });
        scale = interpolate(s, [0, 1], [0.6, 1.15]);
        emojiOverlay = getEmojiForWord(word.text);
      } else if (!isPast) {
        opacity = 0.5;
      }
      break;
    }

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
        transform: `scale(${scale}) translateY(${translateY}px) rotate(${rotate}deg)`,
        fontWeight: "bold",
        textShadow: `2px 2px 8px rgba(0,0,0,0.8), 0 0 20px rgba(0,0,0,0.5)${extraShadow}`,
        display: "inline-block",
        position: "relative",
        ...templateStyles,
      }}
    >
      {word.text}
      {emojiOverlay && (
        <span
          style={{
            position: "absolute",
            top: "-0.8em",
            right: "-0.3em",
            fontSize: style.fontSize * 0.6,
            filter: "drop-shadow(0 2px 4px rgba(0,0,0,0.5))",
            animation: undefined,
            transform: `scale(${interpolate(
              spring({ frame: frame - wordStartFrame, fps, durationInFrames: 15, config: { damping: 10, stiffness: 150 } }),
              [0, 1],
              [0, 1.2]
            )})`,
          }}
        >
          {emojiOverlay}
        </span>
      )}
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
