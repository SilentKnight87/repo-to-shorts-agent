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

type SceneType =
  | 'ColdOpen'
  | 'RepoEvidence'
  | 'PainPoint'
  | 'PipelineMap'
  | 'ArtifactStack'
  | 'LiveProof'
  | 'DemoPreview'
  | 'CTAEndCard';

export type RepoShortsScene = {
  type?: SceneType | string;
  duration_seconds?: number;
  headline?: string;
  narration?: string;
  evidence?: string[];
  caption_emphasis?: string[];
};

export type RepoShortsManifest = {
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
  scenes: Required<RepoShortsScene>[];
  artifacts: string[];
};

const DEFAULT_SCENES: Required<RepoShortsScene>[] = [
  {
    type: 'ColdOpen',
    duration_seconds: 3,
    headline: "This repo made the video you're watching.",
    narration: "This repo made the video you're watching.",
    evidence: ['repo-to-shorts-agent'],
    caption_emphasis: ['repo', 'video'],
  },
  {
    type: 'RepoEvidence',
    duration_seconds: 6,
    headline: 'Source code becomes a launch package.',
    narration: 'Repo-to-Shorts inspects the local project and turns it into a short-video package.',
    evidence: ['src/repo_to_shorts/pipeline.py', 'src/repo_to_shorts/kimi.py'],
    caption_emphasis: ['source', 'launch package'],
  },
  {
    type: 'PipelineMap',
    duration_seconds: 7,
    headline: 'Ingest. Critique. Render. Submit.',
    narration: 'The pipeline builds the brief, storyboard, captions, copy, browser demo, and optional MP4.',
    evidence: ['repo brief', 'storyboard', 'captions.srt', 'demo.mp4'],
    caption_emphasis: ['brief', 'captions', 'MP4'],
  },
  {
    type: 'LiveProof',
    duration_seconds: 6,
    headline: 'Kimi proof is visible in metadata.',
    narration: 'The generated run records live model mode, provider, and model without faking proof.',
    evidence: ['metadata.json'],
    caption_emphasis: ['live-api', 'metadata'],
  },
  {
    type: 'CTAEndCard',
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
  scenes: DEFAULT_SCENES,
  artifacts: ['demo.mp4', 'metadata.json', 'captions.srt', 'submission_pack.md'],
};

const KNOWN_SCENE_TYPES = new Set<string>([
  'ColdOpen',
  'RepoEvidence',
  'PainPoint',
  'PipelineMap',
  'ArtifactStack',
  'LiveProof',
  'DemoPreview',
  'CTAEndCard',
]);

export const normalizeManifest = (input: RepoShortsManifest = {}): NormalizedManifest => {
  const video = input.video ?? {};
  const repo = input.repo ?? {};
  const scenes = input.scenes && input.scenes.length > 0 ? input.scenes : DEFAULT_SCENES;
  const normalizedScenes = scenes.map((scene, index) => ({
    type: String(scene.type || DEFAULT_SCENES[index % DEFAULT_SCENES.length].type),
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
  };
};

export const getDurationInFrames = (manifest: RepoShortsManifest): number => {
  const normalized = normalizeManifest(manifest);
  const sceneDuration = normalized.scenes.reduce(
    (total, scene) => total + scene.duration_seconds,
    0,
  );
  const seconds = sceneDuration || normalized.video.duration_seconds;
  return Math.max(1, Math.round(seconds * normalized.video.fps));
};

export const RepoShortsVideo: React.FC<RepoShortsManifest> = (props) => {
  const manifest = normalizeManifest(props);
  const {fps} = useVideoConfig();
  let from = 0;

  return (
    <AbsoluteFill style={baseFill}>
      <Backplate manifest={manifest} />
      {manifest.scenes.map((scene, index) => {
        const duration = Math.max(1, Math.round(scene.duration_seconds * fps));
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
    </AbsoluteFill>
  );
};

const SceneFrame: React.FC<{
  manifest: NormalizedManifest;
  scene: Required<RepoShortsScene>;
  sceneIndex: number;
  sceneCount: number;
  durationInFrames: number;
}> = ({manifest, scene, sceneIndex, sceneCount, durationInFrames}) => {
  const isKnownSceneType = KNOWN_SCENE_TYPES.has(scene.type);
  const typeName = scene.type;
  const frame = useCurrentFrame();
  const entrance = spring({frame, fps: 30, config: {damping: 18, stiffness: 130}});
  const exit = interpolate(
    frame,
    [durationInFrames - 18, durationInFrames],
    [1, 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.in(Easing.cubic)},
  );
  const opacity = Math.min(entrance, exit);
  const y = interpolate(entrance, [0, 1], [34, 0]);

  return (
    <AbsoluteFill style={{opacity}}>
      <div style={{...safeArea, transform: `translateY(${y}px)`}}>
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
        <CaptionLine scene={scene} />
      </div>
    </AbsoluteFill>
  );
};

const SceneChrome: React.FC<{
  scene: Required<RepoShortsScene>;
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
        {splitHeadline(scene.headline, 4).map((part, index) => (
          <div key={part} style={{color: index % 2 === 0 ? colors.paper : colors.cyan}}>
            {part}
          </div>
        ))}
      </div>
      <div
        style={{
          marginTop: 64,
          display: 'inline-flex',
          border: `1px solid ${colors.cyan}`,
          boxShadow: shadows.glowCyan,
          padding: '20px 26px',
          fontFamily: type.mono,
          fontSize: 34,
          color: colors.green,
          background: colors.panel,
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
  scene: Required<RepoShortsScene>;
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

const PipelineMap: React.FC<{scene: Required<RepoShortsScene>}> = ({scene}) => {
  const steps = ['ingest', 'Kimi critic', 'storyboard', 'render', 'submission'];
  return (
    <FullStage headline={scene.headline} kicker="pipeline">
      <div style={{display: 'grid', gridTemplateRows: `repeat(${steps.length}, 1fr)`, gap: 22}}>
        {steps.map((step, index) => (
          <div
            key={step}
            style={{
              display: 'grid',
              gridTemplateColumns: '132px 1fr',
              alignItems: 'center',
              minHeight: 138,
            }}
          >
            <div style={{fontFamily: type.mono, fontSize: 34, color: colors.amber}}>
              0{index + 1}
            </div>
            <div
              style={{
                borderLeft: `8px solid ${index === 1 ? colors.green : colors.cyan}`,
                paddingLeft: 32,
                fontFamily: type.display,
                fontSize: 72,
                lineHeight: 1,
                textTransform: 'uppercase',
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
      right={<TerminalPanel lines={['metadata.json', ...proofRows.map(([key, value]) => `${key}: ${value}`)]} />}
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
    <div
      style={{
        marginTop: 70,
        border: `1px solid ${colors.green}`,
        background: '#050805',
        boxShadow: shadows.glowCyan,
        padding: 34,
        fontFamily: type.mono,
        fontSize: 34,
        lineHeight: 1.35,
        color: colors.green,
      }}
    >
      <span style={{color: colors.paperDim}}>$ </span>
      repo-shorts analyze . --render mp4
    </div>
    <div
      style={{
        marginTop: 70,
        fontFamily: type.display,
        fontSize: 84,
        lineHeight: 1,
        color: colors.cyan,
        textTransform: 'uppercase',
      }}
    >
      {manifest.artifacts.slice(0, 4).join(' / ')}
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

const CaptionLine: React.FC<{scene: Required<RepoShortsScene>}> = ({scene}) => {
  const text = scene.caption_emphasis.length
    ? scene.caption_emphasis.join('  /  ')
    : scene.narration;
  return (
    <div
      style={{
        position: 'absolute',
        left: 0,
        right: 76,
        bottom: 48,
        display: 'flex',
        alignItems: 'center',
        gap: 18,
        color: colors.paper,
      }}
    >
      <div style={{width: 58, height: 5, background: colors.red}} />
      <div
        style={{
          fontFamily: type.mono,
          fontSize: 30,
          lineHeight: 1.18,
          textTransform: 'uppercase',
          color: colors.paper,
        }}
      >
        {text}
      </div>
    </div>
  );
};

const Backplate: React.FC<{manifest: NormalizedManifest}> = ({manifest}) => {
  const frame = useCurrentFrame();
  const sweep = interpolate(frame % 180, [0, 180], [-260, 1220]);
  return (
    <AbsoluteFill>
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background:
            `linear-gradient(135deg, ${colors.carbon} 0%, #111820 46%, #12100a 100%), ` +
            `repeating-linear-gradient(0deg, transparent 0, transparent 17px, ${colors.ghost} 18px)`,
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
          transform: 'skewY(-4deg)',
        }}
      />
      <div
        style={{
          position: 'absolute',
          left: sweep,
          top: 0,
          width: 180,
          height: '100%',
          background: `linear-gradient(90deg, transparent, ${colors.cyan}17, transparent)`,
          transform: 'skewX(-12deg)',
        }}
      />
      <div
        style={{
          position: 'absolute',
          left: spacing.pageX,
          bottom: 40,
          fontFamily: type.mono,
          color: colors.ghost,
          fontSize: 22,
          textTransform: 'uppercase',
        }}
      >
        {manifest.video.width}x{manifest.video.height} / {manifest.video.fps}fps
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
