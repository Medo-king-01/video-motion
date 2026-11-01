import os,sys,subprocess,shutil
# FFmpeg may live outside PATH (tools/bin, imageio-ffmpeg wheel). Override with FFMPEG_BIN.
FF=os.environ.get('FFMPEG_BIN') or shutil.which('ffmpeg') or 'ffmpeg'
HERE=os.path.dirname(os.path.abspath(__file__)); os.chdir(os.environ.get('REEL_DIR',HERE)); sys.path.insert(0,HERE)
from scenes import *
a,b=int(sys.argv[1]),int(sys.argv[2]); out=f'out/c_{a:05d}_{b:05d}.mp4'   # name carries BOTH ends so a different chunk size never reuses a stale file
os.makedirs('out',exist_ok=True)
if os.path.exists(out): sys.exit()
# MASTER encode spec (brand brief v4): CRF 13 + animation tune -> ~2.5-4 Mbps at 1080x1920. Below ~2 Mbps = rejected.
cmd=[FF,'-y','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r','30','-i','-',
     '-c:v','libx264','-preset','medium','-crf','13','-tune','animation','-x264-params','aq-mode=3:ref=4:deblock=1,1',
     '-pix_fmt','yuv420p',out+'.tmp.mp4']
p=subprocess.Popen(cmd,stdin=subprocess.PIPE)
for i in range(a,b): p.stdin.write(render_frame(i/30).tobytes())
p.stdin.close(); p.wait(); os.rename(out+'.tmp.mp4',out); print('chunk',a,b,flush=True)
