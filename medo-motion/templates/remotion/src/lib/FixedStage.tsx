import React, {useLayoutEffect, useMemo, useRef} from 'react';
import {AbsoluteFill} from 'remotion';
import {backgroundFrame} from './backgrounds.js';
import {DirectedText} from './DirectedText';
import {
  brandHex,
  clampRadius,
  normalizeStageSpec,
  stageStateAt,
} from './stage.js';

export type FixedStageState = ReturnType<typeof stageStateAt>;

export type FixedStageProps = {
  /** Validated or raw Fixed Stage specification (`plan/stage.json` contract). */
  spec: any;
  /** Authoritative VO timestamp in seconds (`frame / fps`). */
  time: number;
  /** Total VO duration in seconds (used for progress bar when enabled). */
  duration?: number | null;
  /** Agent-authored `plan/text-direction.json` (required when header slots are active). */
  direction?: any;
  /** Map of `copyId -> text` from `plan/copy.json` (required when header slots are active). */
  copyById?: Record<string, string>;
  /** Motion policy mode (`normal` | `reduced`). */
  motionMode?: 'normal' | 'reduced';
  /** Optional custom `UNDER` background layer additions. */
  under?: React.ReactNode | ((state: FixedStageState) => React.ReactNode);
  /** `CONTENT` layer: existing scene content and scene transitions, strictly clipped to `win(t)`. */
  children?: React.ReactNode | ((state: FixedStageState) => React.ReactNode);
  /** `OVER` layer: foreground overlays, subtitles/captions, HUD elements (never clipped by `win(t)`). */
  over?: React.ReactNode | ((state: FixedStageState) => React.ReactNode);
};

function withAlphaHex(hex: string, alpha: number): string {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return `rgba(${r},${g},${b},${alpha})`;
}

/**
 * Engine R (Remotion) Fixed Stage component.
 * Enforces strict three-layer compositing order:
 * 1. `UNDER` (persistent stage background + mat)
 * 2. `CONTENT` (scene content & transitions clipped via true CSS `clip-path: inset(... round r)`)
 * 3. `OVER` (optional `copy.json` + `text-direction.json` header, progress bar, captions, foreground overlays)
 */
