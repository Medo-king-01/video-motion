import numpy as np, cv2, math, functools, os, glob
from PIL import Image, ImageDraw, ImageFont
W,H=1080,1920
def _find_font():
    """Brand font first (Cairo), then Tajawal, then a system fallback (flagged as TEMPORARY)."""
    root=os.environ.get('REEL_DIR') or os.getcwd()
    c=[os.environ.get('REEL_FONT')]
    for pat in ('assets/fonts/**/Cairo*.ttf','assets/fonts/**/Tajawal*ExtraBold*.ttf','assets/fonts/**/Tajawal*.ttf'):
        c+=sorted(glob.glob(os.path.join(root,pat),recursive=True))
    c+=['/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf','C:/Windows/Fonts/segoeuib.ttf',
        'C:/Windows/Fonts/arialbd.ttf','/System/Library/Fonts/Supplemental/Arial Bold.ttf']
    for p in c:
        if p and os.path.exists(p): return p
    raise FileNotFoundError('No usable font. Run: python <skill>/scripts/get_fonts.py "Cairo"  (or set REEL_FONT)')
FONT=_find_font()
FONT_IS_TEMP='cairo' not in os.path.basename(FONT).lower() and 'tajawal' not in os.path.basename(FONT).lower()
if FONT_IS_TEMP: print('[brand] WARNING: temporary font in use ->',FONT,'(declare it in the delivery message)')
# ---------- text layout backend ----------
# RAQM is the preferred path. Some Pillow wheels ship without libraqm; then we
# fall back to arabic_shape.py (HarfBuzz shaping + FreeType rasterising), which
# is real shaping, not presentation-form faking. Never letter-by-letter.
try:
    from PIL import features as _pil_features
    HAS_RAQM=bool(_pil_features.check('raqm'))
except Exception:
    HAS_RAQM=False
LAYOUT_BACKEND='raqm' if HAS_RAQM else 'harfbuzz'
_ar=None
if not HAS_RAQM:
    try:
        import arabic_shape as _ar
    except Exception as _e:                     # pragma: no cover - env problem, not logic
        print('[layout] FATAL: no libraqm and no arabic_shape.py:',_e)
        print('        fix: python -m pip install uharfbuzz freetype-py')
    else:
        print('[layout] libraqm not available -> arabic_shape.py (HarfBuzz + FreeType)')


def _shaper():
    """Return the fallback shaper or fail loudly. Never silently draw unjoined text."""
    if _ar is None:
        raise RuntimeError('Arabic shaping backend missing: python -m pip install uharfbuzz freetype-py')
    return _ar

@functools.lru_cache(maxsize=None)
def font(size):
    if HAS_RAQM:
        f=ImageFont.truetype(FONT,size,layout_engine=ImageFont.Layout.RAQM)
    else:
        f=ImageFont.truetype(FONT,size)
    try:  # variable fonts (Cairo[slnt,wght].ttf): force a bold weight
        vals=[]
        for a in f.get_variation_axes():
            nm=a.get('name'); nm=nm.decode() if isinstance(nm,bytes) else str(nm)
            vals.append(min(a['maximum'],max(a['minimum'],800)) if 'eight' in nm else a['default'])
        f.set_variation_by_axes(vals)
    except Exception: pass
    return f
BLACK=(46,36,35); INK=(71,57,56); RED=(203,39,27); DRED=(159,8,3); WHITE=(243,242,241)
# palette v2 aliases (see brand/brand.json): positive=blush, device bars=mauve, numbers/keywords=salmon
EMER=(213,174,166); TEAL=(139,103,101); YEL=(217,127,104); GRAY=(163,162,160); LGRAY=(201,197,194)
SS=3
# ---------- easing ----------
def clamp(x,a=0,b=1): return max(a,min(b,x))
def prog(t,a,b): return clamp((t-a)/(b-a)) if b>a else (1.0 if t>=a else 0.0)
def e_out(x): return 1-(1-x)**3
def e_io(x): return 3*x*x-2*x**3
def e_back(x,s=1.9): x=x-1; return 1+(s+1)*x**3+s*x**2
def e_elastic(x):
    if x<=0: return 0
    if x>=1: return 1
    return 1-math.exp(-7*x)*math.cos(11*x)
