// Native studio Machine Explainer geometry, state, and Canvas2D helper (Phase 1).
// Zero external imports so engines K and R share this module byte for byte.
// Strictly uses the locked 12-colour Medo brand.json v2.6 palette (+ derived inkShadow).

const COS30 = 0.8660254037844386;
const SIN30 = 0.5;
const LAYER_RANK = Object.freeze({ back: 0, mid: 1, front: 2, overlay: 3 });

export const MACHINE_PALETTE = Object.freeze({
  red: '#CB271B',
  red_bright: '#CB0801',
  red_deep: '#9F0803',
  ink: '#0A0A0A',
  ink_soft: '#71717A',
  paper: '#F3F2F1',
  gray_1: '#D8D7D5',
  gray_2: '#C9C5C2',
  gray_3: '#BFBAB7',
  gray_4: '#A3A2A0',
  salmon: '#D97F68',
  blush: '#D5AEA6',
  inkShadow: '#030303',
});

export const MACHINE_ROLES = Object.freeze({
  dark: {
    substrate: { top: MACHINE_PALETTE.ink_soft, left: MACHINE_PALETTE.ink, right: MACHINE_PALETTE.inkShadow, stroke: MACHINE_PALETTE.gray_4 },
    housing: { top: MACHINE_PALETTE.gray_4, left: MACHINE_PALETTE.ink_soft, right: MACHINE_PALETTE.ink, stroke: MACHINE_PALETTE.paper },
    chip: { top: MACHINE_PALETTE.ink, left: MACHINE_PALETTE.inkShadow, right: MACHINE_PALETTE.inkShadow, stroke: MACHINE_PALETTE.gray_3 },
    contact: { top: MACHINE_PALETTE.blush, left: MACHINE_PALETTE.salmon, right: MACHINE_PALETTE.ink_soft, stroke: MACHINE_PALETTE.paper },
    intake: { top: MACHINE_PALETTE.paper, left: MACHINE_PALETTE.blush, right: MACHINE_PALETTE.gray_2, stroke: MACHINE_PALETTE.paper },
    active: { top: MACHINE_PALETTE.salmon, left: MACHINE_PALETTE.red, right: MACHINE_PALETTE.red_deep, stroke: MACHINE_PALETTE.paper },
    cutaway: { top: MACHINE_PALETTE.gray_3, left: MACHINE_PALETTE.ink_soft, right: MACHINE_PALETTE.ink, stroke: MACHINE_PALETTE.blush },
  },
  light: {
    substrate: { top: MACHINE_PALETTE.gray_2, left: MACHINE_PALETTE.gray_3, right: MACHINE_PALETTE.ink_soft, stroke: MACHINE_PALETTE.ink },
    housing: { top: MACHINE_PALETTE.paper, left: MACHINE_PALETTE.gray_1, right: MACHINE_PALETTE.gray_3, stroke: MACHINE_PALETTE.ink },
    chip: { top: MACHINE_PALETTE.ink_soft, left: MACHINE_PALETTE.ink, right: MACHINE_PALETTE.inkShadow, stroke: MACHINE_PALETTE.ink },
    contact: { top: MACHINE_PALETTE.blush, left: MACHINE_PALETTE.salmon, right: MACHINE_PALETTE.red_deep, stroke: MACHINE_PALETTE.ink },
    intake: { top: MACHINE_PALETTE.paper, left: MACHINE_PALETTE.blush, right: MACHINE_PALETTE.gray_2, stroke: MACHINE_PALETTE.ink },
    active: { top: MACHINE_PALETTE.red, left: MACHINE_PALETTE.red_deep, right: MACHINE_PALETTE.ink, stroke: MACHINE_PALETTE.ink },
    cutaway: { top: MACHINE_PALETTE.paper, left: MACHINE_PALETTE.gray_1, right: MACHINE_PALETTE.gray_2, stroke: MACHINE_PALETTE.ink_soft },
  },
});

export const ALLOWED_SOURCE_KINDS = Object.freeze([
  'spec', 'datasheet', 'manual', 'paper', 'standard', 'encyclopedia', 'user',
]);
export const ALLOWED_LOCATOR_KINDS = Object.freeze([
  'section', 'page', 'table', 'figure', 'clause', 'line',
]);
export const ALLOWED_MOTION_KINDS = Object.freeze([
  'packet_flow', 'heat_tint', 'spin', 'airflow_stream', 'pulse',
]);
export const SUPPORTED_ARCHETYPES = Object.freeze([
  'nvme_ssd', 'cpu_package', 'ram_dimm', 'cooling_system', 'custom',
]);

const finite = n => typeof n === 'number' && Number.isFinite(n);
const nonEmpty = s => typeof s === 'string' && s.trim().length > 0;
const clamp01 = v => Math.min(1, Math.max(0, v));
const easeOutCubic = x => {
  const u = clamp01(x);
  return 1 - ((1 - u) ** 3);
};
const round4 = v => Math.round(v * 1e4) / 1e4;

export function isoProjectPoint(x, y, z, { originX = 500, originY = 760, scale = 1.35 } = {}) {
  return [
    round4(originX + (x - y) * COS30 * scale),
    round4(originY + (x + y) * SIN30 * scale - z * scale),
    round4(x + y + z),
  ];
}

