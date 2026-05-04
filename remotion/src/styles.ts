import type {CSSProperties} from 'react';

export const colors = {
  carbon: '#080a0f',
  ink: '#10131b',
  panel: 'rgba(13, 17, 26, 0.86)',
  panelSoft: 'rgba(23, 29, 43, 0.72)',
  paper: '#f6f1df',
  paperDim: '#d5cda9',
  cyan: '#45f7ff',
  green: '#a8ff60',
  amber: '#ffcf5a',
  red: '#ff4e64',
  violet: '#b188ff',
  line: 'rgba(246, 241, 223, 0.18)',
  ghost: 'rgba(246, 241, 223, 0.08)',
};

export const type = {
  display:
    '"Avenir Next Condensed", "Arial Narrow", "Helvetica Neue Condensed", sans-serif',
  body: '"DIN Alternate", "Avenir Next", "Helvetica Neue", sans-serif',
  mono:
    '"JetBrains Mono", "SFMono-Regular", "Cascadia Code", "Liberation Mono", monospace',
};

export const spacing = {
  pageX: 82,
  pageTop: 88,
  pageBottom: 94,
  gutter: 34,
  radius: 8,
};

export const shadows = {
  glowCyan: `0 0 34px ${colors.cyan}55, 0 0 80px ${colors.cyan}24`,
  glowAmber: `0 0 30px ${colors.amber}44`,
  panel: '0 26px 60px rgba(0, 0, 0, 0.34)',
};

export const baseFill: CSSProperties = {
  backgroundColor: colors.carbon,
  color: colors.paper,
  fontFamily: type.body,
  overflow: 'hidden',
};

export const safeArea: CSSProperties = {
  position: 'absolute',
  inset: `${spacing.pageTop}px ${spacing.pageX}px ${spacing.pageBottom}px`,
};

export const monoLabel: CSSProperties = {
  fontFamily: type.mono,
  textTransform: 'uppercase',
  letterSpacing: 0,
  fontSize: 28,
  color: colors.green,
};

export const hairline: CSSProperties = {
  height: 1,
  background: `linear-gradient(90deg, transparent, ${colors.line}, transparent)`,
};