def lerp(a,b,x): return a+(b-a)*x
# ---------- text ----------
@functools.lru_cache(maxsize=2000)
def text_sprite(txt,size,color=(243,242,241),rtl=True,stroke=0,scolor=(46,36,35)):
    if not HAS_RAQM:
        return _shaper().text_sprite(FONT,txt,size,color,rtl,stroke,scolor)
    f=font(size)
    kw=dict(direction='rtl',language='ar') if rtl else dict(direction='ltr')
    d0=ImageDraw.Draw(Image.new('L',(4,4)))
    x0,y0,x1,y1=d0.textbbox((0,0),txt,font=f,stroke_width=stroke,**kw)
    pad=6+stroke
    im=Image.new('RGBA',(x1-x0+2*pad,y1-y0+2*pad),(0,0,0,0))
    ImageDraw.Draw(im).text((pad-x0,pad-y0),txt,font=f,fill=color+(255,),stroke_width=stroke,stroke_fill=scolor+(255,),**kw)
    return prem(np.array(im))
def prem(a):
    a=a.astype(np.float32); a[...,:3]*=a[...,3:4]/255.0; return a
# ---------- sprite drawing (supersampled) ----------
class D:
    def __init__(s,w,h):
        s.w,s.h=w,h; s.im=Image.new('RGBA',(w*SS,h*SS),(0,0,0,0)); s.d=ImageDraw.Draw(s.im)
    def _b(s,b): return [v*SS for v in b]
    def rect(s,b,fill=None,outline=None,width=0): s.d.rectangle(s._b(b),fill=fill,outline=outline,width=int(width*SS))
    def rrect(s,b,r,fill=None,outline=None,width=0): s.d.rounded_rectangle(s._b(b),r*SS,fill=fill,outline=outline,width=int(width*SS))
    def ell(s,b,fill=None,outline=None,width=0): s.d.ellipse(s._b(b),fill=fill,outline=outline,width=int(width*SS))
    def poly(s,pts,fill=None,outline=None,width=0):
        p=[(x*SS,y*SS) for x,y in pts]; s.d.polygon(p,fill=fill)
        if outline: s.d.line(p+[p[0]],fill=outline,width=int(width*SS),joint='curve')
    def line(s,pts,fill,width,round_=True):
        p=[(x*SS,y*SS) for x,y in pts]; s.d.line(p,fill=fill,width=int(width*SS),joint='curve')
        if round_:
            r=width*SS/2
            for x,y in (p[0],p[-1]): s.d.ellipse([x-r,y-r,x+r,y+r],fill=fill)
    def arc(s,b,a0,a1,fill,width): s.d.arc(s._b(b),a0,a1,fill=fill,width=int(width*SS))
    def circ(s,cx,cy,r,fill=None,outline=None,width=0): s.ell((cx-r,cy-r,cx+r,cy+r),fill,outline,width)
    def text(s,xy,txt,size,fill,rtl=False,anchor='mm'):
        if not HAS_RAQM:
            _shaper().draw(s.im,(xy[0]*SS,xy[1]*SS),FONT,txt,size*SS,fill,rtl,anchor); return
        f=font(size*SS)
        kw=dict(direction='rtl',language='ar') if rtl else {}
        s.d.text((xy[0]*SS,xy[1]*SS),txt,font=f,fill=fill,anchor=anchor,**kw)
    def done(s):
        im=s.im.resize((s.w,s.h),Image.LANCZOS); return prem(np.array(im))