function buildNvmeSsd(params = {}) {
  const nandLayers = Number.isInteger(params.nandLayers) && params.nandLayers >= 2 ? params.nandLayers : 4;
  const cutawayAlpha = finite(params.cutawayAlpha) ? clamp01(params.cutawayAlpha) : 0.18;
  const parts = [
    {
      id: 'pcb', tag: 'pcb', layer: 'back', primitive: 'slab', role: 'substrate',
      x: -130, y: -44, z: 0, dx: 260, dy: 88, dz: 8, alpha: 1,
    },
    {
      id: 'm2_pins', tag: 'pcie_bus', layer: 'mid', primitive: 'ticks', role: 'contact',
      x: -128, y: -33, z: 8, count: 8, stepX: 0, stepY: 9, dx: 14, dy: 5, dz: 2, alpha: 1,
    },
  ];
  for (let lane = 0; lane < 4; lane += 1) {
    const ly = -22 + lane * 14;
    parts.push({
      id: `pcie_lane_${lane + 1}`,
      tag: 'pcie_bus',
      layer: 'mid',
      primitive: 'wire',
      role: 'intake',
      points: [[-114, ly, 9.5], [-82, ly * 0.75, 10], [-54, ly * 0.45, 12]],
      width: 3.2,
      alpha: 1,
    });
  }
  parts.push(
    {
      id: 'controller_pkg', tag: 'controller', layer: 'mid', primitive: 'slab', role: 'chip',
      x: -54, y: -24, z: 8, dx: 52, dy: 48, dz: 11, alpha: 1,
    },
    {
      id: 'controller_die', tag: 'controller', layer: 'mid', primitive: 'slab', role: 'contact',
      x: -43, y: -14, z: 19, dx: 30, dy: 28, dz: 3, alpha: 1,
    },
    {
      id: 'dram_cache', tag: 'dram_cache', layer: 'mid', primitive: 'slab', role: 'chip',
      x: -34, y: 26, z: 8, dx: 30, dy: 15, dz: 11, alpha: 1,
    },
    {
      id: 'dram_link', tag: 'dram_cache', layer: 'mid', primitive: 'wire', role: 'contact',
      points: [[-20, 22, 14], [-20, 26, 14]], width: 3.0, alpha: 1,
    },
    {
      id: 'nand_ch_0', tag: 'nand_channel', layer: 'mid', primitive: 'wire', role: 'intake',
      points: [[-2, 14, 9.5], [26, 18, 9.5], [52, 16, 10]], width: 3.4, alpha: 1,
    },
    {
      id: 'nand_ch_1', tag: 'nand_channel', layer: 'mid', primitive: 'wire', role: 'intake',
      points: [[-2, 24, 9.5], [26, 28, 9.5], [52, 26, 10]], width: 3.4, alpha: 1,
    },
    {
      id: 'nand_stack', tag: 'nand_stack', layer: 'mid', primitive: 'slab_stack', role: 'chip',
      x: 52, y: -24, z: 8, dx: 64, dy: 56, layerDz: 5, gapDz: 2, layers: nandLayers, alpha: 1,
    },
    {
      id: 'heatsink_rear_rail', tag: 'heatsink', layer: 'back', primitive: 'slab', role: 'housing',
      x: -116, y: -44, z: 8, dx: 238, dy: 8, dz: 28, alpha: 0.9,
    },
    {
      id: 'heatsink_cutaway_hood', tag: 'heatsink', layer: 'front', primitive: 'slab', role: 'cutaway',
      x: -116, y: -34, z: 38, dx: 238, dy: 74, dz: 4, alpha: cutawayAlpha, cutaway: true,
    },
  );
  const topNandZ = 8 + nandLayers * 7;
  return {
    parts,
    paths: {
      pcie_to_controller: [[-124, -4, 10], [-82, -2, 11], [-28, 0, 22]],
      controller_to_dram: [[-22, 12, 20], [-19, 33, 20]],
      controller_to_nand: [[-2, 18, 12], [26, 22, 12], [84, 4, topNandZ]],
      heat_rise: [[-28, 0, 24], [-28, -6, 48], [-28, -12, 74]],
    },
    world: {
      pcie_entry: [-120, 0, 10],
      controller_center: [-28, 0, 22],
      dram_center: [-19, 33, 19],
      nand_center: [84, 4, topNandZ],
      callout_anchor: [0, -56, 68],
    },
  };
}

function buildCpuPackage(params = {}) {
  const cutawayAlpha = finite(params.cutawayAlpha) ? clamp01(params.cutawayAlpha) : 0.18;
  const parts = [
    {
      id: 'substrate', tag: 'substrate', layer: 'back', primitive: 'slab', role: 'substrate',
      x: -95, y: -95, z: 0, dx: 190, dy: 190, dz: 10, alpha: 1,
    },
    {
      id: 'socket_pins_front', tag: 'socket_pins', layer: 'mid', primitive: 'ticks', role: 'contact',
      x: -76, y: 83, z: 10, count: 6, stepX: 28, stepY: 0, dx: 16, dy: 10, dz: 2.5, alpha: 1,
    },
    {
      id: 'core_0', tag: 'cores', layer: 'mid', primitive: 'slab', role: 'chip',
      x: -72, y: -70, z: 10, dx: 28, dy: 54, dz: 11, alpha: 1,
    },
    {
      id: 'core_1', tag: 'cores', layer: 'mid', primitive: 'slab', role: 'chip',
      x: -38, y: -70, z: 10, dx: 28, dy: 54, dz: 11, alpha: 1,
    },
    {
      id: 'core_2', tag: 'cores', layer: 'mid', primitive: 'slab', role: 'chip',
      x: -72, y: -6, z: 10, dx: 28, dy: 54, dz: 11, alpha: 1,
    },
    {
      id: 'core_3', tag: 'cores', layer: 'mid', primitive: 'slab', role: 'chip',
      x: -38, y: -6, z: 10, dx: 28, dy: 54, dz: 11, alpha: 1,
    },
    {
      id: 'l3_cache', tag: 'l3_cache', layer: 'mid', primitive: 'slab', role: 'contact',
      x: -2, y: -66, z: 10, dx: 26, dy: 118, dz: 12, alpha: 1,
    },
    {
      id: 'io_die', tag: 'io_die', layer: 'mid', primitive: 'slab', role: 'chip',
      x: 34, y: -52, z: 10, dx: 40, dy: 96, dz: 11, alpha: 1,
    },
    {
      id: 'fabric_bridge', tag: 'fabric', layer: 'mid', primitive: 'slab', role: 'contact',
      x: 18, y: 54, z: 10, dx: 28, dy: 18, dz: 9, alpha: 1,
    },
    {
      id: 'fabric_top', tag: 'fabric', layer: 'mid', primitive: 'wire', role: 'intake',
      points: [[-56, 60, 11.5], [18, 60, 14], [58, 58, 11.5]], width: 3.4, alpha: 1,
    },
    {
      id: 'fabric_bot', tag: 'fabric', layer: 'mid', primitive: 'wire', role: 'intake',
      points: [[-56, 70, 11.5], [32, 70, 14], [64, 68, 11.5]], width: 3.4, alpha: 1,
    },
    {
      id: 'ihs_rear_wall', tag: 'ihs', layer: 'back', primitive: 'slab', role: 'housing',
      x: -84, y: -84, z: 10, dx: 168, dy: 10, dz: 24, alpha: 0.9,
    },
    {
      id: 'ihs_cutaway_lid', tag: 'ihs', layer: 'front', primitive: 'slab', role: 'cutaway',
      x: -84, y: -74, z: 34, dx: 168, dy: 158, dz: 4, alpha: cutawayAlpha, cutaway: true,
    },
  ];
  return {
    parts,
    paths: {
      ring_to_cores: [[54, -12, 23], [11, -12, 23], [-52, -36, 23]],
      cores_to_cache: [[-52, 18, 23], [11, 18, 23]],
      cache_to_io: [[11, -24, 23], [54, -24, 23]],
      ihs_heat_spread: [[-38, -20, 24], [8, 0, 38], [42, 18, 44]],
    },
    world: {
      cores_center: [-40, -11, 21],
      l3_center: [11, -7, 22],
      io_center: [54, -4, 21],
      ihs_top: [0, 0, 38],
      callout_anchor: [0, -88, 66],
    },
  };
}

