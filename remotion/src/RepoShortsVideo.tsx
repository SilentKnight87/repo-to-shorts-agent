import React from 'react';
import {
  AbsoluteFill,
  Easing,
  Sequence,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import {
  baseFill,
  colors,
  hairline,
  monoLabel,
  safeArea,
  shadows,
  spacing,
  type,
} from './styles';
import {KNOWN_LAYOUTS, inferSceneLayout, inferSceneType, KNOWN_SCENE_TYPES, type SceneLayout} from './sceneTypes';

type SceneTypeName =
  | 'ColdOpen'
  | 'RepoEvidence'
  | 'PainPoint'
  | 'PipelineMap'
  | 'ArtifactStack'
  | 'LiveProof'
  | 'DemoPreview'
  | 'CTAEndCard';

export type RepoShortsScene = {
  type?: SceneTypeName | string;
  duration_seconds?: number;
  headline?: string;
  narration?: string;
  evidence?: string[];
  caption_emphasis?: string[];
  layout?: string;
  visual_role?: string;
  shot?: string;
  shot_hint?: string;
  visual_tool?: string;
  transition?: string;
  motion_focus?: string;
};

export type RepoShortsManifest = {
  creative_direction?: {
    visual_world?: string;
    tone?: string;
    visual_style?: string;
    quality_bar?: Record<string, unknown>;
    motion_principles?: string[];
    shot_list?: string[];
    continuity_rules?: string[];
    negative_prompts?: string[];
  };
  repo?: {
    name?: string;
    description?: string;
    key_files?: string[];
  };
  video?: {
    width?: number;
    height?: number;
    fps?: number;
    duration_seconds?: number;
  };
  proof?: Record<string, unknown>;
  scenes?: RepoShortsScene[];
  artifacts?: string[];
};

type NormalizedManifest = {
  repo: {
    name: string;
    description: string;
    key_files: string[];
  };
  video: {
    width: number;
    height: number;
    fps: number;
    duration_seconds: number;
  };
  proof: Record<string, unknown>;
  scenes: NormalizedScene[];
  artifacts: string[];
  creative_direction: {
    visual_world: string;
    tone: string;
    visual_style: string;
    quality_bar: Record<string, unknown>;
    motion_principles: string[];
    shot_list: string[];
    continuity_rules: string[];
    negative_prompts: string[];
  };
};

type SceneType = SceneTypeName | 'Unknown';
type NormalizedScene = {
  type: SceneType;
  duration_seconds: number;
  headline: string;
  narration: string;
  evidence: string[];
  caption_emphasis: string[];
  layout: string;
  visual_role: string;
  shot: string;
  shot_hint: string;
  visual_tool: string;
  transition: string;
  motion_focus: string;
};

const DEFAULT_SCENES: NormalizedScene[] = [
  {
    type: 'ColdOpen',
    layout: 'cover_burst',
    visual_role: 'cover',
    shot: '',
    shot_hint: '',
    visual_tool: 'pretext',
    transition: 'cut',
    motion_focus: '',
    duration_seconds: 3,
    headline: "This repo made the video you're watching.",
    narration: "This repo made the video you're watching.",
    evidence: ['repo-to-shorts-agent'],
    caption_emphasis: ['repo', 'video'],
  },
  {
    type: 'RepoEvidence',
    layout: 'repo_card',
    visual_role: 'evidence',
    shot: '',
    shot_hint: '',
    visual_tool: 'svg',
    transition: 'cut',
    motion_focus: '',
    duration_seconds: 6,
    headline: 'Source code becomes a launch package.',
    narration: 'Repo-to-Shorts inspects the local project and turns it into a short-video package.',
    evidence: ['src/repo_to_shorts/pipeline.py', 'src/repo_to_shorts/kimi.py'],
    caption_emphasis: ['source', 'launch package'],
  },
  {
    type: 'PipelineMap',
    layout: 'pipeline_flow',
    visual_role: 'flow',
    shot: '',
    shot_hint: '',
    visual_tool: 'svg',
    transition: 'cut',
    motion_focus: '',
    duration_seconds: 7,
    headline: 'Ingest. Critique. Render. Submit.',
    narration: 'The pipeline builds the brief, storyboard, captions, copy, browser demo, and optional MP4.',
    evidence: ['repo brief', 'storyboard', 'captions.srt', 'demo.mp4'],
    caption_emphasis: ['brief', 'captions', 'MP4'],
  },
  {
    type: 'LiveProof',
    layout: 'proof_sheet',
    visual_role: 'proof',
    shot: '',
    shot_hint: '',
    visual_tool: 'manim',
    transition: 'cut',
    motion_focus: '',
    duration_seconds: 6,
    headline: 'Kimi proof is visible in metadata.',
    narration: 'The generated run records live model mode, provider, and model without faking proof.',
    evidence: ['metadata.json'],
    caption_emphasis: ['live-api', 'metadata'],
  },
  {
    type: 'CTAEndCard',
    layout: 'cta_band',
    visual_role: 'cta',
    shot: '',
    shot_hint: '',
    visual_tool: 'pretext',
    transition: 'cut',
    motion_focus: '',
    duration_seconds: 5,
    headline: 'Run it locally. Record the package. Ship the short.',
    narration: 'One command creates the assets for X and Discord submission.',
    evidence: ['repo-shorts analyze . --render mp4'],
    caption_emphasis: ['Run', 'Ship'],
  },
];

export const DEFAULT_MANIFEST: NormalizedManifest = {
  repo: {
    name: 'repo-to-shorts-agent',
    description: 'Turns a repo into a launch-ready technical demo video package.',
    key_files: ['README.md', 'src/repo_to_shorts/pipeline.py', 'src/repo_to_shorts/kimi.py'],
  },
  video: {
    width: 1080,
    height: 1920,
    fps: 30,
    duration_seconds: 45,
  },
  proof: {
    kimi_mode: 'deterministic-fallback',
    kimi_provider: 'local',
    kimi_model: 'fallback',
  },
  creative_direction: {
    visual_world: 'Retro VHS broadcast deck',
    tone: '',
    visual_style: '',
    quality_bar: {},
    motion_principles: [],
    shot_list: [],
    continuity_rules: [],
    negative_prompts: [],
  },
  scenes: DEFAULT_SCENES,
  artifacts: ['demo.mp4', 'metadata.json', 'captions.srt', 'submission_pack.md'],
};

const KNOWN_SCENE_TYPES_SET = new Set<string>(KNOWN_SCENE_TYPES);
const LAYOUT_EFFECT: Record<
  SceneLayout | 'default',
  {background: string; sideBand: number; accent: string; bar: string}
> = {
  cover_burst: {
    background: `linear-gradient(160deg, ${colors.carbon} 0%, #0c1736 45%, #0f1019 100%)`,
    sideBand: 0,
    accent: colors.cyan,
    bar: colors.green,
  },
  repo_card: {
    background: `linear-gradient(160deg, #0f1824 0%, #111a24 52%, ${colors.ink} 100%)`,
    sideBand: 52,
    accent: colors.amber,
    bar: colors.green,
  },
  problem_block: {
    background: `linear-gradient(160deg, #221111 0%, #1a0f12 54%, ${colors.ink} 100%)`,
    sideBand: 52,
    accent: colors.red,
    bar: colors.ghostMagenta,
  },
  pipeline_flow: {
    background: `linear-gradient(160deg, #0f1927 0%, #121620 52%, ${colors.ink} 100%)`,
    sideBand: 52,
    accent: colors.green,
    bar: colors.cyan,
  },
  artifact_wall: {
    background: `linear-gradient(160deg, ${colors.ink} 0%, ${colors.carbon} 64%, ${colors.panelSoft} 100%)`,
    sideBand: 52,
    accent: colors.amber,
    bar: colors.paperDim,
  },
  proof_sheet: {
    background: `linear-gradient(160deg, #13140e 0%, #1a2715 58%, ${colors.ink} 100%)`,
    sideBand: 52,
    accent: colors.ghost,
    bar: colors.green,
  },
  preview_frame: {
    background: `linear-gradient(160deg, #0f1014 0%, #101623 58%, #0c1b2f 100%)`,
    sideBand: 52,
    accent: colors.cyan,
    bar: colors.ghostCyan,
  },
  cta_band: {
    background: `linear-gradient(160deg, #111111 0%, #1a1a1a 60%, #2a1d2d 100%)`,
    sideBand: 0,
    accent: colors.ghostMagenta,
    bar: colors.green,
  },
  default: {
    background: `linear-gradient(160deg, ${colors.carbon} 0%, #111820 52%, #0b0d15 100%)`,
    sideBand: 52,
    accent: colors.green,
    bar: colors.paperDim,
  },
};

export const normalizeManifest = (input: RepoShortsManifest = {}): NormalizedManifest => {
  const video = input.video ?? {};
  const repo = input.repo ?? {};
  const creative = input.creative_direction ?? {};
  const scenes = input.scenes && input.scenes.length > 0 ? input.scenes : DEFAULT_SCENES;
  const normalizedScenes = scenes.map((scene, index) => ({
    type: inferSceneType(scene.type || DEFAULT_SCENES[index % DEFAULT_SCENES.length].type),
    layout: String(
      scene.layout
        || inferSceneLayout(
          inferSceneType(scene.type || DEFAULT_SCENES[index % DEFAULT_SCENES.length].type),
          index,
        ),
    ),
    visual_role: String(scene.visual_role || ''),
    shot: String(scene.shot || ''),
    shot_hint: String(scene.shot_hint || ''),
    visual_tool: String(scene.visual_tool || ''),
    transition: String(scene.transition || 'cut'),
    motion_focus: String(scene.motion_focus || ''),
    duration_seconds: Math.max(0.5, Number(scene.duration_seconds || 6)),
    headline: String(scene.headline || scene.narration || 'Repo to Shorts'),
    narration: String(scene.narration || scene.headline || ''),
    evidence: normalizeStringList(scene.evidence, 5),
    caption_emphasis: normalizeStringList(scene.caption_emphasis, 6),
  }));
  const summedDuration = normalizedScenes.reduce(
    (total, scene) => total + scene.duration_seconds,
    0,
  );

  return {
    repo: {
      name: String(repo.name || DEFAULT_MANIFEST.repo.name),
      description: String(repo.description || DEFAULT_MANIFEST.repo.description),
      key_files: normalizeStringList(repo.key_files, 8),
    },
    video: {
      width: positiveInteger(video.width, 1080),
      height: positiveInteger(video.height, 1920),
      fps: positiveInteger(video.fps, 30),
      duration_seconds: Math.max(
        1,
        Number(video.duration_seconds || summedDuration || DEFAULT_MANIFEST.video.duration_seconds),
      ),
    },
    proof: input.proof && typeof input.proof === 'object' ? input.proof : {},
    scenes: normalizedScenes,
    artifacts: normalizeStringList(input.artifacts, 12),
    creative_direction: {
      visual_world: String(creative.visual_world || 'Retro VHS broadcast deck'),
      tone: String(creative.tone || ''),
      visual_style: String(creative.visual_style || ''),
      quality_bar: creative.quality_bar && typeof creative.quality_bar === 'object' ? creative.quality_bar : {},
      motion_principles: normalizeStringList(creative.motion_principles, 8),
      shot_list: normalizeStringList(creative.shot_list, 12),
      continuity_rules: normalizeStringList(creative.continuity_rules, 8),
      negative_prompts: normalizeStringList(creative.negative_prompts, 8),
    },
  };
};

export const getDurationInFrames = (manifest: RepoShortsManifest): number => {
  const normalized = normalizeManifest(manifest);
  const sceneFrames = normalized.scenes.reduce(
    (total, scene) => total + getSceneDurationInFrames(scene, normalized.video.fps),
    0,
  );
  return (
    sceneFrames ||
    Math.max(1, Math.round(normalized.video.duration_seconds * normalized.video.fps))
  );
};

export const getSceneDurationInFrames = (
  scene: Pick<NormalizedScene, 'duration_seconds'>,
  fps: number,
): number => {
  return Math.max(1, Math.round(scene.duration_seconds * fps));
};

export const RepoShortsVideo: React.FC<RepoShortsManifest> = (props) => {
  const manifest = normalizeManifest(props);
  const {fps} = useVideoConfig();
  let from = 0;

  return (
    <AbsoluteFill style={baseFill}>
      {manifest.scenes.map((scene, index) => {
        const duration = getSceneDurationInFrames(scene, fps);
        const sequence = (
          <Sequence from={from} durationInFrames={duration} key={`${scene.type}-${index}`}>
            <SceneFrame
              manifest={manifest}
              scene={scene}
              sceneIndex={index}
              sceneCount={manifest.scenes.length}
              durationInFrames={duration}
            />
          </Sequence>
        );
        from += duration;
        return sequence;
      })}
      <FilmGrain />
      <CRTScanlines />
      <CRTVignette />
      <BroadcastFrame manifest={manifest} />
    </AbsoluteFill>
  );
};

const SceneFrame: React.FC<{
  manifest: NormalizedManifest;
  scene: NormalizedScene;
  sceneIndex: number;
  sceneCount: number;
  durationInFrames: number;
}> = ({manifest, scene, sceneIndex, sceneCount, durationInFrames}) => {
  const isKnownSceneType = KNOWN_SCENE_TYPES_SET.has(String(scene.type));
  const typeName = scene.type;
  const frame = useCurrentFrame();
  const sceneProgress = Math.min(1, Math.max(0, frame / Math.max(1, durationInFrames - 1)));
  const entrance = spring({frame, fps: 30, config: {damping: 18, stiffness: 130}});
  const exit = interpolate(
    frame,
    [durationInFrames - 18, durationInFrames],
    [1, 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.in(Easing.cubic)},
  );
  const opacity = Math.min(entrance, exit);
  const y = interpolate(entrance, [0, 1], [34, 0]);
  const stageOffsetX = interpolate(sceneProgress, [0, 1], [sceneIndex % 2 === 0 ? -26 : 26, 0], {
    extrapolateRight: 'clamp',
    easing: Easing.out(Easing.quad),
  });

  return (
    <AbsoluteFill style={{opacity}}>
      <Backplate manifest={manifest} scene={scene} frame={frame} sceneProgress={sceneProgress} />
        <div
          style={{
            ...safeArea,
            transform: `translate(${stageOffsetX}px, ${y}px)`,
          }}
        >
        <SceneChrome
          scene={scene}
          manifest={manifest}
          sceneIndex={sceneIndex}
          sceneCount={sceneCount}
        />
        {typeName === 'ColdOpen' && <ColdOpen manifest={manifest} scene={scene} />}
        {typeName === 'RepoEvidence' && <RepoEvidence manifest={manifest} scene={scene} />}
        {typeName === 'PainPoint' && <PainPoint manifest={manifest} scene={scene} />}
        {typeName === 'PipelineMap' && <PipelineMap scene={scene} />}
        {typeName === 'ArtifactStack' && <ArtifactStack manifest={manifest} scene={scene} />}
        {typeName === 'LiveProof' && <LiveProof manifest={manifest} scene={scene} />}
        {typeName === 'DemoPreview' && <DemoPreview manifest={manifest} scene={scene} />}
        {typeName === 'CTAEndCard' && <CTAEndCard manifest={manifest} scene={scene} />}
        {!isKnownSceneType && <UnknownScene manifest={manifest} scene={scene} />}
        <CaptionLine scene={scene} manifest={manifest} frame={frame} sceneProgress={sceneProgress} />
      </div>
    </AbsoluteFill>
  );
};

const SceneChrome: React.FC<{
  scene: NormalizedScene;
  manifest: NormalizedManifest;
  sceneIndex: number;
  sceneCount: number;
}> = ({scene, manifest, sceneIndex, sceneCount}) => {
  const frame = useCurrentFrame();
  const pulse = interpolate(Math.sin(frame / 9), [-1, 1], [0.28, 1]);

  return (
    <>
      <div style={{display: 'flex', alignItems: 'center', justifyContent: 'space-between'}}>
        <div style={{...monoLabel, color: colors.green}}>Repo-to-Shorts</div>
        <div
          style={{
            fontFamily: type.mono,
            fontSize: 24,
            color: colors.paperDim,
            textTransform: 'uppercase',
          }}
        >
          {String(scene.type).replace(/([a-z])([A-Z])/g, '$1/$2')} {sceneIndex + 1}/
          {sceneCount}
        </div>
      </div>
      <div style={{...hairline, marginTop: 20, marginBottom: 34}} />
      <div
        style={{
          position: 'absolute',
          right: 0,
          top: 112,
          width: 16,
          height: 860,
          border: `1px solid ${colors.line}`,
          background: `linear-gradient(180deg, ${colors.cyan}22, transparent 48%, ${colors.amber}22)`,
        }}
      >
        <div
          style={{
            height: `${((sceneIndex + 1) / sceneCount) * 100}%`,
            background: `linear-gradient(180deg, ${colors.cyan}, ${colors.green}, ${colors.amber})`,
            boxShadow: shadows.glowCyan,
            opacity: pulse,
          }}
        />
      </div>
      <div
        style={{
          position: 'absolute',
          left: 0,
          bottom: 0,
          fontFamily: type.mono,
          fontSize: 22,
          color: colors.paperDim,
          textTransform: 'uppercase',
        }}
      >
        {manifest.repo.name}
      </div>
    </>
  );
};

const ColdOpen: React.FC<SceneProps> = ({manifest, scene}) => {
  const frame = useCurrentFrame();
  const reveal = spring({frame, fps: 30, config: {damping: 16, stiffness: 120}});
  const scan = interpolate(frame, [0, 90], [-220, 660], {extrapolateRight: 'extend'});
  const pulse = interpolate(frame, [0, 18, 30], [0.94, 1, 0.94], {
    easing: Easing.inOut(Easing.sin),
    extrapolateRight: 'clamp',
  });
  const headlineWords = splitHeadline(scene.headline, 3);
  const accent = interpolate(frame, [0, 24, 40], [0, 1, 0.66], {
    easing: Easing.out(Easing.quad),
    extrapolateRight: 'clamp',
  });

  return (
    <main style={{position: 'absolute', inset: '156px 36px 140px 0'}}>
      <div
        style={{
          fontFamily: type.display,
          fontSize: 142,
          lineHeight: 0.88,
          textTransform: 'uppercase',
          maxWidth: 850,
          textShadow: `8px 8px 0 ${colors.ink}, ${shadows.glowCyan}`,
          transform: `scale(${0.92 + reveal * 0.08})`,
        }}
      >
        {headlineWords.map((part, index) => (
          <div
            key={part}
            style={{
              color: index % 2 === 0 ? colors.paper : colors.cyan,
              transform: `translateX(${(index % 2 === 0 ? -1 : 1) * (1 - accent) * 20}px)`,
              opacity: 0.6 + accent * 0.4,
            }}
          >
            {part}
          </div>
        ))}
      </div>
      <div
        style={{
          position: 'absolute',
          left: 0,
          right: 0,
          top: 460,
          fontFamily: type.mono,
          fontSize: 30,
          color: colors.paperDim,
          letterSpacing: 1.1,
          opacity: accent,
        }}
      >
        {manifest.repo.description}
      </div>
      <div
        style={{
          marginTop: 84,
          display: 'inline-flex',
          border: `1px solid ${colors.cyan}`,
          boxShadow: shadows.glowCyan,
          padding: '20px 26px',
          fontFamily: type.mono,
          fontSize: 34,
          color: colors.green,
          background: colors.panel,
          transform: `scale(${0.98 + pulse * 0.03})`,
        }}
      >
        {manifest.repo.name}
      </div>
      <div
        style={{
          position: 'absolute',
          left: 0,
          right: 90,
          top: scan,
          height: 4,
          background: colors.green,
          boxShadow: `0 0 42px ${colors.green}`,
        }}
      />
    </main>
  );
};

type SceneProps = {
  manifest: NormalizedManifest;
  scene: NormalizedScene;
};

const RepoEvidence: React.FC<SceneProps> = ({manifest, scene}) => (
  <TwoColumnStage
    headline={scene.headline}
    kicker="source inspection"
    left={<EvidenceList items={[manifest.repo.description, ...manifest.repo.key_files]} />}
    right={<TerminalPanel lines={scene.evidence.length ? scene.evidence : manifest.repo.key_files} />}
  />
);

const PainPoint: React.FC<SceneProps> = ({scene}) => {
  const pain = scene.evidence.length
    ? scene.evidence
    : ['read the repo', 'write the pitch', 'draw the architecture', 'cut captions', 'package proof'];
  return (
    <TwoColumnStage
      headline={scene.headline}
      kicker="builder friction"
      left={<NumberWall items={pain} />}
      right={<DiagonalStamp text="turn demo work into one run" />}
    />
  );
};

const PipelineMap: React.FC<{scene: NormalizedScene}> = ({scene}) => {
  const frame = useCurrentFrame();
  const progress = Math.min(1, frame / 120);
  const steps = ['ingest', 'Kimi critic', 'storyboard', 'render', 'submission'];
  return (
    <FullStage headline={scene.headline} kicker="pipeline">
      <div
        style={{
          position: 'relative',
          height: 920,
          border: `1px solid ${colors.line}`,
          padding: 24,
          background: `linear-gradient(180deg, ${colors.panel} 0%, transparent 70%)`,
          boxShadow: shadows.panel,
        }}
      >
        <div
          style={{
            position: 'absolute',
            left: 132,
            top: 24,
            width: 4,
            height: 'calc(100% - 48px)',
            background: `linear-gradient(180deg, transparent, ${colors.green}, transparent)`,
            transform: `scaleY(${progress})`,
            transformOrigin: 'top',
          }}
        />
        {steps.map((step, index) => (
          <div
            key={step}
            style={{
              display: 'grid',
              gridTemplateColumns: '132px 1fr',
              alignItems: 'center',
              minHeight: 138,
              transform: `translateX(${interpolate(
                Math.min(1, Math.max(0, progress * steps.length - index)),
                [0, 1],
                [40, 0],
              )}px)`,
              opacity: interpolate(
                Math.min(1, Math.max(0, progress * steps.length - index)),
                [0, 0.25, 1],
                [0.15, 1, 1],
                {extrapolateRight: 'clamp'},
              ),
            }}
          >
            <div style={{fontFamily: type.mono, fontSize: 34, color: colors.amber}}>
              0{index + 1}
            </div>
            <div
              style={{
                borderLeft: `8px solid ${
                  index <= Math.floor(progress * steps.length) ? colors.green : colors.cyan
                }`,
                paddingLeft: 32,
                fontFamily: type.display,
                fontSize: 72,
                lineHeight: 1,
                textTransform: 'uppercase',
                color: index <= Math.floor(progress * steps.length) ? colors.paper : colors.paperDim,
              }}
            >
              {step}
            </div>
          </div>
        ))}
      </div>
    </FullStage>
  );
};

const ArtifactStack: React.FC<SceneProps> = ({manifest, scene}) => (
  <FullStage headline={scene.headline} kicker="generated package">
    <div style={{position: 'relative', height: 900}}>
      {(manifest.artifacts.length ? manifest.artifacts : scene.evidence).map((artifact, index) => (
        <div
          key={artifact}
          style={{
            position: 'absolute',
            left: index % 2 === 0 ? 0 : 86,
            top: index * 92,
            width: 740,
            minHeight: 132,
            border: `1px solid ${colors.line}`,
            background: index % 2 === 0 ? colors.panel : colors.panelSoft,
            boxShadow: shadows.panel,
            padding: '24px 30px',
            transform: `rotate(${index % 2 === 0 ? -1.4 : 1.2}deg)`,
          }}
        >
          <div style={{fontFamily: type.mono, fontSize: 22, color: colors.green}}>
            artifact/{String(index + 1).padStart(2, '0')}
          </div>
          <div style={{fontFamily: type.display, fontSize: 58, textTransform: 'uppercase'}}>
            {artifact}
          </div>
        </div>
      ))}
    </div>
  </FullStage>
);

const LiveProof: React.FC<SceneProps> = ({manifest, scene}) => {
  const proofRows: [string, unknown][] = [
    ['mode', manifest.proof.kimi_mode ?? manifest.proof.mode ?? 'unknown'],
    ['provider', manifest.proof.kimi_provider ?? manifest.proof.provider ?? 'openrouter'],
    ['model', manifest.proof.kimi_model ?? manifest.proof.model ?? 'moonshotai/kimi-k2.6'],
  ];
  return (
    <TwoColumnStage
      headline={scene.headline}
      kicker="metadata proof"
      left={<ProofPanel rows={proofRows} />}
      right={<ProofScroll rows={proofRows} manifest={manifest} />}
    />
  );
};

const DemoPreview: React.FC<SceneProps> = ({manifest, scene}) => (
  <TwoColumnStage
    headline={scene.headline}
    kicker="browser-recordable"
    left={<PhonePreview manifest={manifest} />}
    right={<EvidenceList items={scene.evidence.length ? scene.evidence : manifest.artifacts} />}
  />
);

const CTAEndCard: React.FC<SceneProps> = ({manifest, scene}) => (
  <FullStage headline={scene.headline} kicker="ship package">
    <TypeWriterLine
      lines={[
        '$ repo-shorts analyze . --audience \"Nous Research Hermes Agent Creative Hackathon judges\" --final',
        '$ repo-shorts creative . --audience \"Nous Research Hermes Agent Creative Hackathon judges\" --out runs --final',
      ]}
      y={0}
    />
    <div
      style={{
        marginTop: 36,
        display: 'grid',
        gap: 28,
        gridTemplateColumns: '1fr 1fr',
      }}
    >
      <div
        style={{
          border: `1px solid ${colors.green}`,
          background: '#050805',
          boxShadow: shadows.glowCyan,
          padding: 34,
          fontFamily: type.mono,
          fontSize: 34,
          lineHeight: 1.35,
          color: colors.green,
          minHeight: 220,
        }}
      >
        <span style={{color: colors.paperDim}}>$ </span>
        OPENAI_API_KEY=***
      </div>
      <div
        style={{
          border: `1px solid ${colors.green}`,
          background: '#050805',
          boxShadow: shadows.glowCyan,
          padding: 34,
          fontFamily: type.mono,
          fontSize: 34,
          lineHeight: 1.35,
          color: colors.cyan,
          minHeight: 220,
        }}
      >
        <span style={{color: colors.paperDim}}>$ </span>
        OPENROUTER_API_KEY=***
      </div>
    </div>
    <div
      style={{
        marginTop: 70,
        border: `1px solid ${colors.green}`,
        boxShadow: shadows.glowCyan,
        padding: 34,
        display: 'grid',
        gridTemplateColumns: '1fr 1fr',
        gap: 20,
        color: colors.green,
        fontFamily: type.mono,
        fontSize: 26,
        background: 'rgba(0, 0, 0, 0.5)',
      }}
    >
      <div>
        Output folder:
        <br />
        <span style={{color: colors.paper}}>{manifest.repo.name}/runs</span>
      </div>
      <div style={{textAlign: 'right'}}>
        FPS:
        <br />
        <span style={{color: colors.paper}}>{manifest.video.fps}</span>
      </div>
    </div>
  </FullStage>
);

const UnknownScene: React.FC<SceneProps> = ({manifest, scene}) => (
  <RepoEvidence
    manifest={manifest}
    scene={{
      ...scene,
      headline: scene.headline || `Scene: ${scene.type}`,
    }}
  />
);

const TwoColumnStage: React.FC<{
  headline: string;
  kicker: string;
  left: React.ReactNode;
  right: React.ReactNode;
}> = ({headline, kicker, left, right}) => (
  <main style={{position: 'absolute', inset: '150px 40px 132px 0'}}>
    <Kicker text={kicker} />
    <Headline text={headline} />
    <div style={{display: 'grid', gridTemplateColumns: '0.98fr 1.02fr', gap: 34, marginTop: 52}}>
      {left}
      {right}
    </div>
  </main>
);

const FullStage: React.FC<{headline: string; kicker: string; children: React.ReactNode}> = ({
  headline,
  kicker,
  children,
}) => (
  <main style={{position: 'absolute', inset: '150px 52px 132px 0'}}>
    <Kicker text={kicker} />
    <Headline text={headline} />
    <div style={{marginTop: 58}}>{children}</div>
  </main>
);

const Kicker: React.FC<{text: string}> = ({text}) => (
  <div
    style={{
      display: 'inline-block',
      fontFamily: type.mono,
      color: colors.carbon,
      background: colors.amber,
      padding: '9px 13px',
      fontSize: 24,
      textTransform: 'uppercase',
    }}
  >
    {text}
  </div>
);

const Headline: React.FC<{text: string}> = ({text}) => (
  <h1
    style={{
      margin: '28px 0 0',
      fontFamily: type.display,
      fontSize: 98,
      lineHeight: 0.94,
      textTransform: 'uppercase',
      maxWidth: 860,
      textWrap: 'balance',
    }}
  >
    {text}
  </h1>
);

const EvidenceList: React.FC<{items: string[]}> = ({items}) => (
  <div style={{display: 'grid', gap: 18}}>
    {items.slice(0, 7).map((item, index) => (
      <div
        key={`${item}-${index}`}
        style={{
          borderBottom: `1px solid ${colors.line}`,
          padding: '0 0 17px',
          fontFamily: index === 0 ? type.body : type.mono,
          fontSize: index === 0 ? 34 : 25,
          lineHeight: 1.24,
          color: index === 0 ? colors.paper : colors.paperDim,
        }}
      >
        {item}
      </div>
    ))}
  </div>
);

const TerminalPanel: React.FC<{lines: string[]}> = ({lines}) => (
  <div
    style={{
      border: `1px solid ${colors.green}`,
      background: '#060906',
      boxShadow: shadows.glowCyan,
      padding: 28,
      minHeight: 520,
      fontFamily: type.mono,
      fontSize: 24,
      lineHeight: 1.62,
      color: colors.green,
    }}
  >
    <div style={{color: colors.paperDim, marginBottom: 18}}>repo evidence stream</div>
    {lines.slice(0, 8).map((line, index) => (
      <div key={`${line}-${index}`}>
        <span style={{color: colors.cyan}}>{'>'} </span>
        {line}
      </div>
    ))}
  </div>
);

const NumberWall: React.FC<{items: string[]}> = ({items}) => (
  <div style={{display: 'grid', gap: 20}}>
    {items.slice(0, 6).map((item, index) => (
      <div
        key={`${item}-${index}`}
        style={{
          display: 'grid',
          gridTemplateColumns: '82px 1fr',
          alignItems: 'baseline',
          borderBottom: `1px solid ${colors.line}`,
          paddingBottom: 18,
        }}
      >
        <div style={{fontFamily: type.display, fontSize: 64, color: colors.red}}>
          {String(index + 1).padStart(2, '0')}
        </div>
        <div style={{fontFamily: type.mono, fontSize: 27, color: colors.paperDim}}>{item}</div>
      </div>
    ))}
  </div>
);

const DiagonalStamp: React.FC<{text: string}> = ({text}) => (
  <div
    style={{
      height: 520,
      border: `1px solid ${colors.line}`,
      display: 'grid',
      placeItems: 'center',
      background: `repeating-linear-gradient(135deg, ${colors.ghost}, ${colors.ghost} 12px, transparent 12px, transparent 28px)`,
      overflow: 'hidden',
    }}
  >
    <div
      style={{
        fontFamily: type.display,
        fontSize: 78,
        lineHeight: 0.96,
        textTransform: 'uppercase',
        transform: 'rotate(-9deg)',
        color: colors.cyan,
        textAlign: 'center',
        maxWidth: 430,
      }}
    >
      {text}
    </div>
  </div>
);

const ProofPanel: React.FC<{rows: [string, unknown][]}> = ({rows}) => (
  <div
    style={{
      border: `1px solid ${colors.cyan}`,
      background: colors.panel,
      boxShadow: shadows.panel,
      padding: 32,
    }}
  >
    {rows.map(([key, value], index) => (
      <div
        key={key}
        style={{
          padding: index === rows.length - 1 ? '0' : '0 0 30px',
          marginBottom: index === rows.length - 1 ? 0 : 30,
          borderBottom: index === rows.length - 1 ? 'none' : `1px solid ${colors.line}`,
        }}
      >
        <div style={{fontFamily: type.mono, fontSize: 22, color: colors.amber}}>{key}</div>
        <div
          style={{
            marginTop: 8,
            fontFamily: key === 'model' ? type.mono : type.display,
            fontSize: key === 'model' ? 29 : 70,
            lineHeight: 1,
            color: key === 'mode' ? colors.green : colors.paper,
            wordBreak: 'break-word',
          }}
        >
          {String(value)}
        </div>
      </div>
    ))}
  </div>
);

const ProofScroll: React.FC<{
  rows: [string, unknown][];
  manifest: NormalizedManifest;
}> = ({rows, manifest}) => {
  const frame = useCurrentFrame();
  const slide = interpolate(frame, [0, 20], [0, 1], {extrapolateRight: 'clamp'});
  return (
    <div style={{display: 'grid', gap: 18}}>
      <TerminalPanel lines={['metadata.json']} />
      {rows.map(([key, value], index) => (
        <div
          key={key}
          style={{
            borderLeft: `6px solid ${index % 2 === 0 ? colors.green : colors.cyan}`,
            paddingLeft: 16,
            transform: `translateY(${(1 - slide) * 18}px)`,
            opacity: slide,
          }}
        >
          <div style={{color: colors.paperDim, fontFamily: type.mono, fontSize: 18}}>{key}</div>
          <div
            style={{
              color: colors.paper,
              fontFamily: type.mono,
              fontSize: 32,
              wordBreak: 'break-word',
            }}
          >
            {String(value)}
          </div>
          <div style={{marginTop: 6, color: colors.paperDim, fontSize: 19, fontFamily: type.body}}>
            run folder: /tmp/{manifest.repo.name}/runs
          </div>
        </div>
      ))}
    </div>
  );
};

const TypeWriterLine: React.FC<{lines: string[]; y?: number}> = ({lines, y = 160}) => {
  const frame = useCurrentFrame();
  const line1 = lines[0] ?? '';
  const line2 = lines[1] ?? '';
  const charsA = Math.min(line1.length, Math.floor(frame / 2));
  const charsB = Math.max(0, Math.min(line2.length, Math.floor((frame - 120) / 2)));
  return (
    <div style={{position: 'absolute', left: 0, right: 60, top: y}}>
      <div
        style={{
          fontFamily: type.mono,
          fontSize: 30,
          lineHeight: 1.4,
          color: colors.paperDim,
          marginBottom: 18,
        }}
      >
        <span style={{color: colors.cyan}}>$ </span>
        {line1.slice(0, charsA)}
      </div>
      <div style={{fontFamily: type.mono, fontSize: 30, lineHeight: 1.4, color: colors.paperDim}}>
        <span style={{color: colors.cyan}}>$ </span>
        {line2.slice(0, Math.max(0, charsB))}
      </div>
    </div>
  );
};

const PhonePreview: React.FC<{manifest: NormalizedManifest}> = ({manifest}) => (
  <div
    style={{
      width: 360,
      height: 690,
      margin: '0 auto',
      border: `3px solid ${colors.paper}`,
      borderRadius: 8,
      padding: 18,
      background: colors.ink,
      boxShadow: shadows.panel,
    }}
  >
    <div style={{height: 9, width: 110, margin: '0 auto 26px', background: colors.paperDim}} />
    <div
      style={{
        height: 550,
        border: `1px solid ${colors.line}`,
        background: `linear-gradient(160deg, ${colors.panelSoft}, ${colors.carbon})`,
        padding: 24,
      }}
    >
      <div style={{fontFamily: type.display, fontSize: 54, lineHeight: 0.95, textTransform: 'uppercase'}}>
        {manifest.repo.name}
      </div>
      <div style={{marginTop: 30, fontFamily: type.mono, fontSize: 20, color: colors.green}}>
        demo.html / demo.mp4 / captions.srt
      </div>
    </div>
  </div>
);

const CaptionLine: React.FC<{
  manifest: NormalizedManifest;
  scene: NormalizedScene;
  frame: number;
  sceneProgress: number;
}> = ({manifest, scene, frame, sceneProgress}) => {
  const text = scene.caption_emphasis.length
    ? scene.caption_emphasis.join('  /  ')
    : scene.narration;
  const anchor = scene.type === 'ColdOpen' ? 'upper' : 'mid';
  const drift = interpolate(sceneProgress, [0, 1], [40, 0], {extrapolateRight: 'clamp'});
  const reveal = interpolate(frame, [0, 12, 30], [0, 1, 1], {
    easing: Easing.out(Easing.quad),
    extrapolateRight: 'clamp',
  });
  const label = manifest.repo.name;
  return (
    <div
      style={{
        position: 'absolute',
        left: anchor === 'upper' ? 0 : 52,
        right: 76,
        [anchor === 'upper' ? 'top' : 'bottom']: anchor === 'upper' ? 128 + drift : 48,
        display: 'flex',
        alignItems: 'center',
        gap: 18,
        color: colors.paper,
        opacity: reveal,
        transform: `translateX(${drift}px)`,
      }}
    >
      <div
        style={{
          width: 58,
          height: 5,
          background: colors.red,
          opacity: anchor === 'upper' ? 0.8 : 1,
        }}
      />
      <div
        style={{
          fontFamily: type.mono,
          fontSize: anchor === 'upper' ? 26 : 30,
          lineHeight: 1.18,
          textTransform: 'uppercase',
          color: colors.paper,
        }}
      >
        {text}
      </div>
      <div
        style={{
          marginLeft: 'auto',
          fontFamily: type.mono,
          fontSize: 20,
          color: colors.paperDim,
          opacity: 0.75,
        }}
      >
        {label}
      </div>
    </div>
  );
};

const Backplate: React.FC<{
  manifest: NormalizedManifest;
  scene: NormalizedScene;
  frame: number;
  sceneProgress: number;
}> = ({manifest, scene, frame, sceneProgress}) => {
  const sweep = interpolate(frame % 180, [0, 180], [-260, 1220]);
  const layout = String(scene.layout || inferSceneLayout(scene.type, 0));
  const theme = LAYOUT_EFFECT[KNOWN_LAYOUTS.includes(layout as SceneLayout)
    ? (layout as SceneLayout)
    : 'default'];
  const hue = theme.accent;
  const bgShift = interpolate(sceneProgress, [0, 1], [-20, 20], {extrapolateRight: 'clamp'});
  const sceneGradient = theme.background;
  const sideBand = theme.sideBand;
  return (
    <AbsoluteFill style={{transform: `translateX(${bgShift}px)`}}>
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background: `${sceneGradient}, repeating-linear-gradient(0deg, transparent 0, transparent 17px, ${colors.ghost} 18px)`,
        }}
      />
      <div
        style={{
          position: 'absolute',
          left: 54,
          top: 72,
          width: 880,
          height: 1220,
          border: `1px solid ${colors.line}`,
          transform: `skewY(-4deg) rotate(${interpolate(sceneProgress, [0, 1], [2, -2], {
            extrapolateRight: 'clamp',
          })}deg)`,
        }}
      />
      <div
        style={{
          position: 'absolute',
          left: sweep,
          top: 0,
          width: 180,
          height: '100%',
          background: `linear-gradient(90deg, transparent, ${hue}22, transparent)`,
          transform: 'skewX(-12deg)',
          opacity: interpolate(sceneProgress, [0, 1], [0.22, 0.52]),
        }}
      />
      <div
        style={{
          position: 'absolute',
          left: sideBand || spacing.pageX,
          bottom: 40,
          fontFamily: type.mono,
          color: colors.ghost,
          fontSize: 22,
          textTransform: 'uppercase',
        }}
      >
        {manifest.video.width}x{manifest.video.height} / {manifest.video.fps}fps
      </div>
      <div
        style={{
          position: 'absolute',
          right: sideBand,
          top: 40,
          fontFamily: type.mono,
          color: colors.paperDim,
          fontSize: 20,
          opacity: 0.8,
          textTransform: 'uppercase',
        }}
      >
        {scene.type}
      </div>
    </AbsoluteFill>
  );
};

