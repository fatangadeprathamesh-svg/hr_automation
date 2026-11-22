/**
 * Contrast Checker verifying WCAG 2.1 compliance for all theme pairs
 * Normal text: >= 4.5:1
 * Large text & UI graphical components: >= 3:1
 */

function srgbToLinear(c) {
  const v = c / 255;
  return v <= 0.04045 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
}

function hexToRgb(hex) {
  let clean = hex.replace('#', '');
  if (clean.length === 3) {
    clean = clean.split('').map((c) => c + c).join('');
  }
  const num = parseInt(clean, 16);
  return {
    r: (num >> 16) & 255,
    g: (num >> 8) & 255,
    b: num & 255,
  };
}

function getLuminance(hex) {
  const { r, g, b } = hexToRgb(hex);
  return 0.2126 * srgbToLinear(r) + 0.7152 * srgbToLinear(g) + 0.0722 * srgbToLinear(b);
}

function getContrast(fgHex, bgHex) {
  const l1 = getLuminance(fgHex);
  const l2 = getLuminance(bgHex);
  const brightest = Math.max(l1, l2);
  const darkest = Math.min(l1, l2);
  return (brightest + 0.05) / (darkest + 0.05);
}

const themeTokens = {
  dark: {
    bg: '#0F1218',
    surface: '#171B24',
    surface2: '#212735',
    text: '#F0F4FA',
    textMuted: '#8B95A8',
    accent: '#5B9BF3',
    accentInk: '#0F1218',
    accentText: '#7CB1F7',
    error: '#F87171',
    warning: '#FBBF24',
    success: '#34D399',
    info: '#C084FC',
  },
  light: {
    bg: '#F4F6FA',
    surface: '#FFFFFF',
    surface2: '#E5E9F2',
    text: '#0F1218',
    textMuted: '#576074',
    accent: '#2B6CBF',
    accentInk: '#FFFFFF',
    accentText: '#205499',
    accentBorder: '#205499',
    error: '#B91C1C',
    warning: '#B45309',
    success: '#047857',
    info: '#7E22CE',
  },
};

