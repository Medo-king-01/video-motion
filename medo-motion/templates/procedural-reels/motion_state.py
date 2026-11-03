"""Original offline physics/state adapters; JSON specs match motion-state.js in K/R."""
from __future__ import annotations

import copy
import math
from decimal import Context, Decimal, ROUND_HALF_UP

from motion_plan import compile_sequence, mix_value


def _finite(x):
    try:
        return type(x) in (int, float) and math.isfinite(x)
    except OverflowError:
        return False


def _number(x, name):
    if not _finite(x):
        raise ValueError(f'{name} must be finite')
    return x


def _positive(x, name):
    _number(x, name)
    if x <= 0:
        raise ValueError(f'{name} must be positive')
    return x


def _state(value, velocity):
    return {'value': _number(value, 'value'), 'velocity': _number(velocity, 'velocity')}


def _physics(options):
    if not isinstance(options, dict):
        raise ValueError('physics must be an object')
    stiffness, damping, mass = options.get('stiffness', 100), options.get('damping', 18), options.get('mass', 1)
    _positive(stiffness, 'stiffness'); _positive(mass, 'mass'); _number(damping, 'damping')
    w = math.sqrt(stiffness / mass)
    if not _finite(w) or not 1e-6 <= w <= 1e6: raise ValueError('unsupported spring conditioning')
    z = (damping / mass) / (2*w)
    if damping < 0 or not _finite(w) or not _finite(z) or not 1e-6 <= w <= 1e6 or z > 1e4:
        raise ValueError('unsupported spring conditioning')
    return {'stiffness': stiffness, 'damping': damping, 'mass': mass, 'w': w, 'z': z}


def spring_state(start, target, elapsed, options=None):
    options = {} if options is None else options
    for x in (start, target, elapsed): _number(x, 'spring input')
    params = _physics(options); w, z = params['w'], params['z']
    v = _number(options.get('velocity', 0), 'velocity')
    if elapsed < 0: return _state(start, 0)
    if elapsed == 0: return _state(start, v)
    _number(w*elapsed, 'spring phase')
    a, t = _number(start-target, 'displacement'), elapsed
    if z < 1 - 1e-7:
        d = w * math.sqrt(1 - z*z); b = (v + z*w*a)/d
        e, c, s = math.exp(-z*w*t), math.cos(d*t), math.sin(d*t)
        x = e*(a*c + b*s); velocity = e*((-z*w*a + b*d)*c + (-z*w*b - a*d)*s)
    elif z > 1 + 1e-7:
        q = z + math.sqrt(z*z - 1); r1, r2 = -w/q, -w*q
        c = (v - r2*a)/(r1-r2); d = a-c
        x = c*math.exp(r1*t) + d*math.exp(r2*t)
        velocity = r1*c*math.exp(r1*t) + r2*d*math.exp(r2*t)
    else:
        b, e = v+w*a, math.exp(-w*t)
        x = (a+b*t)*e; velocity = (b-w*(a+b*t))*e
    return _state(target+x, velocity)


def duration_spring(start, target, elapsed, options):
    duration, bounce, velocity = options.get('duration'), options.get('bounce', .2), options.get('velocity', 0)
    _positive(duration, 'duration'); _number(bounce, 'bounce')
    if not 0 <= bounce <= .8: raise ValueError('bounce must be between 0 and .8')
    z = 1-bounce; w = 8/(z*duration)
    params = {'stiffness': w*w, 'damping': 2*z*w, 'velocity': velocity}
    _number(elapsed, 'time'); spring_state(start, target, 0, params)
    last = spring_state(start, target, duration, params)
    if elapsed < 0: return _state(start, 0)
    if elapsed >= duration: return _state(target, 0)
    current = spring_state(start, target, elapsed, params)
    p = elapsed/duration; h, g = 3*p*p-2*p*p*p, p*p*p-p*p
    return _state(current['value']-(last['value']-target)*h-last['velocity']*duration*g,
                  current['velocity']-(last['value']-target)*(6*p-6*p*p)/duration-last['velocity']*(3*p*p-2*p))


