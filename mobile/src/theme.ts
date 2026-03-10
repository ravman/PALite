export const colors = {
  bg: '#0a0a0f',
  card: '#14141f',
  card2: '#1a1a2e',
  accent: '#6c5ce7',
  accent2: '#a29bfe',
  green: '#00b894',
  red: '#e17055',
  orange: '#fdcb6e',
  text: '#e8e8f0',
  text2: '#8888a0',
  border: '#2a2a3e',
  white: '#ffffff',
};

export const radius = {
  sm: 8,
  md: 12,
  lg: 16,
  xl: 20,
  full: 999,
};

export const spacing = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 20,
  xxl: 24,
};

export const typography = {
  h1: { fontSize: 28, fontWeight: '700' as const, color: colors.text },
  h2: { fontSize: 22, fontWeight: '700' as const, color: colors.text },
  h3: { fontSize: 16, fontWeight: '600' as const, color: colors.text },
  body: { fontSize: 14, fontWeight: '400' as const, color: colors.text },
  caption: { fontSize: 12, fontWeight: '400' as const, color: colors.text2 },
  label: { fontSize: 12, fontWeight: '500' as const, color: colors.text2 },
  mono: { fontSize: 14, fontFamily: 'monospace' as const, color: colors.text },
};
