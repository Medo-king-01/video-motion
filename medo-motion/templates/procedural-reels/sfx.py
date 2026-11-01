"""Sound design for the reel — every sound here is synthesised, so the kit is free, offline and
deterministic (same seed → same samples → the same mix on every machine).

Why procedural: a reel needs hits that land on *exact* frames, and licence-free sources still need
QA. Generating them means one vocabulary that both engines' edit lists can reference by name
(`pop`, `whoosh`, `swipe`, `glitch`…), and `transition.py` already declares which sound each
transition wants.

    from sfx import BANK, CATALOG, bus, render_bank, cues_for_transitions
    out = bus(6.0, [{"t": 0.4, "sfx": "whoosh", "gain": .8, "pan": (.7, -.7)}])
"""
import numpy as np
from scipy.signal import butter, lfilter
SR=44100
def R(seed): return np.random.default_rng(int(seed)+11)
def tt(d): return np.arange(int(d*SR))/SR
def bp(x,lo,hi): b,a=butter(2,[lo/(SR/2),min(hi,SR/2-100)/(SR/2)],'band'); return lfilter(b,a,x)
def lp(x,f): b,a=butter(2,f/(SR/2),'low'); return lfilter(b,a,x)
def hp(x,f): b,a=butter(2,f/(SR/2),'high'); return lfilter(b,a,x)
def nrm(x): m=np.max(np.abs(x))+1e-9; return x/m
def sweep(f0,f1,d,curve=6):
    t=tt(d); f=f1+(f0-f1)*np.exp(-t*curve/d); return np.sin(2*np.pi*np.cumsum(f)/SR)
def pop(seed=0):
    r=R(seed); f0=r.uniform(500,640); t=tt(0.16); f=f0*(1+0.9*np.exp(-t*35)); x=np.sin(2*np.pi*np.cumsum(f)/SR)*np.exp(-t*26)
    x[:60]+=r.normal(0,0.25,60)*np.linspace(1,0,60); return nrm(x)
def tick(seed=0):
    r=R(seed); f=r.uniform(2600,3500); t=tt(0.06); return nrm(np.sin(2*np.pi*f*t)*np.exp(-t*120)+r.normal(0,0.05,len(t))*np.exp(-t*200))
def click(seed=0):
    r=R(seed); t=tt(0.08); x=np.sin(2*np.pi*r.uniform(1500,1900)*t)*np.exp(-t*90); x[:80]+=r.normal(0,0.3,80)*np.linspace(1,0,80); return nrm(x)
def zip_(seed=0):
    r=R(seed); d=0.24; t=tt(d); x=sweep(r.uniform(260,340),r.uniform(1700,2200),d,curve=-3) if False else np.sin(2*np.pi*np.cumsum(300+1800*(t/d)**2)/SR)
    return nrm(x*np.minimum(1,t*80)*np.exp(-t*9))
def whoosh(seed=0,d=0.5):
    r=R(seed); n=r.normal(0,1,int(d*SR)); t=tt(d); env=np.sin(np.pi*np.clip(t/d,0,1))**2
    return nrm((bp(n,350,2600)*env+0.5*bp(n,1800,7000)*env**2))
def riser(seed=0,d=0.6):
    r=R(seed); n=r.normal(0,1,int(d*SR)); t=tt(d); a=(t/d)**2
    return nrm(hp(n,1500)*a*0.6+np.sin(2*np.pi*np.cumsum(180+1300*(t/d)**2)/SR)*a*0.5)
def impact(seed=0):
    r=R(seed); d=0.7; t=tt(d); f=36+60*np.exp(-t*18); sub=np.sin(2*np.pi*np.cumsum(f)/SR)*np.exp(-t*6.5)
    nz=lp(r.normal(0,1,len(t)),1100)*np.exp(-t*16)*0.7; return nrm(sub+nz)
def stomp(seed=0):
    r=R(seed); d=0.35; t=tt(d); f=50+70*np.exp(-t*30); x=np.sin(2*np.pi*np.cumsum(f)/SR)*np.exp(-t*12)+lp(r.normal(0,1,len(t)),700)*np.exp(-t*30)*0.5; return nrm(x)
def sparkle(seed=0):
    r=R(seed); d=0.7; t=tt(d); x=np.zeros(len(t))
    for k,f in enumerate([2400,3100,4200,5200]):
        f*=r.uniform(0.95,1.05); s=int(k*0.04*SR); tk=t[:len(t)-s]
        x[s:]+=np.sin(2*np.pi*f*tk+0.5*np.sin(2*np.pi*9*tk))*np.exp(-tk*9)*(0.9**k)
    return nrm(x)
