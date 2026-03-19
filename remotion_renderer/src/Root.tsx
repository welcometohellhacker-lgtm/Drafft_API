import React from 'react';
import {Composition} from 'remotion';
import {VerticalClip} from './compositions/VerticalClip';

export const Root: React.FC = () => {
  return (
    <>
      <Composition
        id="VerticalClip"
        component={VerticalClip}
        durationInFrames={900}
        fps={30}
        width={1080}
        height={1920}
        defaultProps={{
          title: 'Drafft Clip',
          hook: 'Hook goes here',
          ctaText: 'Book a call today',
          aspectRatio: '9:16',
          captionGroups: [],
          brollTimeline: [],
          overlayTimeline: [],
          branding: {},
          colorPalette: {primary: '#0A2540', accent: '#00E5A8', text: '#FFFFFF'},
          animationPack: 'clean_finance_flow',
          transitionPack: 'smooth_fades',
          thumbnailTextOptions: []
        }}
      />
    </>
  );
};
