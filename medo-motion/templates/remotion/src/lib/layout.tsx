import React from 'react';
import {BRAND} from '../brand';

export type LayoutZone = 'content' | 'caption' | 'hud';
export type LayoutBoxKind = 'text' | 'face' | 'keep';

export type LayoutBox = {
  id: string;
  kind: LayoutBoxKind;
  zone?: LayoutZone;
  text?: string;
  x: number;
  y: number;
  w: number;
  h: number;
};

export type LayoutIssue = {
  code: 'L00' | 'L01' | 'L02' | 'L03' | 'L04';
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
  {minOverlap = 2, checkPlatformUi = false}: {minOverlap?: number; checkPlatformUi?: boolean} = {},
): LayoutIssue[] {
  if (!Array.isArray(boxes)) throw new Error('Layout capture is missing');
  const issues: LayoutIssue[] = [];
  for (const b of boxes) {
    if (
      !b ||
      typeof b.id !== 'string' ||
      !b.id.trim() ||
      !['text', 'face', 'keep'].includes(b.kind) ||
      !finite(b.x) ||
      !finite(b.y) ||
      !finite(b.w) ||
      !finite(b.h) ||
      b.w <= 0 ||
      b.h <= 0
    ) {
      issues.push({code: 'L00', ids: [b?.id || '?'], message: 'Invalid registered box'});
      continue;
    }
    if (b.kind !== 'text') continue;
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
  }
  for (let i = 0; i < boxes.length; i += 1) {
    for (let j = i + 1; j < boxes.length; j += 1) {
      const a = boxes[i];
      const b = boxes[j];
      if (!a || !b || (a.kind !== 'text' && b.kind !== 'text')) continue;
      const ox = Math.min(a.x + a.w, b.x + b.w) - Math.max(a.x, b.x);
      const oy = Math.min(a.y + a.h, b.y + b.h) - Math.max(a.y, b.y);
      if (ox >= minOverlap && oy >= minOverlap) {
        issues.push({
          code: a.kind === 'face' || b.kind === 'face' ? 'L03' : 'L02',
          ids: [a.id, b.id],
          message: 'Overlapping protected ink/box',
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

    const baseId = el.getAttribute('data-medo-id') || `${kindAttr}-${elIdx}`;
    if (kindAttr === 'keep' || kindAttr === 'face') {
      const r = el.getBoundingClientRect();
      const w = r.width * sx;
      const h = r.height * sy;
      if (w > 0.1 && h > 0.1) {
        boxes.push({
          id: baseId,
          kind: kindAttr,
          x: (r.left - rootRect.left) * sx,
          y: (r.top - rootRect.top) * sy,
          w,
          h,
        });
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
      boxes.push({
        id: `${baseId}-${lineIdx}`,
        kind: 'text',
        zone,
        text: fullText,
        x: lb.x,
        y: lb.y,
        w: lb.w,
        h: lb.h,
      });
    });
  });

  return boxes;
}

export type ProtectBoxProps = {
  id: string;
  kind?: 'keep' | 'face';
  box: {x: number; y: number; w: number; h: number};
};

export const ProtectBox: React.FC<ProtectBoxProps> = ({id, kind = 'keep', box}) => {
  if (!finite(box.x) || !finite(box.y) || !finite(box.w) || !finite(box.h) || box.w <= 0 || box.h <= 0) {
    return null;
  }
  return (
    <div
      data-medo-box={kind}
      data-medo-id={id}
      data-medo-opacity="1"
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
