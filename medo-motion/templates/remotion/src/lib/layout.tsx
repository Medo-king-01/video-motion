/**
 * Screen-space layout box capture and audit for Engine R (Remotion).
 *
 * Mirrors the conservative AABB contract of `procedural-reels/layout_p.py` (P)
 * and `render/lib/layout.js` (K):
 * - `L00`: invalid/missing registered box or unknown text zone
 * - `L01`: text ink or foreground overlay outside its brand safe zone (`content`, `caption`, `hud`)
 * - `L02`: text box overlaps another text box or a protected `keep` box
 * - `L03`: text box overlaps a protected presenter `face` box
 * - `L04`: non-`hud` text/overlay box overlaps `PLATFORM_RIGHT_RAIL` (x940..1080, y1100..1500)
 * - `L05`: `content`-layer text extends outside Fixed Stage `win(t)`
 * - `L06`: `content`-layer text clipped by Fixed Stage `win(t)` rounded corners (`r > 0`)
 *
 * Boxes are conservative post-line-wrap, post-transform screen-space AABBs;
 * this module does not perform independent pixel-level text clipping/truncation detection.
 */
import React from 'react';
import {BRAND} from '../brand';

export type LayoutZone = 'content' | 'caption' | 'hud';
export type LayoutBoxKind = 'text' | 'face' | 'keep';
export type StageLayer = 'under' | 'content' | 'over';

export type StageWindowBox = {
  x: number;
  y: number;
  w: number;
  h: number;
  r?: number;
};

export type LayoutBox = {
  id: string;
  kind: LayoutBoxKind;
  zone?: LayoutZone;
  layer?: StageLayer;
  chrome?: boolean;
  text?: string;
  x: number;
  y: number;
  w: number;
  h: number;
};

export type LayoutIssue = {
  code: 'L00' | 'L01' | 'L02' | 'L03' | 'L04' | 'L05' | 'L06';
  ids: string[];
  message: string;
};

export type LayoutAuditReport = {
  ok: boolean;
  boxes: LayoutBox[];
  issues: LayoutIssue[];
};

export const PLATFORM_RIGHT_RAIL = Object.freeze({
  x: 940,
  y: 1100,
  w: 140,
  h: 400,
});

const finite = (n: unknown): n is number => typeof n === 'number' && Number.isFinite(n);

function isStageFullscreen(win: StageWindowBox | null | undefined): boolean {
  if (!win || typeof win !== 'object') return true;
  if (!finite(win.x) || !finite(win.y) || !finite(win.w) || !finite(win.h)) return true;
  const r = finite(win.r) ? win.r : 0;
  return (
    Math.abs(win.x) <= 1e-4 &&
    Math.abs(win.y) <= 1e-4 &&
    Math.abs(win.w - BRAND.width) <= 1e-4 &&
    Math.abs(win.h - BRAND.height) <= 1e-4 &&
    Math.abs(r) <= 1e-4
  );
}

function windowCornerClips(box: LayoutBox, win: StageWindowBox, eps = 0.5): string[] {
  const r = finite(win.r) ? win.r : 0;
  if (r <= eps) return [];
  const bx0 = box.x;
  const by0 = box.y;
  const bx1 = bx0 + box.w;
  const by1 = by0 + box.h;
  const wx0 = win.x;
  const wy0 = win.y;
  const wx1 = wx0 + win.w;
  const wy1 = wy0 + win.h;

  const px0 = Math.max(wx0, Math.min(wx1, bx0));
  const py0 = Math.max(wy0, Math.min(wy1, by0));
  const px1 = Math.max(wx0, Math.min(wx1, bx1));
  const py1 = Math.max(wy0, Math.min(wy1, by1));
  if (px1 <= px0 || py1 <= py0) return [];

  const out: string[] = [];
  if (px0 < wx0 + r && py0 < wy0 + r && Math.hypot(wx0 + r - px0, wy0 + r - py0) > r + eps) {
    out.push('top-left');
  }
  if (px1 > wx1 - r && py0 < wy0 + r && Math.hypot(px1 - (wx1 - r), wy0 + r - py0) > r + eps) {
    out.push('top-right');
  }
  if (px0 < wx0 + r && py1 > wy1 - r && Math.hypot(wx0 + r - px0, py1 - (wy1 - r)) > r + eps) {
    out.push('bottom-left');
  }
  if (px1 > wx1 - r && py1 > wy1 - r && Math.hypot(px1 - (wx1 - r), py1 - (wy1 - r)) > r + eps) {
    out.push('bottom-right');
  }
  return out;
}

