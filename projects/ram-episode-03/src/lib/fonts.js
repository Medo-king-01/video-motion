// The free type system for engine K — `assets/fonts/fonts.json` (built by tools/fonts_install.py).
//
// Cairo is the brand default; every other family has one documented job (docs/fonts.md). Register a
// family once per scene, then use it in `ctx.font`. Fonts are loaded lazily: a scene that only wants
// the brand face never downloads the other thirteen.
//
//   import { useFont, family } from './fonts.js';
//   await useFont('Kufam', 700);                      // registers "Kufam"
//   ctx.font = `700 120px ${family('Kufam')}`;        // -> '"Kufam", "Cairo", sans-serif'
import { loadFont } from './arabic.js';

const FALLBACK = { arabic: 'Cairo', latin: 'Inter' };
let manifest = null;
const loaded = new Set();

/** Read the manifest (once). Missing file → empty: the brand face is assumed to be in CSS. */
export async function loadManifest(base = '/assets/fonts/') {
  if (manifest) return manifest;
  try {
    const res = await fetch(`${base}fonts.json`, { cache: 'force-cache' });
    manifest = res.ok ? await res.json() : { families: {} };
  } catch {
    manifest = { families: {} };
  }
  return manifest;
}

/** The families the manifest declares (empty until `loadManifest()` has run). */
export async function families() {
  return Object.keys((await loadManifest()).families || {});
}

/** Nearest available weight at or below `weight` for a family, or null when it is unknown. */
export async function weightFile(name, weight = 800, base = '/assets/fonts/') {
  const fams = (await loadManifest(base)).families || {};
  const meta = fams[name];
  if (!meta || !meta.weights?.length) return null;
  const ws = [...meta.weights].sort((a, b) => a.weight - b.weight);
  const fit = ws.filter((w) => w.weight <= weight);
  const pick = (fit.length ? fit : ws).at(-1);
  return { url: `${base}${name}/${pick.file}`, weight: pick.weight };
}

/** Register one family (memoised). Returns the family name, or null when it is not in the manifest. */
export async function useFont(name, weight = 800, base = '/assets/fonts/') {
  const key = `${name}@${weight}`;
  if (loaded.has(key)) return name;
  const file = await weightFile(name, weight, base);
  if (!file) return null;
  try {
    await loadFont(name, file.url, { weight: String(file.weight) });
    loaded.add(key);
    return name;
  } catch {
    return null;
  }
}

/** Register several families in parallel — call from a scene's init(). */
export async function useFonts(list, base = '/assets/fonts/') {
  return Promise.all(list.map((item) => (Array.isArray(item) ? useFont(item[0], item[1], base)
    : useFont(item, 800, base))));
}

/** A CSS font-family stack for a manifest family, falling back to the script default. */
export function family(name, script = 'arabic') {
  const fallback = FALLBACK[script] || 'sans-serif';
  return name && name !== fallback ? `"${name}", "${fallback}", sans-serif` : `"${fallback}", sans-serif`;
}
