export const KNOWN_SCENE_TYPES = [
  'ColdOpen',
  'RepoEvidence',
  'PainPoint',
  'PipelineMap',
  'ArtifactStack',
  'LiveProof',
  'DemoPreview',
  'CTAEndCard',
] as const;

export type SceneType = (typeof KNOWN_SCENE_TYPES)[number];

export const KNOWN_LAYOUTS = [
  'cover_burst',
  'repo_card',
  'problem_block',
  'pipeline_flow',
  'artifact_wall',
  'proof_sheet',
  'preview_frame',
  'cta_band',
] as const;

export type SceneLayout = (typeof KNOWN_LAYOUTS)[number];

export const inferSceneType = (value: unknown): SceneType | 'Unknown' => {
  const normalized = String(value || '').trim();
  if (!normalized) {
    return 'ColdOpen';
  }
  const exact = KNOWN_SCENE_TYPES.find((type) => type.toLowerCase() === normalized.toLowerCase());
  if (exact) {
    return exact;
  }
  return 'Unknown';
};

export const inferSceneLayout = (type: SceneType | string, index: number): string => {
  switch (type) {
    case 'ColdOpen':
      return 'cover_burst';
    case 'RepoEvidence':
      return 'repo_card';
    case 'PainPoint':
      return 'problem_block';
    case 'PipelineMap':
      return 'pipeline_flow';
    case 'ArtifactStack':
      return 'artifact_wall';
    case 'LiveProof':
      return 'proof_sheet';
    case 'DemoPreview':
      return 'preview_frame';
    case 'CTAEndCard':
      return 'cta_band';
    default:
      return index % 3 === 0 ? 'problem_block' : 'artifact_wall';
  }
};