function effectiveCollisionRect(
  box: LayoutBox,
  other: LayoutBox,
  stageWin: StageWindowBox | null | undefined,
  framedStage: boolean,
): [number, number, number, number] | null {
  const x0 = box.x;
  const y0 = box.y;
  const x1 = x0 + box.w;
  const y1 = y0 + box.h;
  if (!framedStage || !stageWin) return [x0, y0, x1, y1];
  const bLayer = box.layer || (box.zone === 'hud' || box.zone === 'caption' ? 'over' : 'content');
  const oLayer = other.layer || (other.zone === 'hud' || other.zone === 'caption' ? 'over' : 'content');
  if (bLayer === 'content' && oLayer !== 'content') {
    const wx0 = stageWin.x;
    const wy0 = stageWin.y;
    const wx1 = wx0 + stageWin.w;
    const wy1 = wy0 + stageWin.h;
    const cx0 = Math.max(x0, wx0);
    const cy0 = Math.max(y0, wy0);
    const cx1 = Math.min(x1, wx1);
    const cy1 = Math.min(y1, wy1);
    if (cx1 <= cx0 || cy1 <= cy0) return null;
    return [cx0, cy0, cx1, cy1];
  }
  return [x0, y0, x1, y1];
}

export function safeEnvelope(
  zone: LayoutZone = 'content',
  {checkPlatformUi = true}: {checkPlatformUi?: boolean} = {},
) {
  if (!['content', 'caption', 'hud'].includes(zone)) {
    throw new Error(`Unknown layout zone: ${zone}`);
  }
  const yRange: readonly [number, number] =
    zone === 'caption'
      ? [BRAND.contentY[1], BRAND.belowIsDead]
      : zone === 'hud'
        ? [0, BRAND.contentY[0]]
        : BRAND.contentY;
  return {
    w: BRAND.width,
    h: BRAND.height,
    fps: BRAND.fps,
    margin: BRAND.margin,
    zone,
    x: [BRAND.margin, BRAND.width - BRAND.margin] as const,
    y: [yRange[0], yRange[1]] as const,
    nothingImportantBelowY: BRAND.belowIsDead,
    platformRightRail: checkPlatformUi ? {...PLATFORM_RIGHT_RAIL} : null,
  };
}

