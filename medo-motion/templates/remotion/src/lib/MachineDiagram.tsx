import React from 'react';
import {buildMachineScene, partialPolyline2d} from './machine-kit.js';
import {DirectedText} from './DirectedText';
import {BRAND, PALETTE} from '../brand';

export type MachineDiagramProps = {
  spec: any;
  time: number;
  direction?: any;
  scene?: number;
  copyById?: Record<string, string>;
  originX?: number;
  originY?: number;
  scale?: number;
  theme?: 'dark' | 'light';
  calloutY?: number;
  noteY?: number;
};

const ptsAttr = (pts: number[][]) => pts.map(([x, y]) => `${x},${y}`).join(' ');

/**
 * Engine R (Remotion) Machine Explainer renderer.
 * Consumes the exact deterministic scene graph from `machine-kit.js` (byte-identical to K)
 * and renders crisp SVG faces/strokes plus `DirectedText` callouts.
 */
export const MachineDiagram: React.FC<MachineDiagramProps> = ({
  spec,
  time,
  direction,
  scene,
  copyById = {},
  originX,
  originY,
  scale,
  theme = 'dark',
  calloutY,
  noteY,
}) => {
  const graph = buildMachineScene(spec, time, {
    originX,
    originY,
    scale,
    theme,
    fps: BRAND.fps,
  });
  if (!graph.state.active) return null;

  const svgNodes: React.ReactNode[] = [];
  graph.ops.forEach((op: any, idx: number) => {
    if (op.kind === 'solid') {
      op.faces.forEach((face: any, fi: number) => {
        if (op.fillAlpha > 0.004 && face.points.length >= 3) {
          svgNodes.push(
            <polygon
              key={`f-${idx}-${fi}`}
              points={ptsAttr(face.points)}
              fill={face.fill}
              fillOpacity={op.fillAlpha}
            />,
          );
        }
        const strokePts = partialPolyline2d(face.points, op.reveal, face.close);
        if (strokePts.length >= 2 && op.strokeAlpha > 0.004) {
          svgNodes.push(
            <polyline
              key={`s-${idx}-${fi}`}
              points={ptsAttr(strokePts)}
              fill="none"
              stroke={face.stroke}
              strokeOpacity={op.strokeAlpha}
              strokeWidth={op.lineWidth}
              strokeLinejoin="round"
              strokeLinecap="round"
              strokeDasharray={op.cutaway ? '8 6' : undefined}
            />,
          );
        }
      });
      if (op.bladeLines?.length && op.reveal > 0.25) {
        op.bladeLines.forEach((seg: number[][], bi: number) => {
          svgNodes.push(
            <line
              key={`b-${idx}-${bi}`}
              x1={seg[0][0]}
              y1={seg[0][1]}
              x2={seg[1][0]}
              y2={seg[1][1]}
              stroke={op.bladeStroke}
              strokeOpacity={op.strokeAlpha * op.reveal}
              strokeWidth={op.lineWidth * 1.15}
              strokeLinecap="round"
            />,
          );
        });
      }
    } else if (op.kind === 'wire') {
      const strokePts = partialPolyline2d(op.points, op.reveal, false);
      if (strokePts.length >= 2 && op.strokeAlpha > 0.004) {
        svgNodes.push(
          <polyline
            key={`w-${idx}`}
            points={ptsAttr(strokePts)}
            fill="none"
            stroke={op.stroke}
            strokeOpacity={op.strokeAlpha}
            strokeWidth={op.lineWidth}
            strokeLinejoin="round"
            strokeLinecap="round"
          />,
        );
      }
    } else if (op.kind === 'packets' && op.alpha > 0.004) {
      op.dots.forEach((dot: number[], di: number) => {
        svgNodes.push(
          <circle
            key={`p-${idx}-${di}`}
            cx={dot[0]}
            cy={dot[1]}
            r={op.radius}
            fill={op.fill}
            stroke={op.stroke}
            strokeWidth={2}
            opacity={op.alpha}
          />,
        );
      });
    } else if (op.kind === 'airflow' && op.alpha > 0.004) {
      op.streams.forEach((stream: any, si: number) => {
        svgNodes.push(
          <g key={`af-${idx}-${si}`} opacity={op.alpha}>
            <polyline
              points={ptsAttr(stream.points)}
              fill="none"
              stroke={op.stroke}
              strokeWidth={2.4}
              strokeDasharray="10 8"
            />
            <circle cx={stream.bead[0]} cy={stream.bead[1]} r={4.5} fill={op.beadFill} />
          </g>,
        );
      });
    }
  });

  const activeStep = graph.state.activeStep;
  const contentMinY = BRAND.contentY[0];
  const contentMaxY = BRAND.contentY[1];
  const margin = BRAND.margin;
  const boxWidth = BRAND.width - margin * 2;
  const resolvedCalloutY = typeof calloutY === 'number'
    ? calloutY
    : Math.min(contentMaxY - 90, Math.max(contentMinY + 60, graph.bounds.y + graph.bounds.h + 62));
  const resolvedNoteY = typeof noteY === 'number'
    ? noteY
    : Math.max(contentMinY + 24, graph.bounds.y - 84);

  const primaryId = activeStep?.copyIds?.[0];
  const primaryText = primaryId ? copyById[primaryId] : undefined;
  const noteId = activeStep?.evidence === 'illustrative' ? activeStep?.illustrativeLabelId : undefined;
  const noteText = noteId ? copyById[noteId] : undefined;

  return (
    <div style={{position: 'absolute', inset: 0, width: BRAND.width, height: BRAND.height, pointerEvents: 'none'}}>
      <svg width={BRAND.width} height={BRAND.height} style={{position: 'absolute', inset: 0}}>
        {svgNodes}
      </svg>
      {activeStep && direction && typeof scene === 'number' && primaryText && (
        <DirectedText
          direction={direction}
          scene={scene}
          role="label"
          elementId={primaryId}
          time={time}
          start={activeStep.start}
          end={activeStep.end}
          size={46}
          color={theme === 'light' ? PALETTE.ink : PALETTE.paper}
          theme={theme}
          style={{
            position: 'absolute',
            left: margin,
            top: resolvedCalloutY,
            width: boxWidth,
            textAlign: 'center',
            fontSize: 46,
          }}
        >
          {primaryText}
        </DirectedText>
      )}
      {activeStep && direction && typeof scene === 'number' && noteId && noteText && (
        <DirectedText
          direction={direction}
          scene={scene}
          role="label"
          elementId={noteId}
          time={time}
          start={activeStep.start}
          end={activeStep.end}
          size={38}
          color={theme === 'light' ? PALETTE.redDeep : PALETTE.salmon}
          theme={theme}
          style={{
            position: 'absolute',
            left: margin,
            top: resolvedNoteY,
            width: boxWidth,
            textAlign: 'center',
            fontSize: 38,
          }}
        >
          {noteText}
        </DirectedText>
      )}
    </div>
  );
};