function buildRamDimm(params = {}) {
  const cutawayAlpha = finite(params.cutawayAlpha) ? clamp01(params.cutawayAlpha) : 0.16;
  const parts = [
    {
      id: 'dimm_pcb', tag: 'pcb', layer: 'back', primitive: 'slab', role: 'substrate',
      x: -146, y: -32, z: 0, dx: 292, dy: 64, dz: 7, alpha: 1,
    },
    {
      id: 'edge_pins_a', tag: 'bus_pins', layer: 'mid', primitive: 'ticks', role: 'contact',
      x: -136, y: 23, z: 7, count: 6, stepX: 20, stepY: 0, dx: 11, dy: 9, dz: 2.5, alpha: 1,
    },
    {
      id: 'edge_pins_b', tag: 'bus_pins', layer: 'mid', primitive: 'ticks', role: 'contact',
      x: 24, y: 23, z: 7, count: 6, stepX: 20, stepY: 0, dx: 11, dy: 9, dz: 2.5, alpha: 1,
    },
    {
      id: 'rcd_controller', tag: 'rcd_controller', layer: 'mid', primitive: 'slab', role: 'contact',
      x: -16, y: -18, z: 7, dx: 32, dy: 30, dz: 11, alpha: 1,
    },
    {
      id: 'dram_banks_a', tag: 'dram_banks', layer: 'mid', primitive: 'ticks', role: 'chip',
      x: -134, y: -20, z: 7, count: 4, stepX: 28, stepY: 0, dx: 20, dy: 28, dz: 9, alpha: 1,
    },
    {
      id: 'dram_banks_b', tag: 'dram_banks', layer: 'mid', primitive: 'ticks', role: 'chip',
      x: 28, y: -20, z: 7, count: 4, stepX: 28, stepY: 0, dx: 20, dy: 28, dz: 9, alpha: 1,
    },
    {
      id: 'channel_a_bus', tag: 'channel_bus', layer: 'mid', primitive: 'wire', role: 'intake',
      points: [[-16, 15, 9], [-72, 15, 9], [-124, 15, 9]], width: 3.4, alpha: 1,
    },
    {
      id: 'channel_b_bus', tag: 'channel_bus', layer: 'mid', primitive: 'wire', role: 'intake',
      points: [[16, 15, 9], [72, 15, 9], [124, 15, 9]], width: 3.4, alpha: 1,
    },
    {
      id: 'spreader_rear', tag: 'heatspreader', layer: 'back', primitive: 'slab', role: 'housing',
      x: -140, y: -32, z: 7, dx: 280, dy: 7, dz: 26, alpha: 0.9,
    },
    {
      id: 'spreader_cutaway', tag: 'heatspreader', layer: 'front', primitive: 'slab', role: 'cutaway',
      x: -140, y: -25, z: 32, dx: 280, dy: 55, dz: 3, alpha: cutawayAlpha, cutaway: true,
    },
  ];
  return {
    parts,
    paths: {
      channel_a: [[0, 15, 18], [-48, 15, 11], [-122, 6, 17]],
      channel_b: [[0, 15, 18], [48, 15, 11], [122, 6, 17]],
      pins_to_rcd: [[-10, 28, 10], [0, -2, 18]],
    },
    world: {
      rcd_center: [0, -3, 18],
      bank_a_center: [-82, -6, 16],
      bank_b_center: [80, -6, 16],
      callout_anchor: [0, -48, 62],
    },
  };
}

function buildCoolingSystem(params = {}) {
  const finLayers = Number.isInteger(params.finLayers) && params.finLayers >= 3 ? params.finLayers : 5;
  const cutawayAlpha = finite(params.cutawayAlpha) ? clamp01(params.cutawayAlpha) : 0.16;
  const parts = [
    {
      id: 'coldplate', tag: 'coldplate', layer: 'mid', primitive: 'slab', role: 'contact',
      x: -102, y: -32, z: 0, dx: 62, dy: 64, dz: 12, alpha: 1,
    },
    {
      id: 'heatpipe_front', tag: 'heatpipes', layer: 'mid', primitive: 'wire', role: 'active',
      points: [[-66, 26, 11], [-16, 36, 22], [44, 36, 46]], width: 5.0, alpha: 1,
    },
    {
      id: 'heatpipe_coil', tag: 'heatpipes', layer: 'mid', primitive: 'coil', role: 'active',
      x: -36, y: 36, z: 20, length: 34, radius: 6, turns: 4, axis: 'x', alpha: 1,
    },
    {
      id: 'fin_stack', tag: 'fin_stack', layer: 'mid', primitive: 'slab_stack', role: 'housing',
      x: 6, y: -38, z: 16, dx: 68, dy: 68, layerDz: 4, gapDz: 6, layers: finLayers, alpha: 1,
    },
    {
      id: 'fan', tag: 'fan', layer: 'mid', primitive: 'ring', role: 'chip',
      x: 118, y: 4, z: 20, rOuter: 38, rInner: 14, h: 16, blades: 7, segments: 24, alpha: 1,
    },
    {
      id: 'shroud_rear', tag: 'shroud', layer: 'back', primitive: 'slab', role: 'substrate',
      x: 0, y: -46, z: 12, dx: 158, dy: 8, dz: 52, alpha: 0.88,
    },
    {
      id: 'shroud_cutaway', tag: 'shroud', layer: 'front', primitive: 'slab', role: 'cutaway',
      x: 0, y: -38, z: 64, dx: 158, dy: 84, dz: 4, alpha: cutawayAlpha, cutaway: true,
    },
  ];
  return {
    parts,
    paths: {
      heatpipe_transfer: [[-70, 24, 12], [-16, 36, 24], [44, 34, 48]],
      intake_to_exhaust: [[148, 4, 36], [106, 4, 36], [42, 0, 38], [-18, 0, 42]],
    },
    world: {
      coldplate_center: [-71, 0, 12],
      fin_stack_center: [40, -4, 40],
      fan_axis: [118, 4, 28],
      callout_anchor: [18, -60, 82],
    },
  };
}

