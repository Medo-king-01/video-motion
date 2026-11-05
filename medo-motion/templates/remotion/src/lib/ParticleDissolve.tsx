import React, {useEffect, useRef, useState} from 'react';
import {cancelRender, continueRender, delayRender} from 'remotion';
import {particleDissolve} from './effects.js';

export type ParticleDissolveProps = {
  source: string;
  time: number;
  width: number;
  height: number;
  start?: number;
  duration?: number;
  count?: number;
  seed?: number;
  background?: string;
};

/** Canvas renderer that samples source pixels once and paints deterministic fading particles. */
export const ParticleDissolve: React.FC<ParticleDissolveProps> = ({
  source, time, width, height, start = 0, duration = 0.72,
  count = 96, seed = 18, background,
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [pixels, setPixels] = useState<ImageData | null>(null);
  const [loadHandle] = useState(() => delayRender('Loading Particle Dissolve source'));

  // Remotion must wait for the source pixels; otherwise rendered frames can be captured blank.
  useEffect(() => {
    setPixels(null);
    if (!(width > 0) || !(height > 0)) {
      continueRender(loadHandle);
      return;
    }
    let active = true;
    const image = new Image();
    image.crossOrigin = 'anonymous';
    image.onload = () => {
      if (!active) return;
      try {
        const sourceCanvas = document.createElement('canvas');
        sourceCanvas.width = width;
        sourceCanvas.height = height;
        const sourceCtx = sourceCanvas.getContext('2d', {willReadFrequently: true});
        if (!sourceCtx) throw new Error('Particle Dissolve could not create a source canvas context');
        sourceCtx.drawImage(image, 0, 0, width, height);
        const sampledPixels = sourceCtx.getImageData(0, 0, width, height);
        setPixels(sampledPixels);
        continueRender(loadHandle);
      } catch (error) {
        cancelRender(error instanceof Error
          ? error
          : new Error('Particle Dissolve could not sample its source image; check image CORS permissions'));
      }
    };
    image.onerror = () => {
      if (active) cancelRender(new Error(`Particle Dissolve failed to load source image: ${source}`));
    };
    image.src = source;
    return () => {
      active = false;
      image.onload = null;
      image.onerror = null;
    };
  }, [source, width, height, loadHandle]);

  // Repaint from cached source pixels for every arbitrary-time frame request.
  useEffect(() => {
    const output = canvasRef.current;
    if (!output || !(width > 0) || !(height > 0)) return;
    output.width = width;
    output.height = height;
    const ctx = output.getContext('2d');
    if (!ctx) return;
    ctx.clearRect(0, 0, width, height);
    if (background) {
      ctx.fillStyle = background;
      ctx.fillRect(0, 0, width, height);
    }
    if (!pixels) return;

    const state = particleDissolve(time, start, duration, count, seed);
    for (const particle of state.particles) {
      const alpha = Math.max(0, Math.min(1, particle.alpha));
      if (alpha <= 0) continue;
      const sx = Math.max(0, Math.min(width - 1, Math.floor(particle.x * width)));
      const sy = Math.max(0, Math.min(height - 1, Math.floor(particle.y * height)));
      const offset = (sy * width + sx) * 4;
      const a = pixels.data[offset + 3] / 255 * alpha;
      if (a <= 0) continue;
      ctx.globalAlpha = a;
      ctx.fillStyle = `rgb(${pixels.data[offset]}, ${pixels.data[offset + 1]}, ${pixels.data[offset + 2]})`;
      ctx.beginPath();
      ctx.arc(particle.x * width, particle.y * height,
        Math.max(1, particle.radius * width), 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.globalAlpha = 1;
  }, [pixels, time, width, height, start, duration, count, seed, background]);

  return (
    <canvas
      ref={canvasRef}
      width={width}
      height={height}
      data-motion-effect="particle-dissolve"
      style={{width: '100%', height: '100%', display: 'block'}}
    />
  );
};
