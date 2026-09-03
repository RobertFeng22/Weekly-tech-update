import React from 'react';
import {CalculateMetadataFunction, Composition} from 'remotion';
import {WeeklyAI} from './weekly-ai';
import type {WeeklyVideoProps} from './types';

const defaultProps: WeeklyVideoProps = {
  editionDate: '2026-08-26',
  windowStart: '2026-08-19',
  windowEnd: '2026-08-25',
  title: 'AI Weekly',
  subtitle: 'Evidence-gated engineering lessons',
  disclosure: 'AI-generated narration',
  candidateCount: 9,
  approvedCount: 3,
  fps: 30,
  width: 1920,
  height: 1080,
  totalDurationInFrames: 300,
  scenes: [],
};

const calculateMetadata: CalculateMetadataFunction<WeeklyVideoProps> = ({props}) => ({
  durationInFrames: props.totalDurationInFrames,
  fps: props.fps,
  width: props.width,
  height: props.height,
  defaultCodec: 'h264',
  defaultPixelFormat: 'yuv420p',
  props,
});

export const RemotionRoot: React.FC = () => (
  <Composition
    id="WeeklyAI"
    component={WeeklyAI}
    durationInFrames={defaultProps.totalDurationInFrames}
    fps={defaultProps.fps}
    width={defaultProps.width}
    height={defaultProps.height}
    defaultProps={defaultProps}
    calculateMetadata={calculateMetadata}
  />
);
