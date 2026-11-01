import os,sys,json,subprocess,re,math,shutil
FF=os.environ.get('FFMPEG_BIN') or shutil.which('ffmpeg') or 'ffmpeg'
HERE=os.path.dirname(os.path.abspath(__file__)); os.chdir(os.environ.get('REEL_DIR',HERE)); sys.path.insert(0,HERE)
import numpy as np
from scipy.io import wavfile
from scipy.signal import resample_poly, butter, lfilter
from sfx import *
import scenes
B=scenes.B; PT=scenes.PT; TOTAL=B[-1]
N=int((TOTAL+0.3)*SR)
# ---- voice ----
sr,v=wavfile.read(sys.argv[1] if len(sys.argv)>1 else 'out/vo24.wav'); v=v.astype(np.float32)/32768
if v.ndim>1: v=v.mean(1)
v=resample_poly(v,441,240).astype(np.float32)
vo=np.zeros(N,np.float32); vo[:min(N,len(v))]=v[:N]
vpk=np.max(np.abs(vo)); print('vo peak',vpk)
# ---- events ----
E=[]
def ev(t,name,g=1.0,seed=0,pan=0.0): E.append((t,name,g,seed,pan))
ev(0.12,'impact',1.0); ev(0.12,'pop',0.7)
for i in range(14): ev(0.10+i*0.07,'tick',0.35,i)
ev(0.45,'sparkle',0.5,1); ev(0.6,'whoosh',0.3,2,(-.5,.6))
ev(2.55,'riser',0.8); ev(3.10,'impact',1.0,3); ev(3.12,'stomp',0.6); ev(3.15,'pop',0.6,2); ev(3.3,'pop',0.5,3)
for i in range(7): ev(3.4+i*0.28,'whoosh',0.28,10+i,(-.7,.7) if i%2 else (.7,-.7))
for i in range(1,7): ev(B[i]-0.19,'whoosh',0.9,40+i,(0.8,-0.8))
for i in range(6): ev(6.3+i*0.14,'pop',0.55,i,(-0.7+0.28*i))
ev(B[1]+0.2,'pop',0.7,5)
ev(8.0,'whoosh',0.5,7,(-.8,0)); ev(8.3,'whoosh',0.5,8,(.8,0))
for i in range(12): ev(9.7+i*0.24,'pop',0.35,20+i,(-.7+0.13*i)); 
for j in range(3): ev(11.0+j*0.35,'pop',0.5,30+j,0.0)
ev(12.95,'whoosh',0.6,9,(-.6,.6)); ev(13.8,'pop',0.8,4)
b=B[2]; ev(b+0.15,'whoosh',0.5,1,(.8,-.2)); ev(b-0.1,'riser',0.6); ev(b+0.45,'impact',0.8,2); ev(b+0.7,'sparkle',0.6,2); ev(b+1.3,'pop',0.8,3)
for i in range(4): ev(b+1.8+i*0.55,'tick',0.25,i)
b=B[3]; ev(b+0.3,'pop',0.7,1); ev(b+0.8,'pop',0.5,2); ev(b+0.3,'whoosh',0.4,3,(.8,0))
ev(b+2.4,'pop',0.8,4); ev(b+2.35,'zip',0.4,1); ev(b+3.5,'pop',0.8,5); ev(b+3.45,'zip',0.4,2)
ev(b+3.4,'riser',0.8); ev(b+4.0,'impact',1.0,6); ev(b+4.02,'sparkle',0.7,3)
for i in range(3): ev(b+4.6+i*0.15,'pop',0.35,10+i)
ev(b+5.0,'pop',0.7,7); ev(b+5.0,'tick',0.5,1); ev(b+6.5,'tick',0.5,2)
b=B[4]; ev(b+0.4,'pop',0.8,1); ev(b+0.5,'impact',0.5,4); ev(b+0.55,'sparkle',0.4,4)
for i in range(6):
    p=-0.5 if i%2==0 else 0.5
    ev(PT[i]-0.12,'zip',0.5,i,(0,p)); ev(PT[i]+0.45,'pop',0.55,i,p); ev(PT[i]+0.5,'tick',0.4,i)
ev(PT[0],'sparkle',0.4,5); ev(PT[3],'sparkle',0.4,6)
for i in range(6): ev(38.3+i*0.8,'tick',0.45,i)
for t in (38.4,40.3,41.7): ev(t,'pop',0.8,int(t))
b=B[5]; ev(b+0.05,'whoosh',0.4,2,(-.9,0)); ev(b+1.2,'sparkle',0.5,7); ev(b+1.7,'zip',0.5,3); ev(b+2.6,'impact',0.6,5); ev(b+2.7,'pop',0.8,6)
ev(b+2.95,'pop',0.7,7,(.6)); ev(b+3.2,'pop',0.5,8,(.6)); ev(b+3.8,'stomp',0.8,9,(.5))
for i in range(5): ev(b+3.0+i*0.35,'tick',0.5,i,-0.2)
ev(b+4.5,'sparkle',0.6,8)
b=B[6]; ev(b+0.1,'impact',0.9,7); ev(b+0.2,'whoosh',0.4,3,(.8,0)); ev(b+0.6,'pop',0.7,9); ev(b+0.7,'pop',0.6,10,-.5); ev(b+1.3,'pop',0.8,11,-.3)
ev(b+3.6,'whoosh',0.35,5,(-.8,-.2)); ev(b+4.85,'click',1.0,1,-.3); ev(b+4.88,'pop',0.7,12,-.3); ev(b+4.9,'sparkle',0.8,9,-.3)
sf=np.zeros((N,2),np.float32); cache={}
for t,name,g,seed,pan in E:
    k=(name,seed)
    if k not in cache: cache[k]=BANK[name](seed).astype(np.float32)
    place(sf,cache[k],t,g*0.40*vpk,pan)
