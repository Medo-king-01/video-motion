"""Chunked, restartable render (works on Windows/macOS/Linux). Re-run it if it stops: finished chunks are skipped.
Each chunk is a NEW process (lesson learned: one long render silently died mid-way)."""
import os,sys,subprocess,glob,shutil
FF=os.environ.get('FFMPEG_BIN') or shutil.which('ffmpeg') or 'ffmpeg'
HERE=os.path.dirname(os.path.abspath(__file__)); os.chdir(os.environ.get('REEL_DIR',HERE)); sys.path.insert(0,HERE)
FPS=30; CH=int(os.environ.get('REEL_CHUNK','276'))
from scenes import B
N=round(B[-1]*FPS)
if os.environ.get('REEL_MAXFRAMES'): N=min(N,int(os.environ['REEL_MAXFRAMES']))  # smoke test only
os.makedirs('out',exist_ok=True)
import hashlib
def _signature():
    h=hashlib.sha1()
    for fn in ('scenes.py','art.py','lib.py'): h.update(open(os.path.join(HERE,fn),'rb').read())
    for p in sorted(glob.glob('assets/*.png')): h.update(p.encode()); h.update(str(os.path.getsize(p)).encode())
    h.update(repr((N,CH,B)).encode()); return h.hexdigest()
sig=_signature(); sigf='out/chunks.sig'
if os.path.exists(sigf) and open(sigf).read()!=sig:   # code/assets/timing changed -> old chunks are stale
    for p in glob.glob('out/c_*.mp4*'): os.remove(p)
    print('source changed: old chunks removed')
open(sigf,'w').write(sig)
log=open('out_log.txt','a',encoding='utf-8')
for a in range(0,N,CH):
    b=min(a+CH,N)
    r=subprocess.run([sys.executable,os.path.join(HERE,'chunk.py'),str(a),str(b)],stdout=log,stderr=log)
    if r.returncode: print('chunk failed',a,b,'- see out_log.txt; re-run to resume'); sys.exit(1)
parts=sorted(p for p in glob.glob('out/c_*.mp4') if '.tmp' not in p)
with open('out/list.txt','w',encoding='utf-8') as f:
    for p in parts: f.write("file '%s'\n"%os.path.abspath(p).replace('\\','/'))
r=subprocess.run([FF,'-y','-loglevel','error','-f','concat','-safe','0','-i','out/list.txt','-c','copy','out/video_only.mp4'],stdout=log,stderr=log)
log.write('VIDEODONE\n' if r.returncode==0 else 'CONCAT_FAILED\n'); log.close()
print('VIDEODONE' if r.returncode==0 else 'CONCAT_FAILED', len(parts),'chunks, N =',N)