export function expandMachineModel(spec) {
  const arch = spec?.archetype || 'custom';
  const builders = {
    nvme_ssd: buildNvmeSsd,
    cpu_package: buildCpuPackage,
    ram_dimm: buildRamDimm,
    cooling_system: buildCoolingSystem,
  };
  if (builders[arch]) {
    const base = builders[arch](spec?.params || {});
    return {
      parts: Array.isArray(spec?.extraParts) ? [...base.parts, ...spec.extraParts] : base.parts,
      paths: { ...base.paths, ...(spec?.paths || {}) },
      world: { ...base.world, ...(spec?.world || {}) },
    };
  }
  if (arch === 'custom') {
    return {
      parts: Array.isArray(spec?.parts) ? spec.parts.map(p => ({ ...p })) : [],
      paths: { ...(spec?.paths || {}) },
      world: { ...(spec?.world || {}) },
    };
  }
  throw new Error(`Unsupported machine archetype: ${arch}`);
}

export function validateMachineSpec(spec, { fps = 30 } = {}) {
  const errors = [];
  if (!spec || typeof spec !== 'object') return ['machine spec must be an object'];
  if (spec.version !== 1) errors.push('machine spec version must be 1');
  if (!nonEmpty(spec.id)) errors.push('machine spec requires a non-empty id');
  if (!SUPPORTED_ARCHETYPES.includes(spec.archetype)) {
    errors.push(`unsupported archetype "${spec.archetype}"; expected one of ${SUPPORTED_ARCHETYPES.join(', ')}`);
  }
  if (!['vo', 'scene'].includes(spec.clock)) {
    errors.push('clock must be "vo" or "scene"');
  }
  if (spec.clock === 'vo' && (!Number.isInteger(spec.scene) || spec.scene < 1)) {
    errors.push('vo-clock machine spec requires a positive integer scene index');
  }
  if (!finite(spec.start) || !finite(spec.end) || spec.start < 0 || spec.end <= spec.start) {
    errors.push('machine spec requires finite 0 <= start < end');
  }

  const rw = spec.revealWindow;
  const expectedUnit = spec.clock === 'scene' ? 'scene_seconds' : 'vo_seconds';
  if (!rw || typeof rw !== 'object' || Array.isArray(rw)) {
    errors.push(`revealWindow must be an object {unit: "${expectedUnit}", start, end}`);
  } else {
    if (rw.unit !== expectedUnit) {
      errors.push(`revealWindow.unit must be "${expectedUnit}" when clock="${spec.clock}"`);
    }
    if (!finite(rw.start) || !finite(rw.end) || rw.start < spec.start - 1e-9 || rw.end <= rw.start || rw.end > spec.end + 1e-9) {
      errors.push('revealWindow requires finite bounds inside [spec.start, spec.end] with start < end');
    }
  }

  const sourceMap = new Map();
  if (!Array.isArray(spec.sources)) {
    errors.push('sources must be an array (may be empty only when all steps are illustrative)');
  } else {
    for (const src of spec.sources) {
      if (!src || !nonEmpty(src.id) || sourceMap.has(src.id)) {
        errors.push('each source needs a unique non-empty id');
        continue;
      }
      sourceMap.set(src.id, src);
      if (!nonEmpty(src.title) || src.title.trim().length < 3) {
        errors.push(`source "${src.id}": title must be at least 3 characters`);
      }
      if (!ALLOWED_SOURCE_KINDS.includes(src.kind)) {
        errors.push(`source "${src.id}": kind must be one of ${ALLOWED_SOURCE_KINDS.join(', ')}`);
      }
      if (!nonEmpty(src.ref) || src.ref.trim().length < 4) {
        errors.push(`source "${src.id}": ref must provide a verifiable URI, DOI, standard ID, or user brief reference`);
      }
    }
  }

  let model = { parts: [], paths: {}, world: {} };
  if (SUPPORTED_ARCHETYPES.includes(spec.archetype)) {
    model = expandMachineModel(spec);
    if (!model.parts.length) {
      errors.push('expanded machine model contains zero parts');
    }
  }
  const knownTags = new Set(model.parts.map(p => p.tag).filter(nonEmpty));

  if (!Array.isArray(spec.steps) || !spec.steps.length) {
    errors.push('steps must be a non-empty array');
    return errors;
  }

  const stepIds = new Set();
  for (const step of spec.steps) {
    if (!step || !nonEmpty(step.id) || stepIds.has(step.id)) {
      errors.push('each step requires a unique non-empty id');
      continue;
    }
    stepIds.add(step.id);
    if (!['source', 'user', 'illustrative'].includes(step.evidence)) {
      errors.push(`${step.id}: evidence must be "source", "user", or "illustrative"`);
    } else if (step.evidence === 'source' || step.evidence === 'user') {
      const src = sourceMap.get(step.sourceId);
      if (!src) {
        errors.push(`${step.id}: sourceId "${step.sourceId || ''}" is not declared in sources[]`);
      } else if (step.evidence === 'source' && src.kind === 'user') {
        errors.push(`${step.id}: evidence="source" cannot cite a source of kind="user"`);
      }
      const loc = step.locator;
      if (!loc || typeof loc !== 'object' || !ALLOWED_LOCATOR_KINDS.includes(loc.kind)
          || !nonEmpty(loc.value) || loc.value.trim().length < 2) {
        errors.push(
          `${step.id}: requires locator {kind: ${ALLOWED_LOCATOR_KINDS.join('|')}, value: "<specific section/page/clause>"}`,
        );
      }
      if (!nonEmpty(step.quote) || step.quote.trim().length < 10) {
        errors.push(`${step.id}: requires supporting quote/excerpt of at least 10 characters`);
      }
    } else if (step.evidence === 'illustrative') {
      if (!nonEmpty(step.illustrativeLabelId)
          || !Array.isArray(step.copyIds)
          || !step.copyIds.includes(step.illustrativeLabelId)) {
        errors.push(`${step.id}: illustrative evidence requires illustrativeLabelId included in copyIds`);
      }
    }

    if (!Array.isArray(step.copyIds) || !step.copyIds.length || step.copyIds.some(c => !nonEmpty(c))) {
      errors.push(`${step.id}: copyIds must be a non-empty list of copy.json fragment ids`);
    }
    if (!finite(step.start) || !finite(step.end)
        || step.start < spec.start - 1e-9 || step.end <= step.start || step.end > spec.end + 1e-9) {
      errors.push(`${step.id}: step start/end must be finite and within [spec.start, spec.end]`);
    }
    if (!['lead', 'sync', 'reveal'].includes(step.timing)) {
      errors.push(`${step.id}: timing must be "lead", "sync", or "reveal"`);
    } else if (step.timing === 'lead' && step.fact !== false) {
      errors.push(`${step.id}: lead timing is structure-only and requires fact=false`);
    }

    const anc = step.anchor;
    if (!anc || typeof anc !== 'object' || !Number.isInteger(anc.word) || anc.word < 0 || !nonEmpty(anc.text)) {
      errors.push(`${step.id}: anchor requires {word: non-negative int, text: non-empty string}`);
    } else if (finite(anc.wordStart) && finite(anc.wordEnd)) {
      const leadMax = 6 / Math.max(1, fps) + 1e-8;
      if (step.timing === 'lead' && !(anc.wordStart - step.start >= -1e-9 && anc.wordStart - step.start <= leadMax)) {
        errors.push(`${step.id}: lead may precede its word by at most 6 frames at ${fps}fps`);
      } else if (step.timing === 'sync' && Math.abs(step.start - anc.wordStart) > 1e-6) {
        errors.push(`${step.id}: sync must start exactly at anchor word start`);
      } else if (step.timing === 'reveal' && step.start < anc.wordStart - 1e-9) {
        errors.push(`${step.id}: reveal cannot appear before its anchor word`);
      }
      if (step.end < anc.wordEnd - 1e-9) {
        errors.push(`${step.id}: step must survive through the end of its anchor word`);
      }
    }

    if (!Array.isArray(step.activeTags) || !step.activeTags.length || step.activeTags.some(t => !nonEmpty(t))) {
      errors.push(`${step.id}: activeTags must name at least one part tag`);
    } else if (knownTags.size > 0) {
      for (const tag of step.activeTags) {
        if (!knownTags.has(tag)) {
          errors.push(`${step.id}: activeTag "${tag}" does not match any part in archetype "${spec.archetype}"`);
        }
      }
    }

    const mot = step.motion;
    if (!mot || typeof mot !== 'object' || !ALLOWED_MOTION_KINDS.includes(mot.kind)) {
      errors.push(`${step.id}: motion.kind must be one of ${ALLOWED_MOTION_KINDS.join(', ')}`);
    } else if ((mot.kind === 'packet_flow' || mot.kind === 'airflow_stream')
        && nonEmpty(mot.path) && Object.keys(model.paths).length > 0 && !model.paths[mot.path]) {
      errors.push(`${step.id}: motion.path "${mot.path}" is not defined in machine paths`);
    }
  }

  return errors;
}