def placeholder_medo(height):
    """Brand-silhouette stand-in (curly hair, round mirrored glasses, dark blazer) when the real Medo pose PNG is missing.
    ALWAYS declare it in the delivery message: the real anime-style Medo poses are the intended presenter."""
    w=int(height*0.62); d=D(w,height); cx=w/2; r=w*0.2; cy=height*0.2
    for a in range(180,361,20): d.circ(cx+(r+4)*math.cos(math.radians(a)),cy+(r+4)*math.sin(math.radians(a)),r*0.42,fill=(46,36,35))
    d.circ(cx,cy,r,fill=(71,57,56))
    for sx in (-1,1): d.circ(cx+sx*r*0.42,cy+r*0.05,r*0.3,fill=(243,242,241),outline=(46,36,35),width=3)
    d.line([(cx-r*0.12,cy+r*0.05),(cx+r*0.12,cy+r*0.05)],(243,242,241),3)
    d.rrect((cx-w*0.38,cy+r*1.2,cx+w*0.38,height*0.78),w*0.12,fill=(46,36,35))
    d.poly([(cx-w*0.07,cy+r*1.25),(cx+w*0.07,cy+r*1.25),(cx,cy+r*2.1)],fill=(243,242,241))
    d.rrect((cx-w*0.3,height*0.78-2,cx-w*0.04,height-4),10,fill=(71,57,56)); d.rrect((cx+w*0.04,height*0.78-2,cx+w*0.3,height-4),10,fill=(71,57,56))
    d.text((cx,height*0.5),'PLACEHOLDER',max(14,int(w*0.09)),(217,127,104),anchor='mm')
    return d.done()
def load_png(name,height):
    p=f'assets/{name}.png'
    if not os.path.exists(p):
        if name.startswith('medo'):
            print('[brand] WARNING: missing',p,'-> using brand-silhouette PLACEHOLDER'); return placeholder_medo(height)
        raise FileNotFoundError(p)
    im=cv2.imread(p,cv2.IMREAD_UNCHANGED)
    w=int(im.shape[1]*height/im.shape[0])
    im=cv2.resize(im,(w,height),interpolation=cv2.INTER_AREA)
    im=cv2.cvtColor(im,cv2.COLOR_BGRA2RGBA); return prem(im)
# ---------- compositing ----------
def paste(fr,spr,cx,cy,scale=1.0,rot=0.0,alpha=1.0,anchor=(0.5,0.5),flipx=False,sy=None):
    if alpha<=0.003 or scale<=0.003: return
    h,w=spr.shape[:2]; ax,ay=anchor[0]*w,anchor[1]*h
    sxs=scale*(-1 if flipx else 1); sys_=scale if sy is None else sy
    c,sn=math.cos(math.radians(rot)),math.sin(math.radians(rot))
    M=np.array([[c*sxs,-sn*sys_,0],[sn*sxs,c*sys_,0]],np.float32)
    M[0,2]=cx-(M[0,0]*ax+M[0,1]*ay); M[1,2]=cy-(M[1,0]*ax+M[1,1]*ay)
    pts=np.array([[0,0],[w,0],[w,h],[0,h]],np.float32)
    dst=pts@M[:,:2].T+M[:,2]
    x0=max(int(dst[:,0].min())-1,0); x1=min(int(dst[:,0].max())+2,W)
    y0=max(int(dst[:,1].min())-1,0); y1=min(int(dst[:,1].max())+2,H)
    if x1<=x0 or y1<=y0: return
    M2=M.copy(); M2[0,2]-=x0; M2[1,2]-=y0
    wp=cv2.warpAffine(spr,M2,(x1-x0,y1-y0),flags=cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT,borderValue=(0,0,0,0))
    a=wp[...,3:4]/255.0*alpha
    roi=fr[y0:y1,x0:x1]
    roi[:]=np.clip(wp[...,:3]*alpha+roi*(1-a),0,255)
