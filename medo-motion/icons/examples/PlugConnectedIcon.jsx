// itshover-style React icon, vendored so the pipeline has a working example of that component shape.
// Same 24-grid paths as icons/registry.json → svg/plug-connected.svg → lib/icons.js → icons.py.
// Colours stay palette v2: stroke = currentColor (ink or paper), LED = var(--icon-accent) (red or salmon).
//
// Usage:  <PlugConnectedIcon size={128} className="reel-icon reel-icon--on-dark" />
// Needs `motion` (framer-motion's package name since v11): npm i motion
"use client";

import { forwardRef, useEffect, useImperativeHandle, useRef } from "react";
import { motion, useAnimate } from "motion/react";

const PlugConnectedIcon = forwardRef(function PlugConnectedIcon(
  { onMouseEnter, onMouseLeave, className, size = 128, duration = 1, color, accent, ...props },
  ref,
) {
  const [scope, animate] = useAnimate();
  const hovered = useRef(false);

  const play = () =>
    animate([
      ["[data-part=body]", { pathLength: 0, opacity: 0 }, { duration: 0 }],
      ["[data-part=body]", { pathLength: 1, opacity: 1 }, { duration: duration * 0.55, ease: "easeInOut" }],
      ["[data-part=cord]", { pathLength: 0, opacity: 0 }, { duration: 0 }],
      ["[data-part=cord]", { pathLength: 1, opacity: 1 }, { duration: duration * 0.3, ease: "easeOut" }],
      ["[data-part=led]", { scale: 0.2, opacity: 0.2 }, { duration: 0 }],
      ["[data-part=led]", { scale: 1, opacity: 1 }, { duration: duration * 0.2, at: "<" }],
    ]);

  useEffect(() => {
    play();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useImperativeHandle(ref, () => ({
    startAnimation: play,
    stopAnimation: () => animate("[data-part]", { pathLength: 1, opacity: 1 }, { duration: 0 }),
  }));

  const handleEnter = (event) => {
    if (hovered.current) return;
    hovered.current = true;
    animate("[data-part=led]", { scale: [1, 1.35, 1] }, { duration: duration * 0.6, repeat: Infinity, repeatDelay: 0.4 });
    onMouseEnter?.(event);
  };
  const handleLeave = (event) => {
    hovered.current = false;
    animate("[data-part=led]", { scale: 1 }, { duration: 0.2 });
    onMouseLeave?.(event);
  };

  return (
    <motion.svg
      ref={scope}
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      width={size}
      height={size}
      fill="none"
      stroke={color ?? "currentColor"}
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      style={{ "--icon-accent": accent ?? "var(--icon-red, #CB271B)" }}
      onMouseEnter={handleEnter}
      onMouseLeave={handleLeave}
      {...props}
    >
      <title>متصل</title>
      <g data-part="body">
        <motion.line x1="9" y1="2" x2="9" y2="6" />
        <motion.line x1="15" y1="2" x2="15" y2="6" />
        <motion.rect x="6" y="6" width="12" height="8" rx="2.4" />
      </g>
      <motion.line data-part="cord" x1="12" y1="14" x2="12" y2="18.4" />
      <motion.circle data-part="led" cx="12" cy="21" r="1.3" fill="var(--icon-accent)" stroke="none" />
    </motion.svg>
  );
});

export default PlugConnectedIcon;
