import React from 'react';
import {Composition} from 'remotion';
import {VerticalClip} from './compositions/VerticalClip';

const defaultProps = {
  title: 'Drafft Clip',
  hook: 'Hook goes here',
  ctaText: 'Book a call today',
  clipStartSec: 0,
  clipEndSec: 15,
  clipDurationSec: 15,
  fps: 30,
  sourceVideoUrl: '',
  captions: {words: [], groups: [], style: 'finance_clean'},
  visuals: {
    brollTimeline: [],
    overlayTimeline: [],
    transitionTimeline: [],
    zoomEvents: [],
    thumbnailTextOptions: [],
    renderNotes: {},
  },
  branding: {},
  colorPalette: {primary: '#0A2540', accent: '#00E5A8', text: '#FFFFFF'},
  animationPack: 'clean_finance_flow',
  transitionPack: 'smooth_fades',
  audio: {},
  composition: {width: 1080, height: 1920, aspectRatio: '9:16'},
};

export const Root: React.FC = () => {
  return (
    <>
      <Composition
        id="VerticalClip"
        component={VerticalClip}
        durationInFrames={450}
        fps={30}
        width={1080}
        height={1920}
        defaultProps={defaultProps}
        calculateMetadata={({props}: {props: any}) => {
          const fps = props.fps || 30;
          const durationInFrames = Math.max(30, Math.ceil((props.clipDurationSec || 15) * fps));
          return {
            durationInFrames,
            fps,
            width: props.composition?.width || 1080,
            height: props.composition?.height || 1920,
          };
        }}
      />
    </>
  );
};