def swipe(seed=0,d=0.22):
    """Short, wide band noise sweep — the sound of a frame sliding in."""
    r=R(seed); n=r.normal(0,1,int(d*SR)); t=tt(d); u=t/d
    env=(u**0.35)*np.exp(-u*3.1)                     # fast attack, tight tail
    band=bp(n,1200,8000)
    flick=np.sin(2*np.pi*np.cumsum(2100-1500*u)/SR)*np.exp(-u*6)*0.25
    return nrm(band*env+flick)

def noise(seed=0,d=0.8):
    """Neutral air / room tone swell — pairs with dissolves and cut-tos."""
    r=R(seed); n=r.normal(0,1,int(d*SR)); t=tt(d); u=t/d
    env=np.sin(np.pi*u)**2
    return nrm((lp(n,900)+0.5*bp(n,900,3000))*env)

def glitch(seed=0,d=0.3):
    """Digital stutter: squared-off noise bursts on a hard grid."""
    r=R(seed); n=int(d*SR); out=np.zeros(n)
    for i in range(14):
        j=int(r.uniform(0,0.9)*n); L=int(r.uniform(0.008,0.03)*SR); L=min(L,n-j)
        if L<=0: continue
        g=r.uniform(0.3,1.0); out[j:j+L]+=r.choice([-1,1,1])*g*np.sign(r.normal(0,1,L))
    t=tt(d); out=bp(out,900,7000)+0.3*np.sin(2*np.pi*(180+900*np.exp(-t*20))*t)
    return nrm(out*np.exp(-t*3.2))

def chime(seed=0):
    """Soft FM bell — for reveals and confirmations."""
    r=R(seed); d=1.1; t=tt(d); f=r.uniform(880,1100)
    mod=np.sin(2*np.pi*f*2.01*t)*2.2*np.exp(-t*3)
    x=np.sin(2*np.pi*f*t+mod)*np.exp(-t*3.4)+0.35*np.sin(2*np.pi*f*2*t)*np.exp(-t*6)
    return nrm(x)

def sub(seed=0,d=0.9):
    """Sub drop — weight under a cut without a hard impact."""
    t=tt(d); f=90*np.exp(-t*3)+34
    x=np.sin(2*np.pi*np.cumsum(f)/SR)*np.exp(-t*2.4)
    return nrm(x)

def blip(seed=0):
    """Tiny UI confirmation (square-ish, 40 ms)."""
    r=R(seed); d=0.09; t=tt(d); f=r.uniform(900,1400)
    x=np.tanh(3*np.sin(2*np.pi*f*t))*np.exp(-t*38)
    return nrm(x)

BANK=dict(pop=pop,tick=tick,click=click,zip=zip_,whoosh=whoosh,riser=riser,impact=impact,stomp=stomp,
          sparkle=sparkle,swipe=swipe,noise=noise,glitch=glitch,chime=chime,sub=sub,blip=blip)

# Loudness family per sound: mixing by ear is what makes a reel sound amateur, so the bus scales each
# hit by its family before applying the cue gain.
CATALOG={
 'pop':     dict(family='ui',     gain=0.55, tags='accent, marker, sticker'),
 'blip':    dict(family='ui',     gain=0.40, tags='tiny confirmation'),
 'click':   dict(family='ui',     gain=0.45, tags='toggle'),
 'tick':    dict(family='ui',     gain=0.30, tags='counter, blinds, checklist'),
 'zip':     dict(family='ui',     gain=0.45, tags='line draw, underline'),
 'chime':   dict(family='tonal',  gain=0.50, tags='reveal, good news'),
 'sparkle': dict(family='tonal',  gain=0.45, tags='magic detail'),
 'whoosh':  dict(family='air',    gain=0.55, tags='scene change, wipe'),
 'swipe':   dict(family='air',    gain=0.50, tags='slide, push, card stack'),
 'noise':   dict(family='air',    gain=0.35, tags='dissolve, room tone'),
 'riser':   dict(family='build',  gain=0.55, tags='pre-impact lift'),
 'impact':  dict(family='impact', gain=0.75, tags='landing, statement'),
 'stomp':   dict(family='impact', gain=0.55, tags='body drop'),
 'sub':     dict(family='impact', gain=0.45, tags='weight under a cut'),
 'glitch':  dict(family='texture',gain=0.45, tags='glitch transition, error beat'),
}
def duration(name, **kw):
    """Length in seconds of a sound (rendered once, then measured)."""
    return len(BANK[name](**kw))/SR


