// The composition canvas. The brand default is 1080×1920 at 30 fps — the design space every scene is
// laid out in. tools/canvas_engines.py may replace this file for one project with a device downscale of
// that same space (540×960 at 15 fps, for instance); a reshape or an upscale is refused there by name.
export const DESIGN = {width: 1080, height: 1920} as const;

export const CANVAS = {width: 1080, height: 1920, scale: 1, fps: 30} as const;
