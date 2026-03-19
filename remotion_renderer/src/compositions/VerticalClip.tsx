import React from 'react';
import {AbsoluteFill, Audio, Img, OffthreadVideo, Sequence, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';

const msToFrame = (ms: number, fps: number) => Math.max(0, Math.floor((ms / 1000) * fps));
const secToFrame = (sec: number, fps: number) => Math.max(0, Math.floor(sec * fps));

const CaptionLayer: React.FC<any> = ({captions}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const activeGroup = (captions?.groups || []).find((group: any) => {
    const from = secToFrame(group.start_time, fps);
    const to = secToFrame(group.end_time, fps);
    return frame >= from && frame <= to;
  });
  if (!activeGroup) return null;
  return (
    <div style={{position:'absolute', bottom:120, left:60, right:60, display:'flex', justifyContent:'center'}}>
      <div style={{fontSize:52, fontWeight:800, padding:'18px 24px', borderRadius:28, background:'#00000088', textAlign:'center', lineHeight:1.1}}>{activeGroup.text}</div>
    </div>
  );
};

const OverlayLayer: React.FC<any> = ({visuals, ctaText}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  return (
    <>
      {(visuals?.overlayTimeline || []).map((overlay: any, idx: number) => {
        const from = secToFrame(overlay.start || 0, fps);
        const to = secToFrame(overlay.end || 0, fps);
        if (frame < from || frame > to) return null;
        const progress = spring({frame: frame - from, fps, config:{damping:14}});
        return (
          <div key={idx} style={{position:'absolute', left:50, right:50, bottom: overlay.type === 'cta_overlay' ? 260 : 1640, transform:`translateY(${(1-progress)*30}px)`, opacity: progress}}>
            <div style={{background: overlay.type === 'cta_overlay' ? '#00E5A8' : '#00000066', color: overlay.type === 'cta_overlay' ? '#04111f' : '#fff', padding:'16px 20px', borderRadius:24, fontSize: overlay.type === 'cta_overlay' ? 34 : 24, fontWeight:800, textAlign:'center'}}>
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
        return (
          <AbsoluteFill key={idx} style={{opacity:0.42}}>
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
  const titleProgress = spring({frame, fps, config:{damping: 12}});
  const clipStartFrom = secToFrame(props.clipStartSec || 0, fps);
  const duration = Math.max(1, secToFrame(props.clipDurationSec || 15, fps));
  const brand = props.branding?.brand_settings || {};
  const bg = `linear-gradient(180deg, ${props.colorPalette?.primary || '#0A2540'}, #020617)`;
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

      <AbsoluteFill style={{background:'linear-gradient(180deg, rgba(0,0,0,.15), rgba(0,0,0,.5))'}} />
      <BrollLayer visuals={props.visuals} />

      <div style={{position:'absolute', top:50, left:50, right:50, display:'flex', justifyContent:'space-between', alignItems:'center'}}>
        <div style={{fontSize:22, letterSpacing:2, opacity:0.85}}>DRAFFT • VIRAL ENGINE</div>
        <div style={{fontSize:18, opacity:0.75}}>{props.animationPack}</div>
      </div>

      <Sequence from={0} durationInFrames={Math.min(durationInFrames, 110)}>
        <div style={{position:'absolute', top:130, left:50, right:50, transform:`scale(${0.92 + titleProgress * 0.08})`}}>
          <div style={{fontSize:76, lineHeight:0.98, fontWeight:900, textTransform:'uppercase', textShadow:'0 10px 30px rgba(0,0,0,.35)'}}>{props.title}</div>
          <div style={{fontSize:34, marginTop:14, color: props.colorPalette?.accent || '#00E5A8', fontWeight:700}}>{props.hook}</div>
        </div>
      </Sequence>

      <CaptionLayer captions={props.captions} />
      <OverlayLayer visuals={props.visuals} ctaText={props.ctaText} />

      {props.audio?.narrationAudioUrl ? <Audio src={props.audio.narrationAudioUrl} volume={1} /> : null}
    </AbsoluteFill>
  );
};