const FilmGrain: React.FC = () => (
  <AbsoluteFill
    style={{
      pointerEvents: 'none',
      backgroundImage:
        `linear-gradient(${colors.ghost} 1px, transparent 1px), ` +
        `linear-gradient(90deg, ${colors.ghost} 1px, transparent 1px)`,
      backgroundSize: '42px 42px',
      mixBlendMode: 'screen',
      opacity: 0.35,
    }}
  />
);

const CRTScanlines: React.FC = () => (
  <AbsoluteFill
    style={{
      pointerEvents: 'none',
      backgroundImage:
        'repeating-linear-gradient(0deg, rgba(0, 0, 0, 0) 0px, rgba(0, 0, 0, 0) 2px, rgba(0, 0, 0, 0.18) 2px, rgba(0, 0, 0, 0.18) 3px)',
      mixBlendMode: 'multiply',
      opacity: 0.55,
    }}
  />
);

const CRTVignette: React.FC = () => (
  <AbsoluteFill
    style={{
      pointerEvents: 'none',
      background:
        'radial-gradient(ellipse at center, rgba(0,0,0,0) 50%, rgba(0,0,0,0.45) 100%)',
      mixBlendMode: 'multiply',
    }}
  />
);

const formatTimecode = (frame: number, fps: number): string => {
  const totalFrames = Math.max(0, Math.floor(frame));
  const ff = totalFrames % fps;
  const totalSec = Math.floor(totalFrames / fps);
  const ss = totalSec % 60;
  const mm = Math.floor(totalSec / 60) % 60;
  const hh = Math.floor(totalSec / 3600);
  const pad = (n: number, w = 2) => String(n).padStart(w, '0');
  return `${pad(hh)}:${pad(mm)}:${pad(ss)}:${pad(ff)}`;
};

