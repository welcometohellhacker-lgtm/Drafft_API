import React from 'react';
import {Composition} from 'remotion';
import {VerticalClip} from './compositions/VerticalClip';

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
        defaultProps={{
          title: 'Drafft Clip',
          hook: 'Hook goes here',
          ctaText: 'Book a call today',
          clipStartSec: 0,
          clipEndSec: 15,
          clipDurationSec: 15,
          sourceVideoUrl: '',
          captions: {words: [], groups: [], style: 'finance_clean'},
          visuals: {brollTimeline: [], overlayTimeline: [], transitionTimeline: [], zoomEvents: [], thumbnailTextOptions: [], renderNotes: {}},
          branding: {},
          colorPalette: {primary: '#0A2540', accent: '#00E5A8', text: '#FFFFFF'},
          animationPack: 'clean_finance_flow',
          transitionPack: 'smooth_fades',
          audio: {}
        }}
      />
    </>
  );
};