class _Sampler:
    def __init__(self, sample, **metadata):
        self._sample = sample
        self.__dict__.update(metadata)

    def at(self, time):
        _number(time, 'time')
        return self._sample(time)


def compile_inertia(spec):
    if not isinstance(spec, dict): raise ValueError('inertia requires an object')
    start, velocity = spec.get('from'), spec.get('velocity')
    tau, decay, settle = spec.get('timeConstant', .35), spec.get('decayDuration', .6), spec.get('settleDuration', .3)
    lo, hi, snap = spec.get('min'), spec.get('max'), spec.get('snap')
    _number(start, 'from'); _number(velocity, 'velocity')
    for x, name in ((tau, 'timeConstant'), (decay, 'decayDuration'), (settle, 'settleDuration')): _positive(x, name)
    if lo is not None: _number(lo, 'min')
    if hi is not None: _number(hi, 'max')
    if (lo is not None and start < lo) or (hi is not None and start > hi) or (lo is not None and hi is not None and lo >= hi):
        raise ValueError('invalid inertia bounds/initial value')

    def bound(s):
        if lo is not None and (s['value'] < lo or (s['value'] == lo and s['velocity'] < 0)): return _state(lo, 0)
        if hi is not None and (s['value'] > hi or (s['value'] == hi and s['velocity'] > 0)): return _state(hi, 0)
        return s

    target = bound(_state(_number(start+velocity*tau, 'projected target'), 0))['value']
    if snap is not None:
        if not isinstance(snap, list) or not snap or any(not _finite(x) or (lo is not None and x < lo) or (hi is not None and x > hi) for x in snap):
            raise ValueError('snap points must be finite and within bounds')
        target = min(snap, key=lambda x: (abs(x-target), x))

    def free(t): return bound(_state(start+velocity*tau*(-math.expm1(-t/tau)), velocity*math.exp(-t/tau)))
    landing, duration = free(decay), _number(decay+settle, 'duration')
    params = {'duration': settle, 'bounce': 0, 'velocity': landing['velocity']}
    duration_spring(landing['value'], target, 0, params)

    def sample(t):
        s = _state(target, 0) if t >= duration else _state(start, 0) if t < 0 else free(t) if t < decay else bound(duration_spring(landing['value'], target, t-decay, params))
        return {**s, 'target': target, 'done': t >= duration}
    return _Sampler(sample, duration=duration, target=target)


def compile_retarget(spec):
    if not isinstance(spec, dict) or type(spec.get('version')) is not int or spec['version'] != 1 or not isinstance(spec.get('events'), list):
        raise ValueError('retarget requires version=1/events')
    initial, velocity = _number(spec.get('initial'), 'initial'), _number(spec.get('velocity', 0), 'velocity')
    params = _physics(spec.get('physics', {}))
    segments = [{'at': 0, 'from': initial, 'target': initial, 'velocity': velocity}]; previous = -1
    for event in spec['events']:
        if not isinstance(event, dict) or not _finite(event.get('at')) or event['at'] < 0 or event['at'] <= previous:
            raise ValueError('events must have strictly increasing nonnegative times')
        target = _number(event.get('target'), 'target'); last = segments[-1]
        s = spring_state(last['from'], last['target'], event['at']-last['at'], {**params, 'velocity': last['velocity']})
        segments.append({'at': event['at'], 'from': s['value'], 'target': target, 'velocity': s['velocity']}); previous = event['at']

    def sample(t):
        if t < 0: return {**_state(initial, 0), 'target': initial}
        segment = segments[0]
        for s in segments:
            if s['at'] > t: break
            segment = s
        return {**spring_state(segment['from'], segment['target'], t-segment['at'], {**params, 'velocity': segment['velocity']}), 'target': segment['target']}
    return _Sampler(sample)


def compile_follow(spec):
    if not isinstance(spec, dict) or not isinstance(spec.get('events'), list): raise ValueError('follow requires an event log')
    lag = _number(spec.get('lag', 0), 'lag')
    if lag < 0: raise ValueError('lag must be nonnegative')
    events = []
    for e in spec['events']:
        if not isinstance(e, dict) or not _finite(e.get('at')) or e['at'] < 0: raise ValueError('invalid target event')
        events.append({**e, 'at': _number(e['at']+lag, 'delayed time')})
    return compile_retarget({**spec, 'events': events})