export function toSceneLocalMachine(spec, sceneStart = 0) {
  if (!spec || typeof spec !== 'object') throw new Error('machine spec must be an object');
  if (spec.clock === 'scene') return structuredClone ? structuredClone(spec) : JSON.parse(JSON.stringify(spec));
  const offset = Number(sceneStart) || 0;
  return {
    ...spec,
    clock: 'scene',
    start: round4(spec.start - offset),
    end: round4(spec.end - offset),
    revealWindow: {
      unit: 'scene_seconds',
      start: round4(spec.revealWindow.start - offset),
      end: round4(spec.revealWindow.end - offset),
    },
    steps: spec.steps.map(st => ({
      ...st,
      start: round4(st.start - offset),
      end: round4(st.end - offset),
      anchor: {
        ...st.anchor,
        ...(finite(st.anchor?.wordStart) ? { wordStart: round4(st.anchor.wordStart - offset) } : {}),
        ...(finite(st.anchor?.wordEnd) ? { wordEnd: round4(st.anchor.wordEnd - offset) } : {}),
      },
    })),
  };
}

export function machineStateAt(spec, time, { fps = 30 } = {}) {
  const errs = validateMachineSpec(spec, { fps });
  if (errs.length) throw new Error(errs.join('; '));
  if (!finite(time)) throw new Error('time must be finite');

  const active = time >= spec.start && time < spec.end;
  const rwSpan = Math.max(1e-6, spec.revealWindow.end - spec.revealWindow.start);
  const revealProgress = active ? easeOutCubic((time - spec.revealWindow.start) / rwSpan) : 0;

  let activeStep = null;
  if (active) {
    for (const st of spec.steps) {
      if (time >= st.start && time < st.end) activeStep = st;
    }
  }

  let stepProgress = 0;
  let highlightMix = 0;
  let spinDeg = 18;
  let packetProgress = -1;
  let airflowPhase = -1;
  let pulseBoost = 0;

  if (activeStep) {
    const elapsed = Math.max(0, time - activeStep.start);
    const dur = Math.max(1e-6, activeStep.end - activeStep.start);
    stepProgress = round4(clamp01(elapsed / dur));
    highlightMix = round4(easeOutCubic(elapsed / Math.min(0.24, dur * 0.5)));
    const mot = activeStep.motion;
    const rate = finite(mot.rate) && mot.rate > 0 ? mot.rate : 1.25;
    if (mot.kind === 'spin') {
      const rpm = finite(mot.rpm) && mot.rpm > 0 ? mot.rpm : 180;
      spinDeg = round4((18 + elapsed * rpm * 6) % 360);
    } else if (mot.kind === 'packet_flow') {
      packetProgress = round4((elapsed * rate) % 1);
    } else if (mot.kind === 'airflow_stream') {
      airflowPhase = round4((elapsed * rate) % 1);
      const rpm = finite(mot.rpm) && mot.rpm > 0 ? mot.rpm : 180;
      spinDeg = round4((18 + elapsed * rpm * 6) % 360);
    } else if (mot.kind === 'pulse' || mot.kind === 'heat_tint') {
      pulseBoost = round4(0.5 + 0.5 * Math.sin(elapsed * Math.PI * 4));
    }
  }

  return {
    id: spec.id,
    active,
    revealProgress: round4(revealProgress),
    activeStepId: activeStep ? activeStep.id : null,
    activeStep,
    activeTags: activeStep ? [...activeStep.activeTags] : [],
    stepProgress,
    highlightMix,
    spinDeg,
    packetProgress,
    airflowPhase,
    pulseBoost,
  };
}

function polylineLength2d(pts) {
  let len = 0;
  for (let i = 1; i < pts.length; i += 1) {
    len += Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]);
  }
  return len;
}

export function pointAlongPolyline2d(pts, p) {
  if (!pts.length) return [0, 0];
  if (pts.length === 1) return pts[0];
  let budget = polylineLength2d(pts) * clamp01(p);
  for (let i = 1; i < pts.length; i += 1) {
    const a = pts[i - 1];
    const b = pts[i];
    const seg = Math.hypot(b[0] - a[0], b[1] - a[1]);
    if (budget <= seg || i === pts.length - 1) {
      const f = seg > 1e-6 ? clamp01(budget / seg) : 0;
      return [round4(a[0] + (b[0] - a[0]) * f), round4(a[1] + (b[1] - a[1]) * f)];
    }
    budget -= seg;
  }
  return pts[pts.length - 1];
}