def place(buf,sig,t,gain=1.0,pan=0.0):
    i=int(t*SR); n=min(len(sig),buf.shape[0]-i)
    if n<=0 or i<0: return
    s=sig[:n]*gain
    if isinstance(pan,tuple): p=np.linspace(pan[0],pan[1],n)
    else: p=np.full(n,pan)
    a=(p+1)*np.pi/4; buf[i:i+n,0]+=s*np.cos(a); buf[i:i+n,1]+=s*np.sin(a)


# ---------------- cue sheet → stereo bus ----------------
def _pan_value(pan):
    """Scalar or (start, end) pan, clamped to [-1, 1]."""
    if isinstance(pan, (tuple, list)) and len(pan) == 2:
        return (max(-1.0, min(1.0, float(pan[0]))), max(-1.0, min(1.0, float(pan[1]))))
    return max(-1.0, min(1.0, float(pan or 0.0)))


def bus(length, cues, sr=SR, seed_offset=0):
    """Render a cue list into a stereo float32 bus.

    cues: [{"t": 1.2, "sfx": "whoosh", "gain": 1.0, "pan": (0.7, -0.7)}]
    Missing gain/pan fall back to the catalogue defaults, and the catalogue's family gain is always
    applied first, so a cue gain of 1.0 means "as loud as this sound should be in a mix".
    """
    n = int(length * sr) + 1
    out = np.zeros((n, 2), np.float32)
    cache = {}
    for i, cue in enumerate(cues):
        name = cue.get("sfx") or cue.get("name")
        if name not in BANK:
            raise KeyError(f"unknown sfx {name!r}; known: {', '.join(sorted(BANK))}")
        seed = int(cue.get("seed", i) or 0) + seed_offset
        key = (name, seed)
        if key not in cache:
            cache[key] = BANK[name](seed).astype(np.float32)
        gain = float(cue.get("gain", 1.0)) * float(CATALOG.get(name, {}).get("gain", 0.5))
        place(out, cache[key], float(cue.get("t", 0.0)), gain, _pan_value(cue.get("pan", 0.0)))
    return out


def cues_for_transitions(cuts, gain=1.0, pan=(0.0, 0.0)):
    """Cut list → cue list, using the sound each transition declares in transitions.json.

    cuts: [{"scene": 3, "t": 12.4, "name": "wipe"}]  →  [{"t": 12.4 + lead, "sfx": "whoosh", ...}]
    """
    try:
        from transition import sfx_for
    except ImportError:  # pragma: no cover
        sfx_for = lambda _n: None  # noqa: E731
    cues = []
    for i, cut in enumerate(cuts):
        name = sfx_for(cut.get("name", ""))
        if not name:
            continue
        cues.append({"t": float(cut.get("t", 0.0)), "sfx": name,
                     "gain": float(cut.get("gain", gain)), "pan": cut.get("pan", pan), "seed": i})
    return cues


def write_wav(path, buf, sr=SR):
    from scipy.io import wavfile
    wavfile.write(path, sr, (np.clip(buf, -1, 1) * 32767).astype(np.int16))


def render_bank(outdir, names=None, sr=SR):
    """Write the whole kit as 44.1 kHz stereo WAVs (one per sound) — handy for an editor/AE import."""
    import os
    os.makedirs(outdir, exist_ok=True)
    written = []
    for name in (names or BANK):
        sig = BANK[name](0).astype(np.float32)
        st = np.stack([sig, sig], 1) * float(CATALOG.get(name, {}).get("gain", 0.5))
        path = os.path.join(outdir, f"{name}.wav")
        write_wav(path, st, sr)
        written.append(path)
    return written


def duck(vo, bus_buf, depth=0.62, release=6.0, sr=SR):
    """Sidechain-style ducking of the sfx bus under the voice (one-pole envelope follower)."""
    n = min(len(vo), len(bus_buf))
    env = np.abs(vo[:n]).astype(np.float32)
    b, a = butter(1, release / (sr / 2), 'low')
    env = lfilter(b, a, env)
    peak = float(np.max(env)) + 1e-9
    env = np.clip(env / (peak * 0.35 + 1e-9), 0, 1)
    gain = (1.0 - depth * env)[:, None]
    out = bus_buf[:n].copy()
    out *= gain
    return out