def fill_rect(fr,x0,y0,x1,y1,color,alpha=1.0):
    x0,y0,x1,y1=max(int(x0),0),max(int(y0),0),min(int(x1),W),min(int(y1),H)
    if x1<=x0 or y1<=y0: return
    roi=fr[y0:y1,x0:x1]; roi[:]=roi*(1-alpha)+np.array(color,np.float32)*alpha
# ---------- reusable sprites ----------
@functools.lru_cache(maxsize=None)
def circle_spr(r,color,glow=0):
    pad=glow*2+4; d=D(2*r+2*pad,2*r+2*pad)
    if glow:
        g=Image.new('RGBA',d.im.size,(0,0,0,0)); gd=ImageDraw.Draw(g)
        gd.ellipse([pad*SS,pad*SS,(pad+2*r)*SS,(pad+2*r)*SS],fill=color+(150,))
        g=g.filter(__import__('PIL.ImageFilter',fromlist=['x']).GaussianBlur(glow*SS*0.8)); d.im.alpha_composite(g)
    d.circ(pad+r,pad+r,r,fill=color); return d.done()
@functools.lru_cache(maxsize=None)
def sparkle(r,color=(243,242,241)):
    d=D(r*2+4,r*2+4); c=r+2
    pts=[(c,c-r),(c+r*0.18,c-r*0.18),(c+r,c),(c+r*0.18,c+r*0.18),(c,c+r),(c-r*0.18,c+r*0.18),(c-r,c),(c-r*0.18,c-r*0.18)]
    d.poly(pts,fill=color); return d.done()
@functools.lru_cache(maxsize=None)
def pill(w,h,color,alpha=255,r=None):
    d=D(w,h); d.rrect((0,0,w,h),r if r else h//2,fill=color+(alpha,)); return d.done()
@functools.lru_cache(maxsize=None)
def bill(w=150):
    h=int(w*0.55); d=D(w,h)
    d.rrect((0,0,w,h),10,fill=(213,174,166),outline=(139,103,101),width=4)
    d.circ(w/2,h/2,h*0.3,fill=(243,242,241),outline=(139,103,101),width=3); d.text((w/2,h/2),'EGP',int(h*0.26),(139,103,101))
    d.rrect((10,10,34,22),4,fill=(139,103,101)); d.rrect((w-34,h-22,w-10,h-10),4,fill=(139,103,101)); return d.done()
@functools.lru_cache(maxsize=None)
def checkmark(s,color=EMER,bg=True):
    d=D(s,s)
    if bg: d.circ(s/2,s/2,s/2-2,fill=color)
    d.line([(s*.27,s*.52),(s*.44,s*.69),(s*.74,s*.34)],(243,242,241) if bg else color,s*.11); return d.done()
@functools.lru_cache(maxsize=None)
def crossmark(s,color=RED):
    d=D(s,s); d.circ(s/2,s/2,s/2-2,fill=color)
    d.line([(s*.3,s*.3),(s*.7,s*.7)],(243,242,241),s*.11); d.line([(s*.7,s*.3),(s*.3,s*.7)],(243,242,241),s*.11); return d.done()
@functools.lru_cache(maxsize=None)
def bubble(w,h,color=(243,242,241),tail='bl',alpha=255,outline=None):
    d=D(w+40,h+50); d.rrect((20,10,20+w,10+h),h*0.28 if h<200 else 40,fill=color+(alpha,),outline=outline,width=4 if outline else 0)
    if tail=='bl': d.poly([(60,10+h-4),(40,10+h+34),(110,10+h-4)],fill=color+(alpha,))
    elif tail=='br': d.poly([(w-70,10+h-4),(w-10,10+h+34),(w+0,10+h-4)],fill=color+(alpha,))
    elif tail=='bc': d.poly([(w/2-20,10+h-4),(w/2+20,10+h+34),(w/2+50,10+h-4)],fill=color+(alpha,))
    return d.done()