export function auditLayout(
  boxes: LayoutBox[],
  {
    minOverlap = 2,
    checkPlatformUi = false,
    stageWin = null,
  }: {minOverlap?: number; checkPlatformUi?: boolean; stageWin?: StageWindowBox | null} = {},
): LayoutIssue[] {
  if (!Array.isArray(boxes)) throw new Error('Layout capture is missing');
  const issues: LayoutIssue[] = [];
  const validFlags: boolean[] = [];
  const hasStageWin = Boolean(
    stageWin &&
      typeof stageWin === 'object' &&
      finite(stageWin.x) &&
      finite(stageWin.y) &&
      finite(stageWin.w) &&
      finite(stageWin.h) &&
      stageWin.w > 0 &&
      stageWin.h > 0,
  );
  const framedStage = Boolean(hasStageWin && !isStageFullscreen(stageWin));

  for (const b of boxes) {
    const ok = Boolean(
      b &&
        typeof b.id === 'string' &&
        b.id.trim() &&
        ['text', 'face', 'keep'].includes(b.kind) &&
        finite(b.x) &&
        finite(b.y) &&
        finite(b.w) &&
        finite(b.h) &&
        b.w > 0 &&
        b.h > 0,
    );
    validFlags.push(ok);
    if (!ok) {
      issues.push({code: 'L00', ids: [b?.id || '?'], message: 'Invalid registered box'});
      continue;
    }
    if (b.kind !== 'text') {
      if (b.layer === 'over' && b.chrome !== true) {
        if (
          b.x < BRAND.margin ||
          b.x + b.w > BRAND.width - BRAND.margin ||
          b.y < 0 ||
          b.y + b.h > BRAND.belowIsDead
        ) {
          issues.push({code: 'L01', ids: [b.id], message: 'Foreground overlay escapes safe region'});
        }
        if (checkPlatformUi) {
          const rx =
            Math.min(b.x + b.w, PLATFORM_RIGHT_RAIL.x + PLATFORM_RIGHT_RAIL.w) -
            Math.max(b.x, PLATFORM_RIGHT_RAIL.x);
          const ry =
            Math.min(b.y + b.h, PLATFORM_RIGHT_RAIL.y + PLATFORM_RIGHT_RAIL.h) -
            Math.max(b.y, PLATFORM_RIGHT_RAIL.y);
          if (rx >= minOverlap && ry >= minOverlap) {
            issues.push({
              code: 'L04',
              ids: [b.id],
              message: 'Foreground overlay overlaps social right-rail UI zone (x940..1080 y1100..1500)',
            });
          }
        }
      }
      continue;
    }
    const zone = b.zone || 'content';
    if (!['content', 'caption', 'hud'].includes(zone)) {
      issues.push({code: 'L00', ids: [b.id], message: 'Unknown text zone'});
      continue;
    }
    const range: readonly [number, number] =
      zone === 'caption'
        ? [BRAND.contentY[1], BRAND.belowIsDead]
        : zone === 'hud'
          ? [0, BRAND.contentY[0]]
          : BRAND.contentY;
    if (
      b.x < BRAND.margin ||
      b.x + b.w > BRAND.width - BRAND.margin ||
      b.y < range[0] ||
      b.y + b.h > range[1]
    ) {
      issues.push({code: 'L01', ids: [b.id], message: `Ink outside ${zone} safe zone`});
    }
    if (checkPlatformUi && zone !== 'hud') {
      const rx =
        Math.min(b.x + b.w, PLATFORM_RIGHT_RAIL.x + PLATFORM_RIGHT_RAIL.w) -
        Math.max(b.x, PLATFORM_RIGHT_RAIL.x);
      const ry =
        Math.min(b.y + b.h, PLATFORM_RIGHT_RAIL.y + PLATFORM_RIGHT_RAIL.h) -
        Math.max(b.y, PLATFORM_RIGHT_RAIL.y);
      if (rx >= minOverlap && ry >= minOverlap) {
        issues.push({
          code: 'L04',
          ids: [b.id],
          message: 'Ink overlaps social right-rail UI zone (x940..1080 y1100..1500)',
        });
      }
    }
    const effLayer = b.layer || (zone === 'hud' || zone === 'caption' ? 'over' : 'content');
    if (framedStage && stageWin && effLayer === 'content') {
      const eps = 0.5;
      if (
        b.x < stageWin.x - eps ||
        b.y < stageWin.y - eps ||
        b.x + b.w > stageWin.x + stageWin.w + eps ||
        b.y + b.h > stageWin.y + stageWin.h + eps
      ) {
        issues.push({
          code: 'L05',
          ids: [b.id],
          message: 'Content ink extends outside Fixed Stage window win(t)',
        });
      }
      const corners = windowCornerClips(b, stageWin, eps);
      if (corners.length > 0) {
        issues.push({
          code: 'L06',
          ids: [b.id],
          message: `Ink clipped by Fixed Stage rounded corner (${corners.join(', ')})`,
        });
      }
    }
  }
  for (let i = 0; i < boxes.length; i += 1) {
    if (!validFlags[i]) continue;
    const a = boxes[i];
    if (a.chrome === true || a.layer === 'under') continue;
    for (let j = i + 1; j < boxes.length; j += 1) {
      if (!validFlags[j]) continue;
      const b = boxes[j];
      if (b.chrome === true || b.layer === 'under') continue;
      if (a.kind !== 'text' && b.kind !== 'text') continue;
      const ra = effectiveCollisionRect(a, b, stageWin, framedStage);
      const rb = effectiveCollisionRect(b, a, stageWin, framedStage);
      if (!ra || !rb) continue;
      const ox = Math.min(ra[2], rb[2]) - Math.max(ra[0], rb[0]);
      const oy = Math.min(ra[3], rb[3]) - Math.max(ra[1], rb[1]);
      if (ox >= minOverlap && oy >= minOverlap) {
        const isFaceOverlap = a.kind === 'face' || b.kind === 'face';
        issues.push({
          code: isFaceOverlap ? 'L03' : 'L02',
          ids: [a.id, b.id],
          message: isFaceOverlap ? 'Text overlaps protected presenter face box' : 'Overlapping protected ink/box',
        });
      }
    }
  }
  return issues;
}