def compile_variants(spec):
    if not isinstance(spec, dict) or type(spec.get('version')) is not int or spec['version'] != 1 or not isinstance(spec.get('root'), dict) or not isinstance(spec.get('events'), list):
        raise ValueError('variants require version=1/root/events')
    nodes, ids, initial, last, clips = [], set(), {}, {}, []

    def visit(node, inherited, depth):
        if depth > 32 or len(nodes) >= 256 or not isinstance(node, dict) or not isinstance(node.get('id'), str) or not node['id'].strip() or node['id'] in ids:
            raise ValueError('invalid/duplicate variant node')
        ids.add(node['id']); nodes.append(node)
        label = node.get('initial', inherited); variants = node.get('variants')
        if not isinstance(label, str) or not isinstance(variants, dict) or not isinstance(variants.get(label), dict):
            raise ValueError('node requires an initial variant')
        base = variants[label]; mix_value(base, base, 0)
        for value in variants.values():
            if not isinstance(value, dict): raise ValueError('variant state must be an object')
            mix_value(base, value, .5)
        initial[node['id']], last[node['id']] = copy.deepcopy(base), copy.deepcopy(base)
        if not isinstance(node.get('children', []), list): raise ValueError('children must be an array')
        for child in node.get('children', []): visit(child, label, depth+1)

    root = copy.deepcopy(spec['root']); visit(root, None, 0); end = 0
    for index, event in enumerate(spec['events']):
        if not isinstance(event, dict) or not _finite(event.get('at')) or event['at'] < end-1e-12 or not isinstance(event.get('label'), str):
            raise ValueError('variant events must follow the previous transition')
        duration = _positive(event.get('duration'), 'duration'); stagger = _number(event.get('stagger', 0), 'stagger'); order = event.get('order', 'together')
        if stagger < 0 or order not in ('together', 'beforeChildren', 'afterChildren'): raise ValueError('invalid variant orchestration')

        def schedule(node, start):
            children = node.get('children', []); own, finish = start, start+duration
            child_start = finish if order == 'beforeChildren' else start
            for i, child in enumerate(children): finish = max(finish, schedule(child, child_start+i*stagger))
            if order == 'afterChildren' and children: own = finish; finish = own+duration
            target = node['variants'].get(event['label'])
            if not isinstance(target, dict): raise ValueError('missing variant')
            clips.append({'id': f'{index}:{node["id"]}', 'track': node['id'], 'at': own, 'duration': duration, 'from': last[node['id']], 'to': target, 'easing': event.get('easing', 'linear')})
            last[node['id']] = target
            return _number(finish, 'variant end')
        end = schedule(root, max(event['at'], end))
    sequence = compile_sequence({'version': 1, 'clips': clips}) if clips else None
    return _Sampler(lambda t: sequence.at(t) if sequence else copy.deepcopy(initial), duration=end)


