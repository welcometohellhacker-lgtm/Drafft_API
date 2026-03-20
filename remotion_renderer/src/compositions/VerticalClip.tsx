import React from 'react';
import {
  AbsoluteFill,
  Audio,
  Img,
  OffthreadVideo,
  Sequence,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import {getStyleProfile} from './StyleUtils';

const secToFrame = (sec: number, fps: number) => Math.max(0, Math.floor(sec * fps));

// ─── Caption Layer ────────────────────────────────────────────────────────────
const CaptionLayer: React.FC<{captions: any; style: string}> = ({captions, style}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const profile = getStyleProfile(style);
  const activeGroup = (captions?.groups || []).find((g: any) => {
    const from = secToFrame(g.start_time, fps);
    const to = secToFrame(g.end_time, fps);
    return frame >= from && frame <= to;
  });
  if (!activeGroup) return null;
  const from = secToFrame(activeGroup.start_time, fps);
  const pop = spring({frame: frame - from, fps, config: {damping: 10}});
  return (
    <div
      style={{
        position: 'absolute',
        bottom: 140,
        left: 48,
        right: 48,
        display: 'flex',
        justifyContent: 'center',
      }}
    >
      <div
        style={{
          fontSize: 54,
          fontWeight: 900,
          padding: '18px 28px',
          borderRadius: 28,
          background: profile.captionBg,
          textAlign: 'center',
          lineHeight: 1.12,
          boxShadow: profile.accentGlow,
          transform: `scale(${0.96 + pop * 0.04})`,
        }}
      >
        {activeGroup.words?.map((word: any, idx: number) => {
          const wf = secToFrame(word.start_time, fps);
          const wt = secToFrame(word.end_time, fps);
          const active = frame >= wf && frame <= wt;
          const isHighlight = word.text === activeGroup.highlight;
          return (
            <span
              key={idx}
              style={{
                color: active || isHighlight ? '#00E5A8' : '#FFFFFF',
                marginRight: 10,
                textShadow: active ? '0 0 24px rgba(0,229,168,.55)' : 'none',
                transition: 'color 0.1s',
              }}
            >
              {word.text}
            </span>
          );
        })}
      </div>
    </div>
  );
};

// ─── Overlay Layer ────────────────────────────────────────────────────────────
const OverlayLayer: React.FC<{visuals: any; ctaText: string; style: string}> = ({
  visuals,
  ctaText,
  style,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const profile = getStyleProfile(style);
  return (
    <>
      {(visuals?.overlayTimeline || []).map((overlay: any, idx: number) => {
        const from = secToFrame(overlay.start || 0, fps);
        const to = secToFrame(overlay.end || 0, fps);
        if (frame < from || frame > to) return null;
        const progress = spring({frame: frame - from, fps, config: {damping: 14}});
        const isCta = overlay.type === 'cta_overlay';
        return (
          <div
            key={idx}
            style={{
              position: 'absolute',
              left: 50,
              right: 50,
              bottom: isCta ? 260 : 1640,
              transform: `translateY(${(1 - progress) * 30}px) scale(${0.94 + progress * 0.06})`,
              opacity: progress,
            }}
          >
            <div
              style={{
                background: isCta ? '#00E5A8' : '#00000066',
                color: isCta ? '#04111f' : '#fff',
                padding: '16px 22px',
                borderRadius: 24,
                fontSize: isCta ? 34 : 24,
                fontWeight: 900,
                textAlign: 'center',
                boxShadow: profile.accentGlow,
              }}
            >
              {overlay.text || ctaText}
            </div>
          </div>
        );
      })}
    </>
  );
};

// ─── B-roll Item (runs inside a Sequence so frame is 0-based) ─────────────────
const BrollItem: React.FC<{item: any; durationFrames: number}> = ({item, durationFrames}) => {
  const frame = useCurrentFrame();
  const fadeFrames = Math.min(10, Math.floor(durationFrames * 0.2));
  const opacity = interpolate(
    frame,
    [0, fadeFrames, durationFrames - fadeFrames, durationFrames],
    [0, 1, 1, 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );
  const scale = interpolate(frame, [0, durationFrames], [1.0, 1.06], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const isVideo =
    item.asset_type === 'highlight_clip' || Boolean(item.asset_url?.match(/\.mp4(\?|$)/i));
  return (
    <AbsoluteFill style={{opacity}}>
      {isVideo ? (
        <OffthreadVideo
          src={item.asset_url}
          style={{width: '100%', height: '100%', objectFit: 'cover', transform: `scale(${scale})`}}
        />
      ) : (
        <Img
          src={item.asset_url}
          style={{width: '100%', height: '100%', objectFit: 'cover', transform: `scale(${scale})`}}
        />
      )}
    </AbsoluteFill>
  );
};

// ─── B-roll Layer ─────────────────────────────────────────────────────────────
const BrollLayer: React.FC<{visuals: any}> = ({visuals}) => {
  const {fps} = useVideoConfig();
  return (
    <>
      {(visuals?.brollTimeline || []).map((item: any, idx: number) => {
        if (!item.asset_url) return null;
        const from = secToFrame(item.start || 0, fps);
        const to = secToFrame(item.end || 0, fps);
        const durationFrames = Math.max(2, to - from);
        return (
          <Sequence key={idx} from={from} durationInFrames={durationFrames} layout="none">
            <BrollItem item={item} durationFrames={durationFrames} />
          </Sequence>
        );
      })}
    </>
  );
};

// ─── Motion FX ───────────────────────────────────────────────────────────────
const MotionFX: React.FC<{visuals: any}> = ({visuals}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const activeZoom = (visuals?.zoomEvents || []).find((z: any) => {
    const from = secToFrame(z.start || 0, fps);
    const to = secToFrame(z.end || 0, fps);
    return frame >= from && frame <= to;
  });
  if (!activeZoom) return null;
  const from = secToFrame(activeZoom.start || 0, fps);
  const to = secToFrame(activeZoom.end || 0, fps);
  const zoom = interpolate(
    frame,
    [from, to],
    [1, activeZoom.type === 'hook_punch_in' ? 1.08 : 1.04],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );
  return <AbsoluteFill style={{transform: `scale(${zoom})`}} />;
};

// ─── Main Composition ─────────────────────────────────────────────────────────
export const VerticalClip: React.FC<any> = (props) => {
  const frame = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();
  const profile = getStyleProfile(props.captions?.style || 'finance_clean');
  const titleProgress = spring({frame, fps, config: {damping: 12}});
  const clipStartFrom = secToFrame(props.clipStartSec || 0, fps);
  const duration = Math.max(1, secToFrame(props.clipDurationSec || 15, fps));
  const brand = props.branding?.brand_settings || {};
  const bg = `linear-gradient(180deg, ${props.colorPalette?.primary || '#0A2540'} 0%, #020617 100%)`;
  const titleText = String(props.title || '');

  // Fade in/out the whole composition
  const globalOpacity = interpolate(
    frame,
    [0, 8, durationInFrames - 8, durationInFrames],
    [0, 1, 1, 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );

  return (
    <AbsoluteFill
      style={{
        background: bg,
        color: props.colorPalette?.text || '#fff',
        fontFamily: brand.font_family || props.fontFamily || 'Inter',
        opacity: globalOpacity,
      }}
    >
      {/* ── Main source video ── */}
      {props.sourceVideoUrl ? (
        <OffthreadVideo
          src={props.sourceVideoUrl}
          startFrom={clipStartFrom}
          endAt={clipStartFrom + duration}
          style={{width: '100%', height: '100%', objectFit: 'cover'}}
          volume={1}
        />
      ) : null}

      {/* ── Cinematic gradient vignette ── */}
      <AbsoluteFill
        style={{
          background:
            'linear-gradient(180deg, rgba(0,0,0,.25) 0%, transparent 30%, transparent 60%, rgba(0,0,0,.72) 100%)',
        }}
      />

      {/* ── B-roll video/image cuts (highlight clips + prompts) ── */}
      <BrollLayer visuals={props.visuals} />

      {/* ── Subtle zoom motion on main video ── */}
      <MotionFX visuals={props.visuals} />

      {/* ── Top bar branding ── */}
      <div
        style={{
          position: 'absolute',
          top: 60,
          left: 50,
          right: 50,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        <div style={{fontSize: 20, letterSpacing: 3, opacity: 0.82, fontWeight: 600}}>
          DRAFFT • VIRAL ENGINE
        </div>
        <div style={{fontSize: 17, opacity: 0.65}}>{props.animationPack}</div>
      </div>

      {/* ── Title + hook (first 3.5s) ── */}
      <Sequence from={0} durationInFrames={Math.min(durationInFrames, 105)}>
        <div
          style={{
            position: 'absolute',
            top: 140,
            left: 50,
            right: 50,
            transform: `scale(${0.92 + titleProgress * 0.08})`,
          }}
        >
          <div
            style={{
              fontSize: profile.titleSize,
              lineHeight: 0.98,
              fontWeight: 900,
              textTransform: profile.titleTransform as any,
              textShadow: '0 10px 32px rgba(0,0,0,.45)',
            }}
          >
            {titleText}
          </div>
          <div
            style={{
              fontSize: profile.hookSize,
              marginTop: 16,
              color: props.colorPalette?.accent || '#00E5A8',
              fontWeight: 700,
              textShadow: '0 4px 16px rgba(0,229,168,.3)',
            }}
          >
            {props.hook}
          </div>
        </div>
      </Sequence>

      {/* ── Word-level captions ── */}
      <CaptionLayer captions={props.captions} style={props.captions?.style || 'finance_clean'} />

      {/* ── CTA + overlays ── */}
      <OverlayLayer
        visuals={props.visuals}
        ctaText={props.ctaText}
        style={props.captions?.style || 'finance_clean'}
      />

      {/* ── Narration audio ── */}
      {props.audio?.narrationAudioUrl ? (
        <Audio src={props.audio.narrationAudioUrl} volume={1} />
      ) : null}

      {/* ── Background music (ElevenLabs generated, looped at low volume) ── */}
      {props.audio?.backgroundMusicUrl ? (
        <Audio src={props.audio.backgroundMusicUrl} volume={0.18} loop />
      ) : null}
    </AbsoluteFill>
  );
};