type RawRect = {x: number; y: number; w: number; h: number};

function mergeSameLineRects(rawRects: RawRect[]): RawRect[] {
  if (rawRects.length <= 1) return rawRects;
  const sorted = [...rawRects].sort((a, b) => a.y - b.y || a.x - b.x);
  const lines: RawRect[] = [];
  for (const r of sorted) {
    const match = lines.find((ln) => {
      const overlapY = Math.min(ln.y + ln.h, r.y + r.h) - Math.max(ln.y, r.y);
      return overlapY >= 0.4 * Math.min(ln.h, r.h);
    });
    if (match) {
      const nx0 = Math.min(match.x, r.x);
      const ny0 = Math.min(match.y, r.y);
      const nx1 = Math.max(match.x + match.w, r.x + r.w);
      const ny1 = Math.max(match.y + match.h, r.y + r.h);
      match.x = nx0;
      match.y = ny0;
      match.w = nx1 - nx0;
      match.h = ny1 - ny0;
    } else {
      lines.push({...r});
    }
  }
  return lines;
}

/**
 * Extract the active Fixed Stage window `win(t)` from a Remotion DOM container if mounted.
 */
export function collectDomStageWindow(containerEl: HTMLElement): StageWindowBox | null {
  if (typeof document === 'undefined' || !containerEl) return null;
  const stageEl = containerEl.querySelector<HTMLElement>('[data-stage-win]');
  if (!stageEl) return null;
  const raw = stageEl.getAttribute('data-stage-win');
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw);
    if (
      parsed &&
      finite(parsed.x) &&
      finite(parsed.y) &&
      finite(parsed.w) &&
      finite(parsed.h) &&
      parsed.w > 0 &&
      parsed.h > 0
    ) {
      return {
        x: parsed.x,
        y: parsed.y,
        w: parsed.w,
        h: parsed.h,
        r: finite(parsed.r) ? parsed.r : 0,
      };
    }
  } catch {
    return null;
  }
  return null;
}

/**
 * Collect post-transform, post-line-wrap screen-space boxes from a Remotion DOM container
 * mapped back to canonical 1080×1920 design coordinates.
 */