export function partialPolyline2d(pts, progress, close = false) {
  const closed = close && pts.length > 2 ? [...pts, pts[0]] : pts;
  const p = clamp01(progress);
  if (closed.length < 2 || p <= 0.002) return [];
  if (p >= 0.999) return closed;
  let budget = polylineLength2d(closed) * p;
  const out = [closed[0]];
  for (let i = 1; i < closed.length && budget > 0; i += 1) {
    const a = closed[i - 1];
    const b = closed[i];
    const seg = Math.hypot(b[0] - a[0], b[1] - a[1]);
    if (seg <= 1e-6) continue;
    if (budget >= seg) {
      out.push(b);
      budget -= seg;
    } else {
      const f = budget / seg;
      out.push([round4(a[0] + (b[0] - a[0]) * f), round4(a[1] + (b[1] - a[1]) * f)]);
      budget = 0;
    }
  }
  return out;
}

function normalizePrimitives(parts) {
  const flat = [];
  for (const part of parts) {
    if (part.primitive === 'slab_stack') {
      const layers = Math.max(1, part.layers || 1);
      const stepZ = (part.layerDz || 5) + (part.gapDz || 2);
      for (let i = 0; i < layers; i += 1) {
        flat.push({
          ...part,
          id: `${part.id}_L${i + 1}`,
          parentPartId: part.id,
          primitive: 'slab',
          z: part.z + i * stepZ,
          dz: part.layerDz || 5,
        });
      }
    } else if (part.primitive === 'ticks') {
      const count = Math.max(1, part.count || 1);
      for (let i = 0; i < count; i += 1) {
        flat.push({
          ...part,
          id: `${part.id}_${i + 1}`,
          parentPartId: part.id,
          primitive: 'slab',
          x: part.x + i * (part.stepX || 0),
          y: part.y + i * (part.stepY || 0),
        });
      }
    } else {
      flat.push({ ...part, parentPartId: part.id });
    }
  }
  return flat;
}

/**
 * @param {any} spec
 * @param {number} time
 * @param {{ originX?: number, originY?: number, scale?: number, theme?: 'dark' | 'light' | string, lineWidth?: number, fps?: number, forceFullReveal?: boolean }} [opts]
 */