const BAR_COLORS = ['#bcb6a8', '#c8b832', '#3ab2b9', '#4cb24a', '#bf3aa8', '#c8392a', '#3a48b9'];

const BroadcastFrame: React.FC<{manifest: NormalizedManifest}> = ({manifest}) => {
  const frame = useCurrentFrame();
  const recPulse = interpolate(Math.sin(frame / 8), [-1, 1], [0.45, 1]);
  const tc = formatTimecode(frame, 30);

  // Determine which scene we're in for the slate channel label
  let runningFrames = 0;
  let activeType = 'COLD-OPEN';
  for (const scene of manifest.scenes) {
    const dur = Math.max(1, Math.round(scene.duration_seconds * 30));
    if (frame >= runningFrames && frame < runningFrames + dur) {
      activeType = String(scene.type)
        .replace(/([a-z])([A-Z])/g, '$1-$2')
        .toUpperCase();
      break;
    }
    runningFrames += dur;
  }

  return (
    <AbsoluteFill style={{pointerEvents: 'none'}}>
      {/* Top tape edge */}
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          height: 4,
          background: `repeating-linear-gradient(90deg, ${colors.paperDim} 0 6px, transparent 6px 14px)`,
          opacity: 0.45,
        }}
      />

      {/* Slate header */}
      <div
        style={{
          position: 'absolute',
          top: 6,
          left: 0,
          right: 0,
          height: 56,
          background: `linear-gradient(to bottom, ${colors.carbon} 0%, ${colors.carbon}f5 100%)`,
          borderBottom: `1px dashed ${colors.line}`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 28px',
          fontFamily: type.mono,
          fontSize: 18,
          letterSpacing: '0.18em',
          color: colors.labelCream,
          textTransform: 'uppercase',
        }}
      >
        <span style={{color: colors.rec, opacity: recPulse, fontWeight: 700}}>● REC</span>
        <span>CH 02 — {activeType}</span>
        <span style={{color: colors.paperDim}}>{tc}</span>
      </div>

      {/* SMPTE color bars under slate */}
      <div
        style={{
          position: 'absolute',
          top: 62,
          left: 0,
          right: 0,
          height: 14,
          display: 'flex',
        }}
      >
        {BAR_COLORS.map((c, i) => (
          <div key={i} style={{flex: 1, background: c, opacity: 0.78}} />
        ))}
      </div>

      {/* Scope strip footer */}
      <div
        style={{
          position: 'absolute',
          bottom: 0,
          left: 0,
          right: 0,
          height: 28,
          borderTop: `1px dashed ${colors.line}`,
          background: `${colors.carbon}f8`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: 18,
          fontFamily: type.mono,
          fontSize: 11,
          letterSpacing: '0.18em',
          color: colors.paperDim,
          textTransform: 'uppercase',
        }}
      >
        <span>TBC</span>
        <span style={{color: colors.line}}>·</span>
        <span>SC-H</span>
        <span style={{color: colors.line}}>·</span>
        <span>DROPOUT 0.0%</span>
        <span style={{color: colors.line}}>·</span>
        <span style={{color: colors.lock}}>AGC ON</span>
        <span style={{color: colors.line}}>·</span>
        <span>1080×1920</span>
        <span style={{color: colors.line}}>·</span>
        <span>30FPS</span>
      </div>

      {/* Bottom tape edge */}
      <div
        style={{
          position: 'absolute',
          bottom: 30,
          left: 0,
          right: 0,
          height: 4,
          background: `repeating-linear-gradient(90deg, ${colors.paperDim} 0 6px, transparent 6px 14px)`,
          opacity: 0.45,
        }}
      />
    </AbsoluteFill>
  );
};

const splitHeadline = (text: string, maxWordsPerLine: number): string[] => {
  const words = text.split(/\s+/).filter(Boolean);
  const lines: string[] = [];
  for (let index = 0; index < words.length; index += maxWordsPerLine) {
    lines.push(words.slice(index, index + maxWordsPerLine).join(' '));
  }
  return lines.length ? lines : ['Repo to Shorts'];
};

const normalizeStringList = (value: unknown, limit: number): string[] => {
  if (!value) {
    return [];
  }
  if (Array.isArray(value)) {
    return value.map((item) => String(item)).filter(Boolean).slice(0, limit);
  }
  return [String(value)].filter(Boolean).slice(0, limit);
};

const positiveInteger = (value: unknown, fallback: number): number => {
  const number = Number(value);
  return Number.isFinite(number) && number > 0 ? Math.round(number) : fallback;
};
