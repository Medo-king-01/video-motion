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
BANK=dict(pop=pop,tick=tick,click=click,zip=zip_,whoosh=whoosh,riser=riser,impact=impact,stomp=stomp,sparkle=sparkle)
def place(buf,sig,t,gain=1.0,pan=0.0):
    i=int(t*SR); n=min(len(sig),buf.shape[0]-i)
    if n<=0 or i<0: return
    s=sig[:n]*gain
    if isinstance(pan,tuple): p=np.linspace(pan[0],pan[1],n)
    else: p=np.full(n,pan)
    a=(p+1)*np.pi/4; buf[i:i+n,0]+=s*np.cos(a); buf[i:i+n,1]+=s*np.sin(a)