export function buildMachineScene(spec, time, opts = {}) {
  const {
    originX,
    originY,
    scale,
    theme = 'dark',
    lineWidth = 2.6,
    fps = 30,
    forceFullReveal = false,
  } = opts || {};
  const state = machineStateAt(spec, time, { fps });
  const layoutCfg = spec.layout || {};
  const ox = finite(originX) ? originX : (finite(layoutCfg.originX) ? layoutCfg.originX : 500);
  const oy = finite(originY) ? originY : (finite(layoutCfg.originY) ? layoutCfg.originY : 760);
  const sc = finite(scale) ? scale : (finite(layoutCfg.scale) ? layoutCfg.scale : 1.35);
  const th = theme === 'light' ? 'light' : 'dark';
  const roles = MACHINE_ROLES[th];
  const proj = (x, y, z) => isoProjectPoint(x, y, z, { originX: ox, originY: oy, scale: sc });

  const model = expandMachineModel(spec);
  const flatParts = normalizePrimitives(model.parts);
  const rev = forceFullReveal ? 1 : state.revealProgress;
  const activeTagSet = new Set(state.activeTags);
  const activeTintName = state.activeStep?.motion?.tint === 'intake' ? 'intake' : 'active';

  const ops = [];
  const allVertices = [];
  const pushVerts = pts => {
    for (const pt of pts) allVertices.push([pt[0], pt[1]]);
  };

  flatParts.forEach((part, seq) => {
    const baseAlpha = finite(part.alpha) ? clamp01(part.alpha) : 1;
    if (baseAlpha <= 0 || rev <= 0) return;
    const isHighlighted = activeTagSet.has(part.tag) && !part.cutaway;
    const c = roles[isHighlighted ? activeTintName : (part.role || 'housing')] || roles.housing;
    const layerRank = LAYER_RANK[part.layer] ?? 1;
    const fillRamp = clamp01((rev - 0.22) / 0.78);
    const fillAlpha = round4(baseAlpha * fillRamp);

    if (part.primitive === 'slab') {
      const { x, y, z, dx, dy, dz } = part;
      const p100 = proj(x + dx, y, z);
      const p010 = proj(x, y + dy, z);
      const p110 = proj(x + dx, y + dy, z);
      const p001 = proj(x, y, z + dz);
      const p101 = proj(x + dx, y, z + dz);
      const p011 = proj(x, y + dy, z + dz);
      const p111 = proj(x + dx, y + dy, z + dz);
      const leftF = [[p010[0], p010[1]], [p110[0], p110[1]], [p111[0], p111[1]], [p011[0], p011[1]]];
      const rightF = [[p100[0], p100[1]], [p110[0], p110[1]], [p111[0], p111[1]], [p101[0], p101[1]]];
      const topF = [[p001[0], p001[1]], [p101[0], p101[1]], [p111[0], p111[1]], [p011[0], p011[1]]];
      pushVerts([...leftF, ...rightF, ...topF]);
      ops.push({
        kind: 'solid',
        partId: part.id,
        parentPartId: part.parentPartId,
        tag: part.tag || '',
        layer: part.layer || 'mid',
        layerRank,
        depth: round4(x + dx * 0.5 + y + dy * 0.5 + z + dz * 0.5),
        seq,
        cutaway: Boolean(part.cutaway),
        fillAlpha,
        strokeAlpha: baseAlpha,
        lineWidth: isHighlighted ? lineWidth * 1.25 : lineWidth,
        reveal: rev,
        faces: [
          { points: leftF, fill: c.left, stroke: c.stroke, close: true },
          { points: rightF, fill: c.right, stroke: c.stroke, close: true },
          { points: topF, fill: c.top, stroke: c.stroke, close: true },
        ],
      });
    } else if (part.primitive === 'poly3d' && Array.isArray(part.faces3d)) {
      let cx = 0; let cy = 0; let cz = 0; let cnt = 0;
      const faces = part.faces3d.map((f3, fi) => {
        const pts2 = f3.map(([vx, vy, vz]) => {
          cx += vx; cy += vy; cz += vz; cnt += 1;
          const p = proj(vx, vy, vz);
          return [p[0], p[1]];
        });
        pushVerts(pts2);
        return {
          points: pts2,
          fill: fi === 0 ? c.top : (fi % 2 === 1 ? c.left : c.right),
          stroke: c.stroke,
          close: true,
        };
      });
      if (faces.length) {
        ops.push({
          kind: 'solid',
          partId: part.id,
          parentPartId: part.parentPartId,
          tag: part.tag || '',
          layer: part.layer || 'mid',
          layerRank,
          depth: cnt ? round4((cx + cy + cz) / cnt) : 0,
          seq,
          cutaway: Boolean(part.cutaway),
          fillAlpha,
          strokeAlpha: baseAlpha,
          lineWidth,
          reveal: rev,
          faces,
        });
      }
    } else if (part.primitive === 'cylinder' || part.primitive === 'ring') {
      const segs = Math.max(12, part.segments || 24);
      const rOuter = part.primitive === 'ring' ? (part.rOuter || 52) : (part.r || 32);
      const h = part.h || 20;
      const topPts = [];
      const botPts = [];
      for (let i = 0; i < segs; i += 1) {
        const ang = (i / segs) * Math.PI * 2;
        const px = part.x + Math.cos(ang) * rOuter;
        const py = part.y + Math.sin(ang) * rOuter;
        const tp = proj(px, py, part.z + h);
        const bp = proj(px, py, part.z);
        topPts.push([tp[0], tp[1]]);
        botPts.push([bp[0], bp[1]]);
      }
      let minI = 0;
      let maxI = 0;
      for (let i = 1; i < segs; i += 1) {
        if (topPts[i][0] < topPts[minI][0]) minI = i;
        if (topPts[i][0] > topPts[maxI][0]) maxI = i;
      }
      const frontArc = [];
      let cur = minI;
      while (frontArc.length <= segs) {
        frontArc.push(botPts[cur]);
        if (cur === maxI) break;
        cur = (cur + 1) % segs;
      }
      const sidePoly = [topPts[minI], ...frontArc, topPts[maxI]];
      pushVerts([...sidePoly, ...topPts]);
      const faces = [
        { points: sidePoly, fill: c.left, stroke: c.stroke, close: false },
        { points: topPts, fill: c.top, stroke: c.stroke, close: true },
      ];
      const bladeLines = [];
      if (part.primitive === 'ring' && (part.blades || 0) > 0) {
        const rIn = part.rInner || rOuter * 0.36;
        const spinRad = ((isHighlighted ? state.spinDeg : 18) * Math.PI) / 180;
        for (let b = 0; b < part.blades; b += 1) {
          const ang = spinRad + (b / part.blades) * Math.PI * 2;
          const p0 = proj(part.x + Math.cos(ang) * rIn, part.y + Math.sin(ang) * rIn, part.z + h);
          const p1 = proj(
            part.x + Math.cos(ang + 0.28) * (rOuter * 0.88),
            part.y + Math.sin(ang + 0.28) * (rOuter * 0.88),
            part.z + h,
          );
          bladeLines.push([[p0[0], p0[1]], [p1[0], p1[1]]]);
        }
      }
      ops.push({
        kind: 'solid',
        partId: part.id,
        parentPartId: part.parentPartId,
        tag: part.tag || '',
        layer: part.layer || 'mid',
        layerRank,
        depth: round4(part.x + part.y + part.z + h * 0.5),
        seq,
        cutaway: Boolean(part.cutaway),
        fillAlpha,
        strokeAlpha: baseAlpha,
        lineWidth,
        reveal: rev,
        faces,
        bladeLines,
        bladeStroke: roles.active.top,
      });
    } else if (part.primitive === 'wire' || part.primitive === 'coil') {
      let pts3d = part.points || [];
      if (part.primitive === 'coil') {
        const turns = Math.max(2, part.turns || 6);
        const steps = turns * 12;
        const len = part.length || 120;
        const rad = part.radius || 12;
        const axis = part.axis || 'x';
        pts3d = [];
        for (let i = 0; i <= steps; i += 1) {
          const u = i / steps;
          const ang = u * turns * Math.PI * 2;
          const along = u * len;
          const c1 = Math.cos(ang) * rad;
          const c2 = Math.sin(ang) * rad;
          pts3d.push([
            axis === 'x' ? part.x + along : part.x + c1,
            axis === 'y' ? part.y + along : (axis === 'x' ? part.y + c1 : part.y + c2),
            axis === 'z' ? part.z + along : part.z + c2,
          ]);
        }
      }
      if (pts3d.length >= 2) {
        const pts2d = pts3d.map(([px, py, pz]) => {
          const p = proj(px, py, pz);
          return [p[0], p[1]];
        });
        pushVerts(pts2d);
        const avgDepth = pts3d.reduce((acc, p) => acc + p[0] + p[1] + p[2], 0) / pts3d.length;
        ops.push({
          kind: 'wire',
          partId: part.id,
          parentPartId: part.parentPartId,
          tag: part.tag || '',
          layer: part.layer || 'mid',
          layerRank,
          depth: round4(avgDepth),
          seq,
          stroke: c.top,
          strokeAlpha: baseAlpha,
          lineWidth: (part.width || 3.2) * (isHighlighted ? 1.25 : 1),
          reveal: rev,
          points: pts2d,
        });
      }
    }
  });

  // Overlay step motion (rendered AFTER `front` cutaway so packets/airflow are never obscured)
  if (state.activeStep && rev > 0.25) {
    const mot = state.activeStep.motion;
    if (mot.kind === 'packet_flow' && mot.path && model.paths[mot.path] && state.packetProgress >= 0) {
      const path2d = model.paths[mot.path].map(([px, py, pz]) => {
        const p = proj(px, py, pz);
        return [p[0], p[1]];
      });
      pushVerts(path2d);
      const packetOffsets = [0, 0.33, 0.66];
      const dots = packetOffsets.map(off => pointAlongPolyline2d(path2d, (state.packetProgress + off) % 1));
      ops.push({
        kind: 'packets',
        partId: `${state.activeStep.id}_packets`,
        tag: state.activeStep.activeTags[0] || '',
        layer: 'overlay',
        layerRank: LAYER_RANK.overlay,
        depth: 1e6,
        seq: flatParts.length + 1,
        path: path2d,
        dots,
        radius: 6,
        fill: mot.tint === 'intake' ? MACHINE_PALETTE.paper : MACHINE_PALETTE.salmon,
        stroke: th === 'dark' ? MACHINE_PALETTE.ink : MACHINE_PALETTE.paper,
        alpha: state.highlightMix,
      });
    } else if (mot.kind === 'airflow_stream' && mot.path && model.paths[mot.path] && state.airflowPhase >= 0) {
      const base3d = model.paths[mot.path];
      const offsets = [-14, 0, 14];
      const streams = offsets.map((dyOff, si) => {
        const pts2d = base3d.map(([px, py, pz]) => {
          const p = proj(px, py + dyOff, pz);
          return [p[0], p[1]];
        });
        pushVerts(pts2d);
        const bead = pointAlongPolyline2d(pts2d, (state.airflowPhase + si * 0.28) % 1);
        return { points: pts2d, bead };
      });
      ops.push({
        kind: 'airflow',
        partId: `${state.activeStep.id}_airflow`,
        tag: state.activeStep.activeTags[0] || '',
        layer: 'overlay',
        layerRank: LAYER_RANK.overlay,
        depth: 1e6 + 1,
        seq: flatParts.length + 2,
        streams,
        stroke: mot.tint === 'active' ? MACHINE_PALETTE.salmon : MACHINE_PALETTE.blush,
        beadFill: MACHINE_PALETTE.paper,
        alpha: state.highlightMix,
      });
    }
  }

  ops.sort((a, b) => (a.layerRank - b.layerRank) || (a.depth - b.depth) || (a.seq - b.seq));

  let bounds = { x: ox, y: oy, w: 0, h: 0 };
  if (allVertices.length) {
    let minX = Infinity; let minY = Infinity; let maxX = -Infinity; let maxY = -Infinity;
    for (const [vx, vy] of allVertices) {
      if (vx < minX) minX = vx;
      if (vy < minY) minY = vy;
      if (vx > maxX) maxX = vx;
      if (vy > maxY) maxY = vy;
    }
    bounds = {
      x: round4(minX),
      y: round4(minY),
      w: round4(Math.max(1, maxX - minX)),
      h: round4(Math.max(1, maxY - minY)),
    };
  }

  const worldProjected = {};
  for (const [key, coords] of Object.entries(model.world)) {
    if (Array.isArray(coords) && coords.length === 3) {
      const p = proj(coords[0], coords[1], coords[2]);
      worldProjected[key] = { x: p[0], y: p[1], depth: p[2] };
    }
  }

  return {
    state,
    theme: th,
    origin: { x: ox, y: oy, scale: sc },
    ops,
    bounds,
    vertices: allVertices,
    world: worldProjected,
  };
}

