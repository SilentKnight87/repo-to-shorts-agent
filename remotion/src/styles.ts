import type {CSSProperties} from 'react';

export const colors = {
  carbon: '#0b0707',
  ink: '#120c0c',
  panel: 'rgba(18, 12, 12, 0.86)',
  panelSoft: 'rgba(26, 16, 16, 0.72)',
  paper: '#f0e8d8',
  paperDim: '#c9b89a',
  // Mapped to website tokens:
  cyan: '#38d8ff',     // ghost cyan
  green: '#4afa8c',    // --lock
  amber: '#ffcf5a',    // chip / yellow accent
  red: '#ff5e5e',      // --rec
  live: '#ff8c4a',     // --live
  lock: '#4afa8c',
  rec: '#ff5e5e',
  ghostMagenta: '#ff3a8e',
  ghostCyan: '#38d8ff',
  labelCream: '#e8d8b6',
  labelInk: '#3a2a14',
  violet: '#b188ff',
  line: 'rgba(240, 232, 216, 0.18)',
  ghost: 'rgba(240, 232, 216, 0.08)',
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
