import {Audio} from '@remotion/media';
import React from 'react';
import {
  AbsoluteFill,
  Easing,
  Sequence,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import type {Accent, VideoScene, WeeklyVideoProps} from './types';

const colors: Record<Accent, {primary: string; soft: string; glow: string}> = {
  cyan: {primary: '#39E6F4', soft: '#103E49', glow: 'rgba(57,230,244,.28)'},
  violet: {primary: '#A78BFA', soft: '#302454', glow: 'rgba(167,139,250,.28)'},
  amber: {primary: '#F9C74F', soft: '#4B3912', glow: 'rgba(249,199,79,.25)'},
};

const fontFamily =
  '"Noto Sans CJK SC", "Noto Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif';

const enterStyle = (frame: number, fps: number, delay = 0): React.CSSProperties => {
  const value = spring({frame: frame - delay, fps, config: {damping: 18, stiffness: 120}});
  return {
    opacity: value,
    transform: `translateY(${interpolate(value, [0, 1], [42, 0])}px)`,
  };
};

const SceneBackground: React.FC<{accent: Accent}> = ({accent}) => {
  const frame = useCurrentFrame();
  const palette = colors[accent];
  return (
    <AbsoluteFill
      style={{
        background:
          'radial-gradient(circle at 12% 18%, #17213A 0, #0A1020 34%, #050812 72%)',
        overflow: 'hidden',
      }}
    >
      <div
        style={{
          position: 'absolute',
          inset: 0,
          opacity: 0.16,
          backgroundImage:
            'linear-gradient(rgba(255,255,255,.08) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.08) 1px, transparent 1px)',
          backgroundSize: '72px 72px',
          transform: `translate(${(frame * 0.14) % 72}px, ${(frame * 0.08) % 72}px)`,
        }}
      />
      <div
        style={{
          position: 'absolute',
          width: 720,
          height: 720,
          borderRadius: '50%',
          right: -190 + Math.sin(frame / 55) * 24,
          top: -240 + Math.cos(frame / 65) * 18,
          background: palette.glow,
          filter: 'blur(90px)',
        }}
      />
      <div
        style={{
          position: 'absolute',
          width: 420,
          height: 420,
          borderRadius: '50%',
          left: -170 + Math.cos(frame / 48) * 18,
          bottom: -200,
          background: 'rgba(66,89,255,.18)',
          filter: 'blur(80px)',
        }}
      />
    </AbsoluteFill>
  );
};

const Header: React.FC<{
  scene: VideoScene;
  editionDate: string;
  sceneIndex: number;
  sceneCount: number;
}> = ({scene, editionDate, sceneIndex, sceneCount}) => {
  const palette = colors[scene.accent];
  return (
    <div
      style={{
        position: 'absolute',
        top: 54,
        left: 72,
        right: 72,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        fontFamily,
        color: '#DCE6FA',
        fontSize: 22,
        letterSpacing: 1.2,
      }}
    >
      <div style={{display: 'flex', gap: 18, alignItems: 'center'}}>
        <div style={{fontWeight: 900, color: palette.primary}}>AI WEEKLY</div>
        <div style={{opacity: 0.52}}>{editionDate}</div>
      </div>
      <div style={{display: 'flex', gap: 14, alignItems: 'center'}}>
        {scene.topicIndex ? (
          <span
            style={{
              padding: '7px 13px',
              borderRadius: 999,
              background: palette.soft,
              color: palette.primary,
              fontWeight: 800,
            }}
          >
            TOPIC {scene.topicIndex}
          </span>
        ) : null}
        <span style={{fontVariantNumeric: 'tabular-nums', opacity: 0.62}}>
          {String(sceneIndex + 1).padStart(2, '0')} / {String(sceneCount).padStart(2, '0')}
        </span>
      </div>
    </div>
  );
};

const FlowVisual: React.FC<{labels: string[]; accent: Accent}> = ({labels, accent}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const palette = colors[accent];
  const nodes = labels.length > 1 ? labels : ['Input', 'Mechanism', 'Outcome'];
  return (
    <div style={{display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 16}}>
      {nodes.slice(0, 5).map((label, index) => {
        const progress = spring({frame: frame - 18 - index * 9, fps, config: {damping: 16}});
        return (
          <React.Fragment key={label}>
            {index > 0 ? (
              <div
                style={{
                  width: 46,
                  height: 2,
                  background: `linear-gradient(90deg, ${palette.primary}, transparent)`,
                  opacity: progress,
                  transform: `scaleX(${progress})`,
                  transformOrigin: 'left',
                }}
              />
            ) : null}
            <div
              style={{
                width: 188,
                minHeight: 126,
                padding: '22px 18px',
                borderRadius: 22,
                border: `1px solid ${palette.primary}66`,
                background: 'rgba(10,17,32,.78)',
                boxShadow: `0 24px 70px ${palette.glow}`,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                textAlign: 'center',
                color: '#F3F7FF',
                fontSize: 24,
                fontWeight: 760,
                lineHeight: 1.35,
                opacity: progress,
                transform: `translateY(${(1 - progress) * 34}px) scale(${0.94 + progress * 0.06})`,
              }}
            >
              {label}
            </div>
          </React.Fragment>
        );
      })}
    </div>
  );
};

const FunnelVisual: React.FC<{candidateCount: number; approvedCount: number}> = ({
  candidateCount,
  approvedCount,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const stages = [
    {label: 'Candidates', value: candidateCount, width: 620},
    {label: 'Re-verified', value: 'primary sources', width: 480},
    {label: 'Hard gates', value: 'evidence + value', width: 350},
    {label: 'Selected', value: approvedCount, width: 220},
  ];
  return (
    <div style={{display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12}}>
      {stages.map((stage, index) => {
        const progress = spring({frame: frame - 14 - index * 8, fps, config: {damping: 18}});
        return (
          <div
            key={stage.label}
            style={{
              width: stage.width,
              height: 86,
              borderRadius: 20,
              background:
                index === stages.length - 1
                  ? 'linear-gradient(100deg,#15C6D8,#7C5CFC)'
                  : 'linear-gradient(100deg,rgba(40,58,91,.92),rgba(21,31,54,.92))',
              border: '1px solid rgba(255,255,255,.12)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '0 30px',
              color: '#F6FAFF',
              opacity: progress,
              transform: `scaleX(${0.72 + progress * 0.28})`,
            }}
          >
            <span style={{fontSize: 22, opacity: 0.76}}>{stage.label}</span>
            <span style={{fontSize: 30, fontWeight: 900}}>{stage.value}</span>
          </div>
        );
      })}
    </div>
  );
};

const DemoVisual: React.FC<{points: string[]; accent: Accent}> = ({points, accent}) => {
  const frame = useCurrentFrame();
  const palette = colors[accent];
  return (
    <div
      style={{
        width: 760,
        borderRadius: 24,
        overflow: 'hidden',
        border: '1px solid rgba(255,255,255,.13)',
        background: 'rgba(5,9,18,.88)',
        boxShadow: '0 30px 90px rgba(0,0,0,.38)',
      }}
    >
      <div
        style={{
          height: 54,
          background: '#121A2A',
          display: 'flex',
          alignItems: 'center',
          gap: 9,
          padding: '0 20px',
        }}
      >
        {['#FF6B6B', '#FFD166', '#42D392'].map((color) => (
          <div key={color} style={{width: 13, height: 13, borderRadius: '50%', background: color}} />
        ))}
        <span style={{marginLeft: 14, color: '#748099', fontSize: 16}}>weekly-ai / experiment</span>
      </div>
      <div style={{padding: '30px 34px', display: 'flex', flexDirection: 'column', gap: 20}}>
        {points.map((point, index) => {
          const reveal = interpolate(frame, [18 + index * 18, 30 + index * 18], [0, 1], {
            extrapolateLeft: 'clamp',
            extrapolateRight: 'clamp',
            easing: Easing.out(Easing.cubic),
          });
          return (
            <div
              key={point}
              style={{display: 'flex', gap: 18, alignItems: 'flex-start', opacity: reveal}}
            >
              <span style={{color: palette.primary, fontWeight: 900, fontSize: 22}}>
                {String(index + 1).padStart(2, '0')}
              </span>
              <span style={{color: '#E7EDFA', fontSize: 24, lineHeight: 1.45}}>{point}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
};

const EvidenceVisual: React.FC<{points: string[]; accent: Accent}> = ({points, accent}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const palette = colors[accent];
  return (
    <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 18, width: 760}}>
      {points.slice(0, 4).map((point, index) => {
        const progress = spring({frame: frame - 15 - index * 10, fps, config: {damping: 17}});
        return (
          <div
            key={point}
            style={{
              minHeight: 158,
              padding: '25px 25px 22px',
              borderRadius: 22,
              border: `1px solid ${index === 0 ? palette.primary + '77' : 'rgba(255,255,255,.12)'}`,
              background: index === 0 ? palette.soft : 'rgba(14,21,38,.8)',
              color: '#F2F6FF',
              fontSize: 23,
              lineHeight: 1.45,
              opacity: progress,
              transform: `translateY(${(1 - progress) * 30}px)`,
            }}
          >
            <div style={{fontSize: 14, color: palette.primary, fontWeight: 900, marginBottom: 12}}>
              {index === 0 ? 'EVIDENCE' : `BOUNDARY ${index}`}
            </div>
            {point}
          </div>
        );
      })}
    </div>
  );
};

const IntroVisual: React.FC<{points: string[]; accent: Accent}> = ({points, accent}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const palette = colors[accent];
  return (
    <div style={{display: 'flex', gap: 18}}>
      {points.slice(0, 4).map((point, index) => {
        const progress = spring({frame: frame - 28 - index * 8, fps, config: {damping: 16}});
        return (
          <div
            key={point}
            style={{
              minWidth: 190,
              padding: '18px 24px',
              borderRadius: 18,
              color: index === 0 ? '#061016' : '#EAF3FF',
              background: index === 0 ? palette.primary : 'rgba(255,255,255,.08)',
              border: '1px solid rgba(255,255,255,.12)',
              fontSize: 21,
              fontWeight: 800,
              textAlign: 'center',
              opacity: progress,
              transform: `translateY(${(1 - progress) * 24}px)`,
            }}
          >
            {point}
          </div>
        );
      })}
    </div>
  );
};

const SceneVisual: React.FC<{
  scene: VideoScene;
  candidateCount: number;
  approvedCount: number;
}> = ({scene, candidateCount, approvedCount}) => {
  if (scene.kind === 'evaluation_funnel') {
    return <FunnelVisual candidateCount={candidateCount} approvedCount={approvedCount} />;
  }
  if (scene.kind === 'mechanism' || scene.kind === 'problem') {
    return <FlowVisual labels={scene.visual_labels} accent={scene.accent} />;
  }
  if (scene.kind === 'demo') {
    return <DemoVisual points={scene.on_screen_points} accent={scene.accent} />;
  }
  if (scene.kind === 'evidence_and_limits') {
    return <EvidenceVisual points={scene.on_screen_points} accent={scene.accent} />;
  }
  return <IntroVisual points={scene.on_screen_points} accent={scene.accent} />;
};

const Caption: React.FC<{scene: VideoScene}> = ({scene}) => {
  const frame = useCurrentFrame();
  const chunks = scene.captionChunks;
  const usableFrames = Math.max(scene.durationInFrames - 18, 1);
  const index = Math.min(chunks.length - 1, Math.floor((frame / usableFrames) * chunks.length));
  const local = (frame / usableFrames) * chunks.length - index;
  const opacity = interpolate(local, [0, 0.08, 0.9, 1], [0.4, 1, 1, 0.4], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  return (
    <div
      style={{
        position: 'absolute',
        left: 260,
        right: 260,
        bottom: 76,
        minHeight: 70,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '14px 28px',
        borderRadius: 18,
        background: 'rgba(2,6,14,.78)',
        border: '1px solid rgba(255,255,255,.12)',
        color: '#F7FAFF',
        fontFamily,
        fontSize: 27,
        fontWeight: 650,
        textAlign: 'center',
        lineHeight: 1.45,
        opacity,
      }}
    >
      {chunks[index]}
    </div>
  );
};

const SceneCard: React.FC<{
  scene: VideoScene;
  editionDate: string;
  sceneIndex: number;
  sceneCount: number;
  candidateCount: number;
  approvedCount: number;
}> = ({scene, editionDate, sceneIndex, sceneCount, candidateCount, approvedCount}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const palette = colors[scene.accent];
  const outro = interpolate(frame, [scene.durationInFrames - 15, scene.durationInFrames], [1, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  return (
    <AbsoluteFill style={{fontFamily, opacity: outro}}>
      <SceneBackground accent={scene.accent} />
      <Header scene={scene} editionDate={editionDate} sceneIndex={sceneIndex} sceneCount={sceneCount} />
      <div
        style={{
          position: 'absolute',
          left: 96,
          right: 96,
          top: 150,
          bottom: 185,
          display: 'grid',
          gridTemplateColumns: 'minmax(0, 0.92fr) minmax(620px, 1.08fr)',
          gap: 58,
          alignItems: 'center',
        }}
      >
        <div style={{display: 'flex', flexDirection: 'column', alignItems: 'flex-start'}}>
          <div
            style={{
              ...enterStyle(frame, fps, 4),
              color: palette.primary,
              fontSize: 19,
              fontWeight: 900,
              letterSpacing: 2.1,
              textTransform: 'uppercase',
              marginBottom: 20,
            }}
          >
            {scene.eyebrow}
          </div>
          <h1
            style={{
              ...enterStyle(frame, fps, 9),
              margin: 0,
              color: '#F5F8FF',
              fontSize:
                scene.kind === 'intro'
                  ? scene.title.length > 12
                    ? 56
                    : 76
                  : scene.title.length > 20
                    ? 42
                    : scene.title.length > 12
                      ? 46
                      : 61,
              lineHeight: 1.08,
              letterSpacing: -2.4,
              fontWeight: 920,
              maxWidth: 760,
            }}
          >
            {scene.title}
          </h1>
          <p
            style={{
              ...enterStyle(frame, fps, 16),
              margin: '28px 0 0',
              color: '#AEBBD2',
              fontSize: 27,
              lineHeight: 1.52,
              maxWidth: 720,
            }}
          >
            {scene.subtitle}
          </p>
        </div>
        <div style={{...enterStyle(frame, fps, 20), display: 'flex', justifyContent: 'center'}}>
          <SceneVisual scene={scene} candidateCount={candidateCount} approvedCount={approvedCount} />
        </div>
      </div>
      <Caption scene={scene} />
      <Audio src={staticFile(scene.audioSrc)} />
    </AbsoluteFill>
  );
};

const GlobalOverlay: React.FC<Pick<WeeklyVideoProps, 'totalDurationInFrames' | 'disclosure'>> = ({
  totalDurationInFrames,
  disclosure,
}) => {
  const frame = useCurrentFrame();
  const progress = interpolate(frame, [0, totalDurationInFrames - 1], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  return (
    <>
      <div
        style={{
          position: 'absolute',
          left: 0,
          bottom: 0,
          height: 5,
          width: `${progress * 100}%`,
          background: 'linear-gradient(90deg,#39E6F4,#A78BFA,#F9C74F)',
        }}
      />
      <div
        style={{
          position: 'absolute',
          right: 76,
          bottom: 24,
          color: '#71809A',
          fontFamily,
          fontSize: 14,
          letterSpacing: 0.5,
        }}
      >
        {disclosure}
      </div>
    </>
  );
};

export const WeeklyAI: React.FC<WeeklyVideoProps> = (props) => (
  <AbsoluteFill style={{backgroundColor: '#050812'}}>
    {props.scenes.map((scene, index) => (
      <Sequence
        key={scene.scene_id}
        from={scene.startFrame}
        durationInFrames={scene.durationInFrames}
        premountFor={props.fps}
      >
        <SceneCard
          scene={scene}
          editionDate={props.editionDate}
          sceneIndex={index}
          sceneCount={props.scenes.length}
          candidateCount={props.candidateCount}
          approvedCount={props.approvedCount}
        />
      </Sequence>
    ))}
    <GlobalOverlay
      totalDurationInFrames={props.totalDurationInFrames}
      disclosure={props.disclosure}
    />
  </AbsoluteFill>
);
