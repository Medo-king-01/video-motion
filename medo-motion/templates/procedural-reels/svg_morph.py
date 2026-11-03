"""Conservative continuous-time multi-contour morph of bounded SVG geometry plans."""
from __future__ import annotations

import copy
import math

from motion_geometry import compile_morph
from svg_art import validate_svg_art


def _cross(a, b): return a[0]*b[1]-a[1]*b[0]
def _dot(a, b): return a[0]*b[0]+a[1]*b[1]
def _minus(a, b): return (a[0]-b[0], a[1]-b[1])
def _position(p, t): return (p[0][0]+(p[1][0]-p[0][0])*t, p[0][1]+(p[1][1]-p[0][1])*t)


def _quadratic(u, v, product):
    u0, v0 = u[0], v[0]; du, dv = _minus(u[1], u0), _minus(v[1], v0)
    return (product(u0,v0), product(u0,dv)+product(du,v0), product(du,dv))


def _vector(a, b): return (_minus(b[0],a[0]), _minus(b[1],a[1]))
def _orient(a,b,c): return _quadratic(_vector(a,b), _vector(a,c), _cross)
def _dot_at(a,b,c): return _quadratic(_vector(b,a), _vector(b,c), _dot)


def _range(coeff, lo, hi):
    c, b, a = coeff
    def f(t): return (a*t+b)*t+c
    vals = [f(lo), f(hi)]
    if a != 0:
        vertex = -b/(2*a)
        if lo < vertex < hi: vals.append(f(vertex))
    return min(vals), max(vals)


def _same_side(x,y,eps): return (x[0] > eps and y[0] > eps) or (x[1] < -eps and y[1] < -eps)


def _edges_separate(a,b,c,d,lo,hi,eps,linear_eps,budget,depth=0):
    budget[0] += 1
    if budget[0] > 50000: raise ValueError('morph topology verification budget exceeded')
    ab = [_position(p,t) for p in (a,b) for t in (lo,hi)]
    cd = [_position(p,t) for p in (c,d) for t in (lo,hi)]
    if any(max(p[k] for p in ab)+linear_eps < min(p[k] for p in cd) or max(p[k] for p in cd)+linear_eps < min(p[k] for p in ab) for k in (0,1)): return True
    if _same_side(_range(_orient(a,b,c),lo,hi), _range(_orient(a,b,d),lo,hi), eps) or _same_side(_range(_orient(c,d,a),lo,hi), _range(_orient(c,d,b),lo,hi), eps): return True
    if depth >= 12: return False
    mid = (lo+hi)/2
    return _edges_separate(a,b,c,d,lo,mid,eps,linear_eps,budget,depth+1) and _edges_separate(a,b,c,d,mid,hi,eps,linear_eps,budget,depth+1)


def _adjacent_safe(a,b,c,lo,hi,eps,budget,depth=0):
    budget[0] += 1
    if budget[0] > 50000: raise ValueError('morph topology verification budget exceeded')
    orient = _range(_orient(a,b,c),lo,hi)
    if orient[0] > eps or orient[1] < -eps or _range(_dot_at(a,b,c),lo,hi)[1] < -eps: return True
    if depth >= 12: return False
    mid = (lo+hi)/2
    return _adjacent_safe(a,b,c,lo,mid,eps,budget,depth+1) and _adjacent_safe(a,b,c,mid,hi,eps,budget,depth+1)


def _inside(point, ring, t):
    x,y = _position(point,t); inside = False
    for i in range(len(ring)):
        ax,ay = _position(ring[i],t); bx,by = _position(ring[(i+1)%len(ring)],t)
        if (ay > y) != (by > y) and x < (bx-ax)*(y-ay)/(by-ay)+ax: inside = not inside
    return inside


def _validate_rings(rings):
    scale = max([1]+[abs(n) for ring in rings for p in ring for pos in p for n in pos])
    eps, linear_eps = 1e-10*scale*scale, 1e-10*scale; budget = [0]
    for ring in rings:
        area = [0.,0.,0.]; n = len(ring)
        for i, point in enumerate(ring):
            nxt, after = ring[(i+1)%n], ring[(i+2)%n]
            vector = _vector(point,nxt)
            if _range(_quadratic(vector,vector,_dot),0,1)[0] <= eps: raise ValueError('morph edge can collapse')
            q = _quadratic(point,nxt,_cross)
            for k in range(3): area[k] += q[k]
            if not _adjacent_safe(point,nxt,after,0,1,eps,budget): raise ValueError('morph adjacent edges may overlap')
        bounds = _range(area,0,1)
        if bounds[0] <= eps and bounds[1] >= -eps: raise ValueError('morph ring area may collapse')
        for i in range(n):
            for j in range(i+1,n):
                if j == i+1 or (i == 0 and j == n-1): continue
                if not _edges_separate(ring[i],ring[(i+1)%n],ring[j],ring[(j+1)%n],0,1,eps,linear_eps,budget): raise ValueError('morph ring may self-intersect')
    for i in range(len(rings)):
        for j in range(i+1,len(rings)):
            a,b = rings[i],rings[j]
            for k in range(len(a)):
                for q in range(len(b)):
                    if not _edges_separate(a[k],a[(k+1)%len(a)],b[q],b[(q+1)%len(b)],0,1,eps,linear_eps,budget): raise ValueError('morph contours may intersect')
            if _inside(a[0],b,0) != _inside(a[0],b,1) or _inside(b[0],a,0) != _inside(b[0],a,1): raise ValueError('morph contour nesting differs')


def compile_svg_morph(spec):
    if not isinstance(spec, dict) or type(spec.get('version')) is not int or spec['version'] != 1: raise ValueError('SVG morph requires version 1')
    source, target, count = spec.get('from'), spec.get('to'), spec.get('count', 24)
    validate_svg_art(source); validate_svg_art(target)
    if type(count) is not int or not 8 <= count <= 64 or source['viewBox'] != target['viewBox'] or len(source['shapes']) != len(target['shapes']) or len(source['shapes']) > 8: raise ValueError('incompatible SVG morph plans')
    morphs, total = [], 0
    for a,b in zip(source['shapes'],target['shapes']):
        if any(a[k] != b[k] for k in ('id','fill','stroke','strokeWidth','opacity')) or len(a['contours']) != len(b['contours']): raise ValueError('SVG shape paint/contour mismatch')
        group, rings = [], []
        for x,y in zip(a['contours'],b['contours']):
            total += count
            if not x['closed'] or not y['closed'] or total > 192: raise ValueError('SVG morph needs closed contours within sample budget')
            plan = compile_morph({'from': x['points'], 'to': y['points'], 'count': count, 'closed': True, 'align': True})
            start, end = plan.at(0), plan.at(1)
            rings.append([((p['x'],p['y']),(q['x'],q['y'])) for p,q in zip(start,end)]); group.append(plan)
        _validate_rings(rings); morphs.append(group)
    base = copy.deepcopy(source)
    class SvgMorph:
        def at(self, progress):
            if type(progress) not in (int,float) or not math.isfinite(progress): raise ValueError('progress must be finite')
            result = copy.deepcopy(base)
            for shape,group in zip(result['shapes'],morphs):
                for contour,plan in zip(shape['contours'],group): contour['points'] = plan.at(progress)
            return result
    return SvgMorph()
