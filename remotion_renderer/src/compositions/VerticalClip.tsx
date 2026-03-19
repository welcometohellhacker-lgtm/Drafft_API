import React from 'react';
import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';

export const VerticalClip: React.FC<any> = (props) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const titleScale = spring({frame, fps, config: {damping: 12}});
  const captionOpacity = interpolate(frame, [0, 15], [0, 1], {extrapolateRight: 'clamp'});
  const bg = `radial-gradient(circle at top, ${props.colorPalette?.accent || '#00E5A8'}22, transparent 35%), linear-gradient(180deg, ${props.colorPalette?.primary || '#0A2540'}, #020617)`;
  const firstCaption = props.captionGroups?.[0]?.text || props.hook;
  return (
    <AbsoluteFill style={{background: bg, color: props.colorPalette?.text || '#fff', fontFamily: props.branding?.brand_settings?.font_family || props.fontFamily || 'Inter', justifyContent: 'space-between', padding: 70}}>
      <div style={{fontSize: 30, opacity: 0.85, letterSpacing: 2}}>DRAFFT • {props.animationPack}</div>
      <div style={{transform: `scale(${titleScale})`}}>
        <div style={{fontSize: 84, fontWeight: 800, lineHeight: 1.0, textTransform: 'uppercase'}}>{props.title}</div>
        <div style={{fontSize: 36, marginTop: 20, color: props.colorPalette?.accent || '#00E5A8'}}>{props.hook}</div>
      </div>
      <div>
        <div style={{opacity: captionOpacity, fontSize: 46, fontWeight: 700, background: '#00000055', borderRadius: 28, padding: '22px 28px', display: 'inline-block'}}>{firstCaption}</div>
        <div style={{marginTop: 28, fontSize: 28, opacity: 0.85}}>CTA: {props.ctaText}</div>
        <div style={{marginTop: 14, fontSize: 22, opacity: 0.65}}>Transitions: {props.transitionPack}</div>
      </div>
    </AbsoluteFill>
  );
};
