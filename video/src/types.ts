export type SceneKind =
  | 'intro'
  | 'evaluation_funnel'
  | 'problem'
  | 'mechanism'
  | 'demo'
  | 'evidence_and_limits'
  | 'decision_guide';

export type Accent = 'cyan' | 'violet' | 'amber';

export type VideoScene = {
  scene_id: string;
  topic_id: string | null;
  topicIndex: number | null;
  kind: SceneKind;
  accent: Accent;
  eyebrow: string;
  title: string;
  subtitle: string;
  narration: string;
  on_screen_points: string[];
  visual_labels: string[];
  audioSrc: string;
  audioDurationSeconds: number;
  startFrame: number;
  durationInFrames: number;
  captionChunks: string[];
};

export type WeeklyVideoProps = {
  editionDate: string;
  windowStart: string;
  windowEnd: string;
  title: string;
  subtitle: string;
  disclosure: string;
  candidateCount: number;
  approvedCount: number;
  fps: number;
  width: number;
  height: number;
  totalDurationInFrames: number;
  scenes: VideoScene[];
};
