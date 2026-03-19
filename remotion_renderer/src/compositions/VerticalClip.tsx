import React from 'react';
import {AbsoluteFill, Audio, Img, OffthreadVideo, Sequence, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {getStyleProfile} from './StyleUtils';

const secToFrame = (sec: number, fps: number) => Math.max(0, Math.floor(sec * fps));

const CaptionLayer: React.FC<any> = ({captions, style}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const profile = getStyleProfile(style);
  const activeGroup = (captions?.groups || []).find((group: any) => {
    const from = secToFrame(group.start_time, fps);
    const to = secToFrame(group.end_time, fps);
    return frame >= from && frame <= to;
  });
  if (!activeGroup) return null;
  return (
    <div style={{position:'absolute', bottom:120, left:56, right:56, display:'flex', justifyContent:'center'}}>
      <div style={{fontSize:52, fontWeight:900, padding:'18px 24px', borderRadius:28, background:profile.captionBg, textAlign:'center', lineHeight:1.1, boxShadow: profile.accentGlow}}>
        {activeGroup.words?.map((word: any, idx: number) => (
          <span key={idx} style={{color: word.text === activeGroup.highlight ? '#00E5A8' : '#FFFFFF', marginRight: 10}}>{word.text}</span>
        ))}
      </div>
    </div>
  );
};

const OverlayLayer: React.FC<any> = ({visuals, ctaText, style}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const profile = getStyleProfile(style);
  return (
    <>
      {(visuals?.overlayTimeline || []).map((overlay: any, idx: number) => {
        const from = secToFrame(overlay.start || 0, fps);
        const to = secToFrame(overlay.end || 0, fps);
        if (frame < from || frame > to) return null;
        const progress = spring({frame: frame - from, fps, config:{damping:14}});
        const isCta = overlay.type === 'cta_overlay';
        return (
          <div key={idx} style={{position:'absolute', left:50, right:50, bottom: isCta ? 260 : 1640, transform:`translateY(${(1-progress)*30}px) scale(${0.94 + progress * 0.06})`, opacity: progress}}>
            <div style={{background: isCta ? '#00E5A8' : '#00000066', color: isCta ? '#04111f' : '#fff', padding:'16px 20px', borderRadius:24, fontSize: isCta ? 34 : 24, fontWeight:900, textAlign:'center', boxShadow: profile.accentGlow}}>
              {overlay.text || ctaText}
            </div>
          </div>
        );
      })}
    </>
  );
};

const BrollLayer: React.FC<any> = ({visuals}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  return (
    <>
      {(visuals?.brollTimeline || []).map((item: any, idx: number) => {
        if (!item.asset_url) return null;
        const from = secToFrame(item.start || 0, fps);
        const to = secToFrame(item.end || 0, fps);
        if (frame < from || frame > to) return null;
        const scale = interpolate(frame, [from, to], [1, 1.08]);
        const opacity = interpolate(frame, [from, from + 8, to - 8, to], [0, 0.44, 0.44, 0]);
        return (
          <AbsoluteFill key={idx} style={{opacity}}>
            <Img src={item.asset_url} style={{width:'100%', height:'100%', objectFit:'cover', transform:`scale(${scale})`}} />
          </AbsoluteFill>
        );
      })}
    </>
  );
};

export const VerticalClip: React.FC<any> = (props) => {
  const frame = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();
  const profile = getStyleProfile(props.captions?.style || 'finance_clean');
  const titleProgress = spring({frame, fps, config:{damping: 12}});
  const clipStartFrom = secToFrame(props.clipStartSec || 0, fps);
  const duration = Math.max(1, secToFrame(props.clipDurationSec || 15, fps));
  const brand = props.branding?.brand_settings || {};
  const bg = `linear-gradient(180deg, ${props.colorPalette?.primary || '#0A2540'}, #020617)`;
  const titleText = (props.title || '').toString();
  return (
    <AbsoluteFill style={{background:bg, color: props.colorPalette?.text || '#fff', fontFamily: brand.font_family || props.fontFamily || 'Inter'}}>
      {props.sourceVideoUrl ? (
        <OffthreadVideo
          src={props.sourceVideoUrl}
          startFrom={clipStartFrom}
          endAt={clipStartFrom + duration}
          style={{width:'100%', height:'100%', objectFit:'cover'}}
        />
      ) : null}

      <AbsoluteFill style={{background:'linear-gradient(180deg, rgba(0,0,0,.1), rgba(0,0,0,.58))'}} />
      <BrollLayer visuals={props.visuals} />

      <div style={{position:'absolute', top:50, left:50, right:50, display:'flex', justifyContent:'space-between', alignItems:'center'}}>
        <div style={{fontSize:22, letterSpacing:2, opacity:0.88}}>DRAFFT • VIRAL ENGINE</div>
        <div style={{fontSize:18, opacity:0.75}}>{props.animationPack}</div>
      </div>

      <Sequence from={0} durationInFrames={Math.min(durationInFrames, 110)}>
        <div style={{position:'absolute', top:130, left:50, right:50, transform:`scale(${0.92 + titleProgress * 0.08})`}}>
          <div style={{fontSize:profile.titleSize, lineHeight:0.98, fontWeight:900, textTransform: profile.titleTransform as any, textShadow:'0 10px 30px rgba(0,0,0,.35)'}}>{titleText}</div>
          <div style={{fontSize:profile.hookSize, marginTop:14, color: props.colorPalette?.accent || '#00E5A8', fontWeight:700}}>{props.hook}</div>
        </div>
      </Sequence>

      <CaptionLayer captions={props.captions} style={props.captions?.style} />
      <OverlayLayer visuals={props.visuals} ctaText={props.ctaText} style={props.captions?.style} />

      {props.audio?.narrationAudioUrl ? <Audio src={props.audio.narrationAudioUrl} volume={1} /> : null}
    </AbsoluteFill>
  );
};
