import React from 'react';
import {Composition, registerRoot} from 'remotion';
import {
  DEFAULT_MANIFEST,
  RepoShortsVideo,
  type RepoShortsManifest,
  getDurationInFrames,
  normalizeManifest,
} from './RepoShortsVideo';

const Root: React.FC = () => {
  return React.createElement(Composition, {
    id: 'RepoShortsVideo',
    component: RepoShortsVideo,
    durationInFrames: getDurationInFrames(DEFAULT_MANIFEST),
    fps: DEFAULT_MANIFEST.video.fps,
    width: DEFAULT_MANIFEST.video.width,
    height: DEFAULT_MANIFEST.video.height,
    defaultProps: DEFAULT_MANIFEST,
    calculateMetadata: ({props}: {props: RepoShortsManifest}) => {
      const manifest = normalizeManifest(props);
      return {
        durationInFrames: getDurationInFrames(manifest),
        fps: manifest.video.fps,
        width: manifest.video.width,
        height: manifest.video.height,
        props: manifest,
      };
    },
  });
};

registerRoot(Root);