export const FixedStage: React.FC<FixedStageProps> = ({
  spec,
  time,
  duration = null,
  direction = null,
  copyById = undefined,
  motionMode = 'normal',
  under,
  children,
  over,
}) => {
  if (motionMode !== 'normal' && motionMode !== 'reduced') {
    throw new Error('invalid motion mode');
  }
  const norm = useMemo(
    () => (spec && spec._normalized === true ? spec : normalizeStageSpec(spec)),
    [spec],
  );
  const state = stageStateAt(norm, time, {duration});
  const {w: cw, h: ch} = norm.canvas;
  const wb = state.win;
  const bgCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const ambTime = motionMode === 'reduced' ? 0 : state.time;

  useLayoutEffect(() => {
    if (state.isFullscreen || !norm.under.background) return;
    const canvas = bgCanvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    backgroundFrame(ctx, cw, ch, ambTime, norm.under.background);
  }, [ambTime, ch, cw, norm.under.background, state.isFullscreen]);

  const activeHeader = state.activeHeader;
  let headerText: string | null = null;
  if (activeHeader) {
    const lookedUp = copyById?.[activeHeader.copyId];
    if (typeof lookedUp !== 'string' || !lookedUp.trim()) {
      throw new Error(
        `Header slot "${activeHeader.id}" missing non-empty copyId "${activeHeader.copyId}" in copyById`,
      );
    }
    if (!direction) {
      throw new Error(`Header slot "${activeHeader.id}" requires plan/text-direction.json`);
    }
    headerText = lookedUp;
  }

  const clipRadius = clampRadius(wb.r, wb.w, wb.h);
  const clipTop = wb.y;
  const clipRight = Math.max(0, cw - (wb.x + wb.w));
  const clipBottom = Math.max(0, ch - (wb.y + wb.h));
  const clipLeft = wb.x;
  const contentClipPath = state.isFullscreen
    ? undefined
    : clipRadius > 0
      ? `inset(${clipTop}px ${clipRight}px ${clipBottom}px ${clipLeft}px round ${clipRadius}px)`
      : `inset(${clipTop}px ${clipRight}px ${clipBottom}px ${clipLeft}px)`;

  const frCfg = norm.under.frame;
  const pbCfg = norm.over.progressBar;

  return (
    <AbsoluteFill
      data-stage-id={norm.id}
      data-stage-mode={state.mode}
      data-stage-win={JSON.stringify(wb)}
      style={{
        width: cw,
        height: ch,
        overflow: 'hidden',
        backgroundColor: brandHex(norm.under.surfaceRole),
        direction: 'rtl',
      }}
    >
      {/* Layer 1: UNDER (persistent stage background & outer structural mat) */}
      {!state.isFullscreen && (
        <AbsoluteFill data-stage-layer="under" style={{zIndex: 1, pointerEvents: 'none'}}>
          {norm.under.background ? (
            <canvas
              ref={bgCanvasRef}
              width={cw}
              height={ch}
              style={{width: cw, height: ch, display: 'block'}}
            />
          ) : (
            <AbsoluteFill style={{backgroundColor: brandHex(norm.under.surfaceRole)}} />
          )}
          {frCfg.enabled && frCfg.matAlpha > 0 && state.chromeOpacity > 0 && (
            <div
              style={{
                position: 'absolute',
                left: wb.x - 8,
                top: wb.y + 10,
                width: wb.w + 16,
                height: wb.h + 4,
                borderRadius: clampRadius(wb.r + 4, wb.w + 16, wb.h + 4),
                backgroundColor: withAlphaHex(
                  brandHex(frCfg.matRole),
                  frCfg.matAlpha * state.chromeOpacity,
                ),
              }}
            />
          )}
          {typeof under === 'function' ? under(state) : under}
        </AbsoluteFill>
      )}

      {/* Layer 2: CONTENT (existing scene content & transitions, strictly clipped to win(t)) */}
      <AbsoluteFill
        data-stage-layer="content"
        style={{
          zIndex: 2,
          clipPath: contentClipPath,
          WebkitClipPath: contentClipPath,
        }}
      >
        {typeof children === 'function' ? children(state) : children}
      </AbsoluteFill>

      {/* Crisp window border stroke when framed */}
      {!state.isFullscreen && frCfg.enabled && frCfg.strokeWidth > 0 && state.chromeOpacity > 0.005 && (
        <div
          data-stage-chrome="frame"
          style={{
            position: 'absolute',
            left: wb.x,
            top: wb.y,
            width: wb.w,
            height: wb.h,
            borderRadius: clipRadius,
            border: `${frCfg.strokeWidth}px solid ${brandHex(frCfg.strokeRole)}`,
            opacity: state.chromeOpacity,
            boxSizing: 'border-box',
            pointerEvents: 'none',
            zIndex: 3,
          }}
        />
      )}

      {/* Layer 3: OVER (optional header, progress bar, subtitles/captions, foreground overlays — unclipped) */}
      <AbsoluteFill data-stage-layer="over" style={{zIndex: 4, pointerEvents: 'none'}}>
        {activeHeader && headerText && (
          <div
            style={{
              position: 'absolute',
              left: activeHeader.x,
              right: 'auto',
              top: activeHeader.y,
              width: 'max-content',
              transform: 'translate(-50%, -50%)',
              maxWidth: activeHeader.maxWidth + (activeHeader.pillRole ? 68 : 0),
              padding: activeHeader.pillRole ? '12px 34px' : 0,
              borderRadius: activeHeader.pillRole ? 999 : 0,
              backgroundColor: activeHeader.pillRole
                ? withAlphaHex(brandHex(activeHeader.pillRole), activeHeader.pillAlpha)
                : 'transparent',
              border:
                activeHeader.pillRole && activeHeader.pillBorderRole
                  ? `3px solid ${brandHex(activeHeader.pillBorderRole)}`
                  : undefined,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <DirectedText
              direction={direction}
              scene={activeHeader.scene}
              role={activeHeader.role}
              elementId={activeHeader.copyId}
              zone="hud"
              time={state.time}
              start={activeHeader.start}
              end={activeHeader.end}
              size={activeHeader.size}
              color={brandHex(activeHeader.colorRole)}
              accent={brandHex(activeHeader.accentRole)}
              theme={norm.theme}
              style={{
                fontSize: activeHeader.size,
                lineHeight: 1.9,
                textAlign: 'center',
                maxWidth: activeHeader.maxWidth,
                whiteSpace: 'pre-line',
              }}
            >
              {headerText}
            </DirectedText>
          </div>
        )}

        {duration !== null && duration !== undefined && pbCfg.enabled && (
          <div
            style={{
              position: 'absolute',
              left: pbCfg.marginX,
              right: pbCfg.marginX,
              top: pbCfg.y,
              height: pbCfg.height,
              borderRadius: pbCfg.height,
              backgroundColor: withAlphaHex(brandHex(pbCfg.trackRole), pbCfg.trackAlpha),
              overflow: 'hidden',
              direction: 'ltr',
            }}
          >
            <div
              style={{
                width: `${state.progress * 100}%`,
                height: '100%',
                backgroundColor: brandHex(pbCfg.fillRole),
              }}
            />
          </div>
        )}

        {typeof over === 'function' ? over(state) : over}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