export function collectDomLayoutBoxes(
  containerEl: HTMLElement,
  canvasSize: {width: number; height: number} = {width: BRAND.width, height: BRAND.height},
): LayoutBox[] {
  if (typeof document === 'undefined' || !containerEl) return [];
  const rootRect = containerEl.getBoundingClientRect();
  if (rootRect.width <= 0 || rootRect.height <= 0) return [];
  const sx = canvasSize.width / rootRect.width;
  const sy = canvasSize.height / rootRect.height;
  const boxes: LayoutBox[] = [];

  const nodes = containerEl.querySelectorAll<HTMLElement>('[data-medo-box]');
  nodes.forEach((el, elIdx) => {
    const kindAttr = el.getAttribute('data-medo-box');
    if (kindAttr !== 'text' && kindAttr !== 'face' && kindAttr !== 'keep') return;
    const opacity = Number(el.getAttribute('data-medo-opacity') ?? '1');
    if (!Number.isFinite(opacity) || opacity <= 0.01) return;

    const layerContainer = el.closest<HTMLElement>('[data-stage-layer]');
    const layerAttr = layerContainer?.getAttribute('data-stage-layer');
    const resolvedLayer: StageLayer | undefined =
      layerAttr === 'under' || layerAttr === 'content' || layerAttr === 'over'
        ? layerAttr
        : undefined;
    const isChrome = el.getAttribute('data-medo-chrome') === '1';

    const baseId = el.getAttribute('data-medo-id') || `${kindAttr}-${elIdx}`;
    if (kindAttr === 'keep' || kindAttr === 'face') {
      const r = el.getBoundingClientRect();
      const w = r.width * sx;
      const h = r.height * sy;
      if (w > 0.1 && h > 0.1) {
        const entry: LayoutBox = {
          id: baseId,
          kind: kindAttr,
          x: (r.left - rootRect.left) * sx,
          y: (r.top - rootRect.top) * sy,
          w,
          h,
        };
        if (resolvedLayer) entry.layer = resolvedLayer;
        if (isChrome) entry.chrome = true;
        boxes.push(entry);
      }
      return;
    }

    const zone = (el.getAttribute('data-medo-zone') || 'content') as LayoutZone;
    const fullText = (el.textContent || '').trim();
    if (!fullText) return;

    const rawRects: RawRect[] = [];
    const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
    let current = walker.nextNode();
    while (current) {
      if ((current.nodeValue || '').trim()) {
        const range = document.createRange();
        range.selectNodeContents(current);
        const rects = Array.from(range.getClientRects());
        for (const r of rects) {
          const w = r.width * sx;
          const h = r.height * sy;
          if (w > 0.25 && h > 0.25) {
            rawRects.push({
              x: (r.left - rootRect.left) * sx,
              y: (r.top - rootRect.top) * sy,
              w,
              h,
            });
          }
        }
      }
      current = walker.nextNode();
    }

    const lineBoxes = mergeSameLineRects(rawRects);
    const underline = el.querySelector<HTMLElement>('[data-medo-underline="1"]');
    if (underline && lineBoxes.length > 0) {
      const ur = underline.getBoundingClientRect();
      const uw = ur.width * sx;
      const uh = ur.height * sy;
      if (uw > 0.25 && uh > 0.25) {
        const last = lineBoxes[lineBoxes.length - 1];
        const ux = (ur.left - rootRect.left) * sx;
        const uy = (ur.top - rootRect.top) * sy;
        const nx0 = Math.min(last.x, ux);
        const ny0 = Math.min(last.y, uy);
        const nx1 = Math.max(last.x + last.w, ux + uw);
        const ny1 = Math.max(last.y + last.h, uy + uh);
        last.x = nx0;
        last.y = ny0;
        last.w = nx1 - nx0;
        last.h = ny1 - ny0;
      }
    }

    lineBoxes.forEach((lb, lineIdx) => {
      const entry: LayoutBox = {
        id: `${baseId}-${lineIdx}`,
        kind: 'text',
        zone,
        text: fullText,
        x: lb.x,
        y: lb.y,
        w: lb.w,
        h: lb.h,
      };
      if (resolvedLayer) entry.layer = resolvedLayer;
      boxes.push(entry);
    });
  });

  return boxes;
}

export type ProtectBoxProps = {
  id: string;
  kind?: 'keep' | 'face';
  chrome?: boolean;
  box: {x: number; y: number; w: number; h: number};
};

export const ProtectBox: React.FC<ProtectBoxProps> = ({id, kind = 'keep', chrome = false, box}) => {
  if (!finite(box.x) || !finite(box.y) || !finite(box.w) || !finite(box.h) || box.w <= 0 || box.h <= 0) {
    return null;
  }
  return (
    <div
      data-medo-box={kind}
      data-medo-id={id}
      data-medo-opacity="1"
      data-medo-chrome={chrome ? '1' : undefined}
      style={{
        position: 'absolute',
        left: box.x,
        top: box.y,
        width: box.w,
        height: box.h,
        pointerEvents: 'none',
      }}
    />
  );
};