const checks = [
  // Dark theme checks
  { theme: 'dark', role: 'text', name: 'Text on Background', fg: themeTokens.dark.text, bg: themeTokens.dark.bg, req: 4.5 },
  { theme: 'dark', role: 'text', name: 'Text on Surface', fg: themeTokens.dark.text, bg: themeTokens.dark.surface, req: 4.5 },
  { theme: 'dark', role: 'text', name: 'Text on Surface-2', fg: themeTokens.dark.text, bg: themeTokens.dark.surface2, req: 4.5 },
  { theme: 'dark', role: 'text', name: 'Text Muted on Surface', fg: themeTokens.dark.textMuted, bg: themeTokens.dark.surface, req: 4.5 },
  { theme: 'dark', role: 'text', name: 'Text Muted on Surface-2', fg: themeTokens.dark.textMuted, bg: themeTokens.dark.surface2, req: 4.5 },
  { theme: 'dark', role: 'text', name: 'Accent Text on Background', fg: themeTokens.dark.accentText, bg: themeTokens.dark.bg, req: 4.5 },
  { theme: 'dark', role: 'text', name: 'Accent Text on Surface', fg: themeTokens.dark.accentText, bg: themeTokens.dark.surface, req: 4.5 },
  { theme: 'dark', role: 'text', name: 'Accent Ink on Accent Button', fg: themeTokens.dark.accentInk, bg: themeTokens.dark.accent, req: 4.5 },
  { theme: 'dark', role: 'status', name: 'Error Status on Surface', fg: themeTokens.dark.error, bg: themeTokens.dark.surface, req: 4.5 },
  { theme: 'dark', role: 'status', name: 'Warning Status on Surface', fg: themeTokens.dark.warning, bg: themeTokens.dark.surface, req: 4.5 },
  { theme: 'dark', role: 'status', name: 'Success Status on Surface', fg: themeTokens.dark.success, bg: themeTokens.dark.surface, req: 4.5 },
  { theme: 'dark', role: 'status', name: 'Info Status on Surface', fg: themeTokens.dark.info, bg: themeTokens.dark.surface, req: 4.5 },
  { theme: 'dark', role: 'ui', name: 'Accent UI Component on Surface', fg: themeTokens.dark.accent, bg: themeTokens.dark.surface, req: 3.0 },

  // Light theme checks
  { theme: 'light', role: 'text', name: 'Text on Background', fg: themeTokens.light.text, bg: themeTokens.light.bg, req: 4.5 },
  { theme: 'light', role: 'text', name: 'Text on Surface (White)', fg: themeTokens.light.text, bg: themeTokens.light.surface, req: 4.5 },
  { theme: 'light', role: 'text', name: 'Text Muted on Surface (White)', fg: themeTokens.light.textMuted, bg: themeTokens.light.surface, req: 4.5 },
  { theme: 'light', role: 'text', name: 'Text Muted on Background (Ivory)', fg: themeTokens.light.textMuted, bg: themeTokens.light.bg, req: 4.5 },
  { theme: 'light', role: 'text', name: 'Accent Text on Surface (White)', fg: themeTokens.light.accentText, bg: themeTokens.light.surface, req: 4.5 },
  { theme: 'light', role: 'text', name: 'Accent Text on Background (Ivory)', fg: themeTokens.light.accentText, bg: themeTokens.light.bg, req: 4.5 },
  { theme: 'light', role: 'text', name: 'Accent Ink on Accent Button', fg: themeTokens.light.accentInk, bg: themeTokens.light.accent, req: 4.5 },
  { theme: 'light', role: 'status', name: 'Error Status on Surface (White)', fg: themeTokens.light.error, bg: themeTokens.light.surface, req: 4.5 },
  { theme: 'light', role: 'status', name: 'Warning Status on Surface (White)', fg: themeTokens.light.warning, bg: themeTokens.light.surface, req: 4.5 },
  { theme: 'light', role: 'status', name: 'Success Status on Surface (White)', fg: themeTokens.light.success, bg: themeTokens.light.surface, req: 4.5 },
  { theme: 'light', role: 'status', name: 'Info Status on Surface (White)', fg: themeTokens.light.info, bg: themeTokens.light.surface, req: 4.5 },
  { theme: 'light', role: 'ui', name: 'Accent Button Border on Surface (White)', fg: themeTokens.light.accentBorder, bg: themeTokens.light.surface, req: 3.0 },
  { theme: 'light', role: 'ui', name: 'Accent Button Border on Background (Ivory)', fg: themeTokens.light.accentBorder, bg: themeTokens.light.bg, req: 3.0 },
];

console.log('========================================================================');
console.log(' WCAG 2.1 CONTRAST VERIFICATION REPORT (INDIGO & GOLD THEME)');
console.log('========================================================================\n');

let allPassed = true;
const results = [];

for (const check of checks) {
  const contrast = getContrast(check.fg, check.bg);
  const passed = contrast >= check.req;
  if (!passed) allPassed = false;

  const resultObj = {
    Theme: check.theme.toUpperCase(),
    Element: check.name,
    'Foreground': check.fg,
    'Background': check.bg,
    'Required': `${check.req}:1`,
    'Actual Ratio': `${contrast.toFixed(2)}:1`,
    'Status': passed ? 'PASS ✓' : 'FAIL ✗',
  };
  results.push(resultObj);
}

console.table(results);

if (allPassed) {
  console.log('\n✓ ALL CONTRAST PAIRS PASSED WCAG 2.1 SPECIFICATION!\n');
} else {
  console.error('\n✗ SOME CONTRAST PAIRS FAILED. ADJUST VALUES BEFORE PROCEEDING.\n');
  process.exit(1);
}