# ---- music bed ----
bpm=76; beat=60/bpm; m=np.zeros(N,np.float32); tm=np.arange(N)/SR
chords=[(110,130.8,164.8,220),(87.3,110,130.8,174.6),(130.8,164.8,196,261.6),(98,123.5,146.8,196)]
nb=int(TOTAL/(beat*4))+2; r=np.random.default_rng(3)
for c in range(nb):
    t0=c*beat*4; ch=chords[c%4]; L=beat*4*1.12; i0=int(t0*SR); n=min(int(L*SR),N-i0)
    if n<=0: break
    t=np.arange(n)/SR; w=np.sin(np.pi*np.clip(t/L,0,1))**1.5
    pad=sum(np.sin(2*np.pi*f*t)+0.4*np.sin(2*np.pi*f*2*t*1.002)+0.25*np.sin(2*np.pi*f*3*t) for f in ch)/len(ch)
    m[i0:i0+n]+=pad*w*0.42
    for bt in (0,2):  # bass + kick
        j=int((t0+bt*beat)*SR); nn=min(int(0.7*SR),N-j)
        if nn>0:
            tb=np.arange(nn)/SR; m[j:j+nn]+=np.sin(2*np.pi*(ch[0]/2)*tb)*np.exp(-tb*4)*0.5
            kf=45+70*np.exp(-tb*40); m[j:j+nn]+=np.sin(2*np.pi*np.cumsum(kf)/SR)*np.exp(-tb*14)*0.45
    for s8 in range(8):  # pluck arpeggio + hats
        j=int((t0+s8*beat/2)*SR); nn=min(int(0.35*SR),N-j)
        if nn<=0: continue
        tb=np.arange(nn)/SR
        if r.random()<0.65:
            f=ch[r.integers(0,4)]*2*(2 if r.random()<0.3 else 1); m[j:j+nn]+=(np.sin(2*np.pi*f*tb)+0.3*np.sin(2*np.pi*2*f*tb))*np.exp(-tb*9)*0.16
        if s8%2==1:
            h=hp(r.normal(0,1,nn),7000)*np.exp(-tb*70); m[j:j+nn]+=h*0.10
b2,a2=butter(2,4800/(SR/2),'low'); m=lfilter(b2,a2,m).astype(np.float32); m/=np.max(np.abs(m))
# duck under VO
env=np.abs(vo); bb,aa=butter(1,6/(SR/2),'low'); env=lfilter(bb,aa,env)/ (vpk*0.35+1e-9); duck=1-0.62*np.clip(env,0,1)
m=m*duck
fade=np.clip((TOTAL+0.3-tm)/1.2,0,1)*np.clip(tm/0.8,0,1)
mus=np.stack([m*fade,m*fade],1)*0.17*vpk*1.6
mix=np.stack([vo,vo],1)+sf+mus
mix=np.clip(mix/ max(1.0,np.max(np.abs(mix))*1.02),-1,1)
wavfile.write('out/mix_raw.wav',SR,(mix*32767).astype(np.int16))
# ---- two-pass loudnorm ----
p1=subprocess.run([FF,'-hide_banner','-i','out/mix_raw.wav','-af','loudnorm=I=-14.5:TP=-1.5:LRA=11:print_format=json','-f','null','-'],capture_output=True,text=True).stderr
j=json.loads(p1[p1.rindex('{'):p1.rindex('}')+1]); print({k:j[k] for k in ('input_i','input_tp','input_lra','input_thresh','target_offset')})
af=f"loudnorm=I=-14.5:TP=-1.5:LRA=11:measured_I={j['input_i']}:measured_TP={j['input_tp']}:measured_LRA={j['input_lra']}:measured_thresh={j['input_thresh']}:offset={j['target_offset']}:linear=true"
subprocess.run([FF,'-y','-loglevel','error','-i','out/mix_raw.wav','-af',af,'-ar','44100','out/final_audio.wav'],check=True)
p3=subprocess.run([FF,'-hide_banner','-i','out/final_audio.wav','-af','loudnorm=I=-14.5:TP=-1.5:print_format=summary','-f','null','-'],capture_output=True,text=True).stderr
print([l for l in p3.splitlines() if 'Input Integrated' in l or 'Input True Peak' in l])