export function drawMachineGeometry(ctx, sceneGraph) {
  if (!sceneGraph?.state?.active) return sceneGraph;
  for (const op of sceneGraph.ops) {
    if (op.kind === 'solid') {
      for (const face of op.faces) {
        if (op.fillAlpha > 0.004 && face.points.length >= 3) {
          ctx.save();
          ctx.globalAlpha *= op.fillAlpha;
          ctx.fillStyle = face.fill;
          ctx.beginPath();
          ctx.moveTo(face.points[0][0], face.points[0][1]);
          for (let i = 1; i < face.points.length; i += 1) {
            ctx.lineTo(face.points[i][0], face.points[i][1]);
          }
          ctx.closePath();
          ctx.fill();
          ctx.restore();
        }
        const strokePts = partialPolyline2d(face.points, op.reveal, face.close);
        if (strokePts.length >= 2 && op.strokeAlpha > 0.004) {
          ctx.save();
          ctx.globalAlpha *= op.strokeAlpha;
          ctx.strokeStyle = face.stroke;
          ctx.lineWidth = op.lineWidth;
          ctx.lineJoin = 'round';
          ctx.lineCap = 'round';
          if (op.cutaway) ctx.setLineDash([8, 6]);
          ctx.beginPath();
          ctx.moveTo(strokePts[0][0], strokePts[0][1]);
          for (let i = 1; i < strokePts.length; i += 1) {
            ctx.lineTo(strokePts[i][0], strokePts[i][1]);
          }
          ctx.stroke();
          ctx.restore();
        }
      }
      if (op.bladeLines?.length && op.reveal > 0.25) {
        ctx.save();
        ctx.globalAlpha *= op.strokeAlpha * op.reveal;
        ctx.strokeStyle = op.bladeStroke;
        ctx.lineWidth = op.lineWidth * 1.15;
        ctx.lineCap = 'round';
        for (const [[x0, y0], [x1, y1]] of op.bladeLines) {
          ctx.beginPath();
          ctx.moveTo(x0, y0);
          ctx.lineTo(x1, y1);
          ctx.stroke();
        }
        ctx.restore();
      }
    } else if (op.kind === 'wire') {
      const strokePts = partialPolyline2d(op.points, op.reveal, false);
      if (strokePts.length >= 2 && op.strokeAlpha > 0.004) {
        ctx.save();
        ctx.globalAlpha *= op.strokeAlpha;
        ctx.strokeStyle = op.stroke;
        ctx.lineWidth = op.lineWidth;
        ctx.lineJoin = 'round';
        ctx.lineCap = 'round';
        ctx.beginPath();
        ctx.moveTo(strokePts[0][0], strokePts[0][1]);
        for (let i = 1; i < strokePts.length; i += 1) {
          ctx.lineTo(strokePts[i][0], strokePts[i][1]);
        }
        ctx.stroke();
        ctx.restore();
      }
    } else if (op.kind === 'packets' && op.alpha > 0.004) {
      ctx.save();
      ctx.globalAlpha *= op.alpha;
      for (const [dx, dy] of op.dots) {
        ctx.fillStyle = op.fill;
        ctx.strokeStyle = op.stroke;
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(dx, dy, op.radius, 0, Math.PI * 2);
        ctx.fill();
        ctx.stroke();
      }
      ctx.restore();
    } else if (op.kind === 'airflow' && op.alpha > 0.004) {
      ctx.save();
      ctx.globalAlpha *= op.alpha;
      for (const stream of op.streams) {
        ctx.strokeStyle = op.stroke;
        ctx.lineWidth = 2.4;
        ctx.setLineDash([10, 8]);
        ctx.beginPath();
        ctx.moveTo(stream.points[0][0], stream.points[0][1]);
        for (let i = 1; i < stream.points.length; i += 1) {
          ctx.lineTo(stream.points[i][0], stream.points[i][1]);
        }
        ctx.stroke();
        ctx.setLineDash([]);
        ctx.fillStyle = op.beadFill;
        ctx.beginPath();
        ctx.arc(stream.bead[0], stream.bead[1], 4.5, 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.restore();
    }
  }
  return sceneGraph;
}