def compile_values(spec):
    if not isinstance(spec, dict) or type(spec.get('version')) is not int or spec['version'] != 1 or not isinstance(spec.get('nodes'), list) or len(spec['nodes']) > 128:
        raise ValueError('values require version=1/nodes (max 128)')
    constants = copy.deepcopy(spec.get('constants', {}))
    if not isinstance(constants, dict): raise ValueError('constants must be an object')
    for v in constants.values(): mix_value(v, v, 0)
    sequence = compile_sequence(spec['sequence']) if spec.get('sequence') else None
    source_order = list(constants)
    for k in sequence.at(0) if sequence else []:
        if k in constants: raise ValueError('duplicate source')
        source_order.append(k)
    sources, nodes, dependencies = set(source_order), {}, {}
    for raw in spec['nodes']:
        n = copy.deepcopy(raw)
        if not isinstance(n, dict) or not isinstance(n.get('id'), str) or not n['id'].strip() or n['id'] in sources or n['id'] in nodes:
            raise ValueError('invalid/duplicate value id')
        op = n.get('op')
        if op in ('map', 'mix', 'velocity'):
            refs = [n.get('input')]
            if op == 'map':
                r, out = n.get('range'), n.get('output')
                if not isinstance(r, list) or len(r) != 2 or not all(_finite(x) for x in r) or r[0] == r[1] or not isinstance(out, list) or len(out) != 2 or ('clamp' in n and not isinstance(n['clamp'], bool)):
                    raise ValueError('invalid map')
                _number(r[1]-r[0], 'map range span'); mix_value(*out, .5)
            if op == 'mix': mix_value(n.get('from'), n.get('to'), .5)
            if op == 'velocity':
                if _positive(n.get('step', 1/600), 'step') > 1: raise ValueError('velocity step must be <=1 second')
        elif op in ('add', 'multiply'):
            refs = n.get('inputs')
            if not isinstance(refs, list) or not refs: raise ValueError('arithmetic needs inputs')
        elif op == 'template':
            digits = n.get('digits', 3)
            if type(digits) is not int or not 0 <= digits <= 6: raise ValueError('template digits must be 0..6')
            parts = n.get('parts')
            if not isinstance(parts, list) or not all(isinstance(p, str) or (isinstance(p, dict) and isinstance(p.get('input'), str)) for p in parts):
                raise ValueError('invalid template')
            refs = [p['input'] for p in parts if isinstance(p, dict)]
        else: raise ValueError('unknown value operation')
        if not all(isinstance(r, str) for r in refs): raise ValueError('references must be strings')
        nodes[n['id']], dependencies[n['id']] = n, refs
    visiting, done = set(), {}

    def check(key):
        if key in sources: return False
        if key not in nodes or key in visiting: raise ValueError('missing reference or cyclic value graph')
        if key in done: return done[key]
        visiting.add(key); upstream = any([check(r) for r in dependencies[key]]); own = nodes[key]['op'] == 'velocity'
        if own and upstream: raise ValueError('nested velocity derivatives are unsupported')
        visiting.remove(key); done[key] = own or upstream
        return done[key]
    for key in nodes: check(key)

    def sample(t):
        memo, samples = {}, {}

        def value(key, time):
            cache_key = (key, time)
            if cache_key in memo: return memo[cache_key]
            if time not in samples: samples[time] = {**constants, **(sequence.at(time) if sequence else {})}
            if key in sources: return samples[time][key]
            n = nodes[key]; op = n['op']
            def read(ref): return value(ref, time)
            if op == 'velocity':
                h = n.get('step', 1/600)
                out = (_number(value(n['input'], time+h), 'velocity input')-_number(value(n['input'], time-h), 'velocity input'))/(2*h)
            elif op == 'map':
                p = (_number(read(n['input']), 'map input')-n['range'][0])/(n['range'][1]-n['range'][0])
                if n.get('clamp', True): p = max(0, min(1, p))
                out = mix_value(*n['output'], p)
            elif op == 'mix': out = mix_value(n['from'], n['to'], _number(read(n['input']), 'mix input'))
            elif op == 'add': out = sum(_number(read(r), 'add input') for r in n['inputs'])
            elif op == 'multiply': out = math.prod(_number(read(r), 'multiply input') for r in n['inputs'])
            else:
                parts = []
                for part in n['parts']:
                    if isinstance(part, str): parts.append(part); continue
                    v = read(part['input'])
                    if isinstance(v, str): parts.append(v); continue
                    _number(v, 'template reference')
                    if abs(v) >= 1e21: raise ValueError('template number too large')
                    rounded = Decimal.from_float(float(v)).quantize(Decimal((0, (1,), -n.get('digits', 3))),
                        context=Context(prec=40, rounding=ROUND_HALF_UP, traps=[]))
                    text = format(rounded, 'f')
                    if '.' in text: text = text.rstrip('0').rstrip('.')
                    parts.append('0' if rounded == 0 else text)
                out = ''.join(parts)
            if type(out) in (int, float): _number(out, 'derived value')
            memo[cache_key] = out
            return out
        return copy.deepcopy({key: value(key, t) for key in [*source_order, *nodes]})
    sample(0)
    return _Sampler(sample)
