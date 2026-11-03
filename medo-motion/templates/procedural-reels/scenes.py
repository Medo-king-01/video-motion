import math, functools, random, os
from render_policy import decorative_time, motion_mode
MOTION_MODE = motion_mode(os.environ.get("MEDO_MOTION_MODE", "normal"))
# This demo explicitly reduces only its ambient grid/dust, not every scene motion.
SUPPORTS_REDUCED_MOTION = True
from art import *
# The demo episode's VO is 55.2 s — this is that episode's data, NOT a length rule.
# A real project rebuilds B from its own VO: python3 tools/vo_length.py out/vo24.wav --json plan/beats.json
B=[0,5.9,15.75,20.2,28.7,43.5,48.9,55.2]
FPS=30
# HUD: progress bar only. There is NO series name and NO logo in this studio, so
# CHIP stays None. Set it to a short string only if the user explicitly asks for
# an on-screen label (never invent one).
CHIP=None
def over(dst,src,x,y):
    h,w=src.shape[:2]; H_,W_=dst.shape[:2]
    sx0=max(0,-x); sy0=max(0,-y); x=max(x,0); y=max(y,0)
    src=src[sy0:,sx0:]; h,w=src.shape[:2]; h=min(h,H_-y); w=min(w,W_-x); src=src[:h,:w]
    if h<=0 or w<=0: return
    roi=dst[y:y+h,x:x+w]; roi[:]=src+roi*(1-src[...,3:4]/255.0)
# ---------- background ----------
def make_bg():
    yy=np.linspace(0,1,H)[:,None,None]
    base=np.array((10,10,10),np.float32)*(1-yy)+np.array((3,3,3),np.float32)*yy
    bg=np.repeat(base,W,1)
    for y in range(40,H,64):
        for x in range(40,W,64): bg[y-1:y+2,x-1:x+2]+=9
    xx=np.linspace(-1,1,W)[None,:,None]; vig=1-0.28*(xx**2)*np.ones((H,1,1)); bg=bg*vig
    return np.ascontiguousarray(bg.astype(np.float32))
def make_bgs():
    yy=np.linspace(0,1,H)[:,None,None]; xx=np.linspace(-1,1,W)[None,:,None]
    d=np.array((10,10,10),np.float32)*(1-yy)+np.array((3,3,3),np.float32)*yy
    d=np.repeat(d,W,1)*(1-0.28*(xx**2)*np.ones((H,1,1)))
    l=np.array((243,242,241),np.float32)*(1-yy)+np.array((216,215,213),np.float32)*yy
    l=np.repeat(l,W,1)*(1-0.10*(xx**2)*np.ones((H,1,1)))
    return np.ascontiguousarray(d.astype(np.float32)),np.ascontiguousarray(l.astype(np.float32))
BGD,BGL=make_bgs()
T={'dark':True}
INK2=(3,3,3); GOLD=(213,174,166)
THEME=[0,0,1,0,1,0,1]
GRID=[(3,3,3),(64,-18,10),(159,8,3),(88,0,-22),(3,3,3),(80,-16,0),(3,3,3)]
def bg_frame(k,t):
    dark=THEME[k]; base=BGD if dark else BGL; cell,vx,vy=GRID[k]
    ys=((np.arange(H)+int(t*vy))%cell)<2; xs=((np.arange(W)+int(t*vx))%cell)<2
    m=(ys[:,None]|xs[None,:]).astype(np.float32)[...,None]
    return base+m*np.float32(8.0 if dark else -9.0)
_rn=random.Random(5); DUST=[(_rn.uniform(0,W),_rn.uniform(0,H),_rn.uniform(-14,14),_rn.uniform(-30,-9),_rn.randint(2,5),_rn.uniform(0.25,0.6)) for _ in range(30)]
def dust(fr,t,dark):
    col=(213,174,166) if dark else (113,113,122)
    for x,y,vx,vy,r,a in DUST: paste(fr,circle_spr(r,col,0),(x+vx*t)%W,(y+vy*t)%H,alpha=a*0.8)
def bl(t,off=0): return ((t+off)%4.3)<0.13
IMPACTS=[(0.12,10,0.30),(3.10,12,0.30),(B[2]+0.45,7,0.0),(B[3]+4.0,12,0.35),(B[4]+0.35,6,0.0),(B[5]+2.6,8,0.0),(B[6]+0.1,8,0.25),(B[6]+4.85,7,0.0)]
def shake_flash(t):
    sx=sy=fl=0
    for te,amp,f in IMPACTS:
        d=t-te
        if 0<=d<0.5:
            e=math.exp(-d*9); sx+=amp*e*math.sin(d*70); sy+=amp*0.6*e*math.cos(d*83); fl=max(fl,f*max(0,1-d/0.10))
    return sx,sy,fl
def camera(fr,z,tx,ty):
    M=np.array([[z,0,W/2-z*W/2+tx],[0,z,H/2-z*H/2+ty]],np.float32)
    return cv2.warpAffine(fr,M,(W,H),flags=cv2.INTER_LINEAR,borderMode=cv2.BORDER_REPLICATE)
def speed_lines(fr,cx,cy,u,col):
    if u<=0 or u>=1: return
    r0=110+260*e_out(u); r1=r0+300*(1-u)+60
    for i in range(26):
        a=i*6.2832/26+0.1*math.sin(i*3.1)
        cv2.line(fr,(int(cx+r0*math.cos(a)),int(cy+r0*math.sin(a))),(int(cx+r1*math.cos(a)),int(cy+r1*math.sin(a))),col,max(1,int(6*(1-u))),cv2.LINE_AA)

SK={'cur':None}
def Medo(name,h):
    k=(name,h)
    if k not in SK: SK[k]=load_png(name,h)
    return SK[k]
def red_circle(fr,cx,cy,r,col=RED,alpha=1.0,glow=40):
    paste(fr,circle_spr(int(r),col,glow),cx,cy,alpha=alpha)
def ring(fr,cx,cy,r,col,width,alpha=1.0):
    key=('ring',int(r),col,width)
    if key not in SK:
        d=D(int(2*r+20),int(2*r+20)); d.circ(r+10,r+10,r,outline=col,width=width); SK[key]=d.done()
    paste(fr,SK[key],cx,cy,alpha=alpha)
def txt(fr,s,cx,cy,size,color=WHITE,rtl=True,scale=1,alpha=1,stroke=0,scolor=(3,3,3),rot=0):
    paste(fr,text_sprite(s,size,color,rtl,stroke,scolor),cx,cy,scale=scale,alpha=alpha,rot=rot)
# ---------- captions ----------
def reveal_times(words,t0,t1):
    tot=sum(len(w)+1 for w,_ in words); span=(t1-t0)*0.82; out=[]; acc=0
    for w,_ in words: out.append(t0+span*acc/tot); acc+=len(w)+1
    return out
def mk(text,t0,t1,hl=None):
    hl=hl or {}; words=[]
    for w in text.split():
        key=w.strip('،:؟.!,'); words.append((w,hl.get(key,WHITE)))
    return dict(t0=t0,t1=t1,words=words,times=reveal_times(words,t0,t1))
CAPS=[
 mk("هتدفع كام ألف جنيه في لابتوب،",0.15,2.9,{"ألف":YEL,"جنيه":YEL}),
 mk("وبعد شهر تكتشف إنه مش مناسب لاستخدامك؟",2.9,5.6,{"مش":RED,"مناسب":RED,"شهر":YEL}),
 mk("ده بيحصل مع ناس كتير،",6.26,7.74,{"ناس":YEL,"كتير":YEL}),
 mk("والسبب بسيط:",8.13,8.94,{"بسيط":EMER}),
 mk("اللي بيبيعلك بيكلمك بأرقام ومصطلحات،",9.65,12.57,{"بأرقام":YEL,"ومصطلحات":YEL}),
 mk("ومحدش بيشرحلك الكلام ده يعني إيه",12.95,15.5,{"يعني":RED,"إيه":RED}),
 mk("أهلاً بيكم،",16.24,17.1,{}),
 mk("معاكم ميدو، وعشان كده بدأنا السلسلة دي.",17.26,19.9,{"ميدو":RED}),
 mk("هنبدأ من الأول خالص:",20.6,22.0,{"الأول":YEL}),
 mk("إيه الفرق بين اللابتوب والكمبيوتر المكتبي،",22.0,25.1,{"اللابتوب":EMER,"والكمبيوتر":YEL,"المكتبي":YEL}),
 mk("وإمتى يبقى كل واحد فيهم هو الاختيار الأنسب ليك",25.1,28.45,{"الأنسب":YEL}),
 mk("وبعدها هناخد اللابتوب حتة حتة:",29.07,31.5,{"حتة":YEL}),
 mk("المعالج، الرامات، التخزين، الشاشة، كارت الشاشة، والبطارية.",31.86,37.7,{"المعالج":EMER,"الرامات":EMER,"التخزين":EMER,"الشاشة":EMER,"كارت":EMER,"والبطارية":EMER}),
 mk("كل جزء هنشرحه بالبلدي، يعني إيه وبيأثر على استخدامك إزاي.",38.3,43.3,{"بالبلدي":YEL,"استخدامك":EMER}),
 mk("وفي الآخر هتبقى قادر تختار لابتوب بنفسك،",43.9,46.5,{"قادر":EMER,"بنفسك":EMER}),
 mk("من غير ما تعتمد على كلام البائع.",46.6,48.7,{"البائع":RED}),
 mk("لو عايز تشتري لابتوب في الفترة الجاية،",49.27,51.85,{}),
 mk("أو عايز تفهم اللي في إيدك،",51.85,53.55,{}),
 mk("تابع السلسلة من أول حلقة.",53.55,55.2,{"تابع":RED,"السلسلة":YEL}),
]
@functools.lru_cache(maxsize=None)
def cap_layout(i):
    c=CAPS[i]; size=58; sp=20; maxw=970
    spr=[text_sprite(w,size,col,True,6,(3,3,3)) for w,col in c['words']]
    lines=[[]]; lw=[0]
    for k,s in enumerate(spr):
        w=s.shape[1]-12
        add=w+(sp if lines[-1] else 0)
        if lines[-1] and lw[-1]+add>maxw: lines.append([]); lw.append(0); add=w
        lines[-1].append(k); lw[-1]+=add
    lh=92; n=len(lines); pos={}
    for li,idx in enumerate(lines):
        xr=lw[li]/2; cy=(li-(n-1)/2)*lh
        for k in idx:
            w=spr[k].shape[1]-12; pos[k]=(xr-w/2,cy); xr-=w+sp
    bw=max(lw)+80; bh=n*lh+30
    return spr,pos,bw,bh
@functools.lru_cache(maxsize=None)
def plate(w,h):
    d=D(w,h); d.rrect((2,2,w-2,h-2),30,fill=(48,38,40,232),outline=RED,width=3); return d.done()
def draw_caption(fr,t,cy=1455):
    for i,c in enumerate(CAPS):
        end=c['t1']+0.28
        if i+1<len(CAPS): end=min(end,CAPS[i+1]['t0'])
        if not (c['t0']<=t<end): continue
        spr,pos,bw,bh=cap_layout(i)
        fade=min(prog(t,c['t0'],c['t0']+0.1),1-prog(t,end-0.1,end))
        # Captions are unboxed (brand rule). Real projects use captions.draw_word_caption
        # with MEASURED word onsets + an explicit style from plan/text-direction.json.
        for k,s in enumerate(spr):
            tw=c['times'][k]
            if t<tw: continue
            a=prog(t,tw,tw+0.10); sc=0.78+0.22*e_back(prog(t,tw,tw+0.22),2.4)
            x,y=pos[k]; paste(fr,s,540+x,cy+y+(1-a)*16,scale=sc,alpha=a*fade)
# ---------- shared sprites ----------
@functools.lru_cache(maxsize=None)
def term_spr(term,col=WHITE):
    ts=text_sprite(term,44,col,False); w=ts.shape[1]+52; h=84
    d=D(w,h); d.rrect((2,2,w-2,h-2),h//2,fill=(26,26,32,240),outline=RED,width=3); base=d.done()
    over(base,ts,(w-ts.shape[1])//2,(h-ts.shape[0])//2); return base
@functools.lru_cache(maxsize=None)
def card_spr(label,tag,kind,hot=False):
    w,h=440,190; d=D(w,h)
    d.rrect((2,2,w-2,h-2),30,fill=(26,26,32,245),outline=(RED if hot else (113,113,122)),width=4 if hot else 3)
    d.rrect((w-16,40,w-6,h-40),5,fill=RED)
    base=d.done(); ic=icon(kind,128)
    over(base,ic,w-34-128,(h-128)//2)
    t1=text_sprite(label,50,WHITE,True)
    if t1.shape[1]>250: t1=text_sprite(label,int(50*250/t1.shape[1]),WHITE,True)
    t2=text_sprite(tag,28,(163,162,160),False)
    cx=(w-34-128-14)//2+14
    over(base,t1,cx-t1.shape[1]//2,52-t1.shape[0]//2+30); over(base,t2,cx-t2.shape[1]//2,128+4)
    return base
@functools.lru_cache(maxsize=None)
def jbubble():
    d=D(380,100); d.rrect((2,2,378,98),40,fill=(70,70,78,230)); d.poly([(60,96),(40,140),(110,96)],fill=(70,70,78,230)) if False else None
    b=d.done(); ts=text_sprite("i7 · 16GB · RTX",38,(191,186,183),False); over(b,ts,(380-ts.shape[1])//2,(100-ts.shape[0])//2); return b
def sparkles(fr,t,cx,cy,rx,ry,n,seed,cols=(YEL,WHITE),sz=(14,26),speed=3.0):
    rnd=random.Random(seed)
    for i in range(n):
        a=rnd.uniform(0,6.28); rr=rnd.uniform(0.7,1.0); ph=rnd.uniform(0,6.28); s=rnd.randint(*sz)
        k=0.5+0.5*math.sin(t*speed+ph); paste(fr,sparkle(s,cols[i%len(cols)]),cx+rx*rr*math.cos(a),cy+ry*rr*math.sin(a),scale=0.3+0.9*k,rot=t*40+i*20,alpha=0.35+0.65*k)
# ================= SCENES =================
def scene1(fr,t):
    lt=t-B[0]; hot=prog(lt,3.0,3.25)
    pulse=1+0.02*math.sin(lt*3)
    red_circle(fr,540,1000,520*e_elastic(prog(lt,0,0.7))*pulse,RED if lt<3.1 else DRED,0.95)
    if lt>=3.1: ring(fr,540,1000,520+ (lt-3.1)*20,(243,242,241),3,alpha=max(0,0.5-(lt-3.1)*0.4))
    ring(fr,540,300,60+500*prog(lt,0.1,0.7),RED,6,alpha=0.7*(1-prog(lt,0.1,0.7))) if 0.1<lt<0.7 else None
    # price
    n=int(25000*e_out(prog(lt,0.1,1.1))); col=INK2 if lt<3.1 else RED
    sh=(math.sin(lt*70)*9 if 3.1<lt<3.6 else 0)
    scl=1+0.22*max(0,1-abs(lt-0.12)/0.25)
    txt(fr,f"{n:,} ج.م",540+sh,300,118,col,scale=scl*(1 if lt<3.1 else 0.96),alpha=prog(lt,0,0.15))
    if lt>3.1:
        wd=text_sprite("25,000 ج.م",118,col,True,5).shape[1]*0.96*e_out(prog(lt,3.1,3.45))
        fill_rect(fr,540+sh-wd/2,296,540+sh+wd/2,306,INK2,1.0)
        c=prog(lt,3.15,3.5); paste(fr,pill(400,92,(3,3,3),240),540,430,scale=c,alpha=c)
        txt(fr,"بعد 30 يوم",540,430,56,YEL,scale=c,alpha=c)
    # buyer
    bob=-abs(math.sin(lt*9))*20*(1-hot) if lt<3.2 else 0
    gy=1385+bob
    if lt<3.2:
        sc=1.15*(1+0.025*max(0,math.sin(lt*9))); paste(fr,person((113,113,122),'excited','hold',blink=bl(lt)),540,gy,scale=sc,anchor=(0.5,1.0))
    else:
        x=540+(math.sin(lt*60)*8 if lt<3.8 else 0); k=prog(lt,3.2,3.6)
        paste(fr,person((113,113,122),'frustrated','hold'),x,1385+14*k,scale=1.15*(1-0.02*k),rot=-2.5*k,anchor=(0.5,1.0))
    # laptop in hands
    lscr='glow' if lt<3.2 else 'bad'
    lx=540+(math.sin(lt*60)*7 if 3.2<lt<3.8 else 0); ly=985+(14 if lt>=3.2 else bob)
    paste(fr,laptop(430,lscr),lx,ly)
    if lt<3.2:
        sparkles(fr,lt,540,900,330,200,9,5,(YEL,WHITE),(12,24),4)
    # bills
    for i in range(9):
        t0=0.5+i*0.33 if i<2 else 3.4+(i-2)*0.28
        if lt<t0: continue
        u=(lt-t0)/1.8
        if u>1: continue
        rnd=random.Random(i*13+1); vx=(1 if i%2 else -1)*rnd.uniform(300,470); 
        x=540+vx*u; y=1010-300*u+rnd.uniform(-30,30)-120*math.sin(u*3.1)*0; rot=rnd.uniform(-200,200)*u
        paste(fr,bill(130),x,y,rot=rot,alpha=1-prog(u,0.65,1),scale=0.9+0.2*u)
    if 3.3<lt<5.0:
        k=prog(lt,3.3,3.7); txt(fr,"- 25,000",770,1140-170*prog(lt,3.3,5.0),64,(243,242,241),rtl=False,alpha=k*(1-prog(lt,4.6,5.0)),stroke=5,scolor=(159,8,3))
def crowd_person(i):
    shirts=[(113,113,122),(217,127,104),(113,113,122),(113,113,122),(113,113,122),(203,39,27)]
    skins=[(217,127,104),(217,127,104),(213,174,166),(217,127,104),(217,127,104),(213,174,166)]
    ex=['frustrated','confused']
    return person(shirts[i%6],ex[i%2],'shrug' if i%2 else 'stand',skin=skins[i%6])
TERMS=[("i7-13700H",WHITE),("16GB DDR5",YEL),("RTX 4060",WHITE),("1TB NVMe",YEL),("144Hz",YEL),("45W TDP",WHITE),("IPS",WHITE),("Gen 4",YEL),("DDR5 4800",WHITE),("OLED",YEL),("6GB VRAM",WHITE),("2.5K",YEL)]
def scene2(fr,t):
    lt=t-B[1]
    red_circle(fr,540,960,440,(217,127,104),0.30,60)
    ck=e_back(prog(lt,0.2,0.6)); paste(fr,pill(330,88,RED),540,250,scale=ck,alpha=min(1,ck)); txt(fr,"المشكلة",540,250,52,WHITE,scale=ck)
    # crowd
    ca=1-prog(t,8.0,8.9)
    if ca>0:
        for i in range(6):
            t0=6.3+i*0.14; k=e_back(prog(t,t0,t0+0.4))
            x=150+i*156+(0 if ca==1 else -60*(1-ca)); by=1110-(1-ca)*40
            paste(fr,crowd_person(i),x,by,scale=0.5*k,anchor=(0.5,1.0),alpha=ca)
            txt(fr,'؟',x,by-0.5*780-30+math.sin(t*5+i)*6,80,GOLD if i%2 else RED,scale=k,alpha=ca,stroke=4)
    # buyer
    enter=e_out(prog(t,8.0,8.9))
    bx=-200+(270+200)*enter
    ex='smile' if t<10.3 else 'confused'; pose='stand' if t<12.95 else 'shrug'
    sway=math.sin(t*4)*1.5 if t>10.3 else 0
    if enter>0: paste(fr,person((113,113,122),ex,pose,blink=bl(t,1.1)),bx,1380,scale=1.0,rot=sway,anchor=(0.5,1.0))
    # seller
    se=e_out(prog(t,8.3,9.1)); sx=1300-(1300-810)*se
    talking=9.65<=t<15.2
    sex='confident' if not talking else ('talk1' if int(t*8)%2==0 else 'talk2')
    if t>=15.2: sex='confident'
    if se>0: paste(fr,person((159,8,3),sex,'talk',skin=(217,127,104),hairstyle='slick',tie=(216,215,213),collar=(243,242,241),blink=bl(t,2.3)),sx,1380,scale=1.0,flipx=True,anchor=(0.5,1.0))
    # jargon
    mouth=(720,640)
    swirl=e_io(prog(t,12.95,13.9))
    for i,(w,c) in enumerate(TERMS):
        t0=9.7+i*0.24
        if t<t0: continue
        rnd=random.Random(i*7+3); tx=rnd.uniform(160,900); ty=rnd.uniform(430,900)
        k=prog(t,t0,t0+0.7)
        fx=lerp(mouth[0],tx,e_out(k))+math.sin(t*2+i)*18; fy=lerp(mouth[1],ty,e_out(k))+math.cos(t*2.3+i)*14
        ang=i*6.28/len(TERMS)+(t-12.95)*1.7
        ox=330+300*math.cos(ang); oy=560+170*math.sin(ang)
        x=lerp(fx,ox,swirl); y=lerp(fy,oy,swirl)
        a=e_back(prog(t,t0,t0+0.3)); fa=1-prog(t,15.2,15.7)
        if fa>0: paste(fr,term_spr(w,c),x,y,scale=min(a,1.1)*(0.9+0.1*math.sin(t*3+i)),rot=math.sin(t*3+i)*6+swirl*math.sin(t*4+i)*8,alpha=fa)
    # question marks + bubble
    if t>=11.0:
        for j,(dx,dy) in enumerate([(-120,-120),(130,-190),(-30,-250)]):
            k=e_back(prog(t,11.0+j*0.35,11.5+j*0.35)); txt(fr,'؟',bx+dx,980+dy+math.sin(t*4+j)*8-110,110,GOLD if j%2 else RED,scale=k,stroke=0)
    if t>=13.8:
        k=e_back(prog(t,13.8,14.2)); paste(fr,bubble(330,110,(243,242,241),'bc',255,INK2),270,455,scale=k,alpha=min(1,k))
        txt(fr,"يعني إيه؟",270,455,56,BLACK,scale=k)
def scene3(fr,t):
    lt=t-B[2]
    k=e_elastic(prog(lt,0,0.8))
    red_circle(fr,540,1000,500*k,RED,1.0,50)
    ring(fr,540,1000,548*k,(243,242,241),3,alpha=0.35)
    # (no logo slot: this studio has no logo by design)
    # medo
    m=Medo('medo_wave',930); en=e_back(prog(lt,0.15,0.75),1.4)
    y=1440+(1-en)*700+math.sin(lt*3)*5
    paste(fr,m,520,y,scale=1.0,rot=math.sin(lt*7)*1.6,anchor=(0.5,1.0))
    hx,hy=520+0.30*m.shape[1],y-m.shape[0]+0.26*m.shape[0]
    for j in range(2):
        a=0.5+0.5*math.sin(lt*8+j*2.2); r=60+j*30
        d=D(260,260); d.arc((130-r,130-r,130+r,130+r),-50,50,(255,255,255,255),7); arc_spr=d.done()
        paste(fr,arc_spr,hx+86,hy+20,alpha=a*prog(lt,0.7,0.9),scale=1.0)
    sparkles(fr,lt,540,900,400,400,8,11,(WHITE,YEL),(10,20),3)
def scene4(fr,t):
    lt=t-B[3]
    red_circle(fr,540,1050,430,RED,0.92,40)
    c=e_back(prog(lt,0.2,0.65)); paste(fr,pill(420,92,RED),540,255,scale=c,alpha=min(1,c)); txt(fr,"الحلقة الأولى",540,255,52,WHITE,scale=c)
    c2=prog(lt,0.7,1.2); txt(fr,"لابتوب ولا كمبيوتر مكتبي؟",540,355-(1-c2)*20,60,INK2,alpha=c2)
    # devices
    k1=e_back(prog(lt,2.3,2.8)); k2=e_back(prog(lt,3.4,3.9))
    hl1=prog(lt,5.0,5.3)*(1-prog(lt,6.4,6.7)); hl2=prog(lt,6.5,6.8)*(1-prog(lt,7.8,8.1))
    if hl1>0: red_circle(fr,260,560,200,EMER,0.28*hl1,60)
    if hl2>0: red_circle(fr,815,560,200,TEAL,0.35*hl2,60)
    paste(fr,laptop(400,'glow'),245,560+math.sin(lt*2)*5,scale=k1,alpha=min(1,k1))
    paste(fr,desktop(300),820,545+math.sin(lt*2+1)*5,scale=k2,alpha=min(1,k2))
    paste(fr,pill(250,70,EMER),245,745,scale=k1,alpha=min(1,k1)); txt(fr,"لابتوب",245,745,42,(3,3,3),scale=k1)
    paste(fr,pill(330,70,TEAL),830,745,scale=k2,alpha=min(1,k2)); txt(fr,"كمبيوتر مكتبي",830,745,42,WHITE,scale=k2)
    speed_lines(fr,535,600,prog(lt,4.0,4.6),RED if not T['dark'] else WHITE)
    if 4.0<lt<4.7: ring(fr,535,600,60+300*prog(lt,4.0,4.7),RED,6,alpha=0.8*(1-prog(lt,4.0,4.7)))
    v=e_elastic(prog(lt,4.0,4.8)); pulse=1+0.05*math.sin(lt*5)
    paste(fr,circle_spr(58,RED,20),535,600,scale=v*pulse); txt(fr,"VS",535,600,54,WHITE,rtl=False,scale=v*pulse)
    m=Medo('medo_think',650); en=e_back(prog(lt,0.3,0.9),1.3)
    paste(fr,m,540,1410+(1-en)*600+math.sin(lt*2.4)*4,anchor=(0.5,1.0),rot=math.sin(lt*1.7)*1.2)
    # thought cloud
    tc=prog(lt,4.6,5.2)
    if tc>0:
        for j,(dx,dy,r) in enumerate([(440,860,10),(395,905,16),(345,955,22)]):
            paste(fr,circle_spr(r,(243,242,241),0),dx,dy,scale=e_back(prog(lt,4.6+j*0.15,5.0+j*0.15)))
        cl=e_back(prog(lt,5.0,5.5)); paste(fr,circle_spr(80,(243,242,241),0),240,1040,scale=cl*(1+0.03*math.sin(lt*4)))
        txt(fr,"؟",240,1030,120,RED,scale=cl,stroke=0)
PARTS=[("المعالج","CPU","cpu"),("الرامات","RAM","ram"),("التخزين","STORAGE","ssd"),("الشاشة","DISPLAY","display"),("كارت الشاشة","GPU","gpu"),("البطارية","BATTERY","battery")]
SLOTS=[(780,790),(300,790),(780,990),(300,990),(780,1190),(300,1190)]
def part_times():
    c=CAPS[12]; wt=c['times']; return [wt[0],wt[1],wt[2],wt[3],wt[4],wt[6]]
PT=part_times()
def scene5(fr,t):
    lt=t-B[4]
    red_circle(fr,540,420,330,(159,8,3),0.8,60)
    L=e_elastic(prog(lt,0.2,1.0)); lift=e_io(prog(lt,1.4,2.2))
    lx,ly=540,380
    paste(fr,laptop(540,'glow'),lx,ly-0*lift,scale=L*(1-0.0))
    # connector dashes + cards
    for i,(label,tag,kind) in enumerate(PARTS):
        t0=PT[i]-0.12
        if t<t0: continue
        sx,sy=SLOTS[i]; u=prog(t,t0,t0+0.6); k=e_back(u,1.5)
        x=lerp(lx,sx,e_out(u)); y=lerp(ly+60,sy,e_out(u))
        hot=(38.3<=t<43.3) and int((t-38.3)/0.8)%6==i
        paste(fr,card_spr(label,tag,kind,hot),x,y,scale=min(1.0,0.35+0.65*k),rot=(1-u)*(-14 if i%2 else 14),alpha=min(1,u*3))
    # beat pulses
    for b in (PT[0],PT[3]):
        r=prog(t,b-0.1,b+0.7)
        if 0<r<1: ring(fr,lx,ly,300+260*r,(243,242,241),3,alpha=0.5*(1-r))
    # K chips
    chips=[(38.4,40.2,"بالبلدي",YEL,BLACK),(40.3,41.6,"يعني إيه؟",RED,WHITE),(41.7,43.4,"بيأثر على استخدامك",EMER,(3,3,3))]
    for a,b,s,bgc,fc in chips:
        if a<=t<b+0.15:
            k=e_back(prog(t,a,a+0.3))*(1-prog(t,b,b+0.15))
            w=int(text_sprite(s,56,fc,True).shape[1]+90)
            paste(fr,pill(w,92,bgc),540,640,scale=k,alpha=min(1,k)); txt(fr,s,540,640,56,fc,scale=k)
def scene6(fr,t):
    lt=t-B[5]
    red_circle(fr,420,1100,430,RED,0.92,40)
    for sy in (520,780):
        fill_rect(fr,70,sy,1010,sy+14,(113,113,122)); fill_rect(fr,70,sy+14,1010,sy+22,(10,10,10))
    screens=['blank','dark','glow','blank','dark','blank','glow','dark']
    pick=2
    for i in range(8):
        row=i//4; col=i%4; x=200+col*225; y=520-row*0+ (260 if row else 0)
        if i==pick and lt>1.6: continue
        paste(fr,laptop(190,screens[i]),x,y,anchor=(0.5,1.0),alpha=0.9)
    # picked laptop flight
    if lt>1.2:
        u=e_io(prog(lt,1.7,2.7)); sx,sy=200+pick*225,520
        if lt<1.7: ring(fr,sx,sy-60,130+8*math.sin(lt*12),EMER,6,alpha=0.9)
        gx=lerp(sx,165,u); gy=lerp(sy-60,1060,u); sc=lerp(1.0,1.5,u)
        paste(fr,laptop(190,'glow'),gx,gy,scale=sc,rot=(1-u)*0+math.sin(lt*3)*2*u)
    # shopper
    wk=e_out(prog(lt,0.0,1.1)); x=-180+(430+180)*wk
    step=abs(math.sin(lt*10))*10*(1-wk) if wk<1 else 0
    nchk=int(clamp((lt-3.0)/0.35,0,5))
    ex='smile' if lt<2.7 else 'confident'
    paste(fr,person((217,127,104),ex,'paper',skin=(217,127,104),pants=(10,10,10),hair=(3,3,3),blink=bl(t,0.7)),x,1385-step,anchor=(0.5,1.0),scale=0.95,rot=math.sin(lt*3)*1.2)
    pp=paper_spec(190,nchk); paste(fr,pp,x+176,1385-step-0.95*780+0.95*250,anchor=(0.5,0.9),rot=10)
    # seller far
    sk=e_back(prog(lt,2.9,3.4))
    if sk>0:
        paste(fr,person((159,8,3),'confident','stand',skin=(217,127,104),hairstyle='slick',tie=(216,215,213),collar=(243,242,241)),935,1200,scale=0.5*sk,anchor=(0.5,1.0),alpha=min(1,sk))
        ba=prog(lt,3.2,3.6)*(1-prog(lt,5.1,5.4))
        paste(fr,jbubble(),870,730,scale=0.78,alpha=ba*0.9)
        if lt>3.8:
            c=e_back(prog(lt,3.8,4.2)); paste(fr,crossmark(96),870,730,scale=c,alpha=min(1,c)*(1-prog(lt,5.1,5.4)))
    if lt>4.5:
        r=prog(lt,4.5,5.3); ring(fr,x,900,300+260*r,EMER,6,alpha=0.7*(1-r))
        sparkles(fr,lt,x,900,300,400,7,3,(EMER,YEL,WHITE),(10,20),4)
def scene7(fr,t):
    lt=t-B[6]
    k=e_elastic(prog(lt,0,0.8)); red_circle(fr,620,1000,500*k,RED,1.0,50)
    ring(fr,620,1000,545*k,WHITE,3,alpha=0.3)
    e=e_elastic(prog(lt,0.5,1.3))
    paste(fr,circle_spr(100,(3,3,3),30),540,260,scale=e); ring(fr,540,260,100*e,RED,8); ring(fr,540,260,115*e+2*math.sin(lt*4),(243,242,241),2,alpha=0.4)
    m=Medo('medo_point',1010); en=e_back(prog(lt,0.15,0.75),1.3)
    mx,my=700,1445+(1-en)*700+math.sin(lt*3)*4
    paste(fr,m,mx,my,anchor=(0.5,1.0),rot=math.sin(lt*2)*0.8)
    tipx=mx-m.shape[1]/2+0.55*m.shape[1]; tipy=my-m.shape[0]+0.41*m.shape[0]
    # laptop
    lk=e_back(prog(lt,0.6,1.2)); paste(fr,laptop(330,'glow'),255,1160+math.sin(lt*2)*5,scale=lk,rot=-4,alpha=min(1,lk))
    # button
    bk=e_back(prog(lt,1.2,1.7)); done=lt>=4.9
    press=1-0.07*max(0,1-abs(lt-4.85)/0.12)
    bx,by=tipx-290,tipy+10
    paste(fr,follow_button(520,150,False,done),bx,by,scale=0.85*bk*press,alpha=min(1,bk)) if not done else paste(fr,follow_button(520,150,False,True),bx,by,scale=0.85*press)
    # cursor tap
    if 3.6<=lt<5.6:
        u=e_io(prog(lt,3.6,4.8)); cx_=lerp(bx-340,bx-70,u); cy_=lerp(by+330,by+40,u)
        paste(fr,cursor(90),cx_,cy_,scale=1.0-0.08*max(0,1-abs(lt-4.85)/0.12),alpha=1-prog(lt,5.2,5.6),anchor=(0.1,0.08))
    if lt>4.85:
        r=prog(lt,4.85,5.6); ring(fr,bx,by,200+300*r,EMER,6,alpha=0.8*(1-r))
        sparkles(fr,lt,bx,by,300,120,9,9,(EMER,WHITE,YEL),(12,24),5)
SCENES=[scene1,scene2,scene3,scene4,scene5,scene6,scene7]
def wipe(fr,t):
    for tb in B[1:-1]:
        d=t-tb
        if -0.2<d<0.2:
            if d<0: x0=W*(1-e_io(prog(d,-0.2,0))); fill_rect(fr,x0,0,W,H,RED); fill_rect(fr,x0-14,0,x0,H,WHITE)
            else: x1=W*(1-e_io(prog(d,0,0.2))); fill_rect(fr,0,0,x1,H,RED); fill_rect(fr,x1,0,x1+14,H,WHITE)
@functools.lru_cache(maxsize=None)
def chip_spr(label):
    ts=text_sprite(label,34,WHITE,True); w=ts.shape[1]+70
    d=D(w,64); d.rrect((2,2,w-2,62),31,fill=(60,48,50,238)); b=d.done(); over(b,ts,(w-ts.shape[1])//2,(64-ts.shape[0])//2); return b
def render_frame(t):
    k=max(0,min(6,int(np.searchsorted(B,t,side='right')-1))); dark=THEME[k]; T['dark']=bool(dark)
    ambient_t=decorative_time(t,MOTION_MODE)
    fr=bg_frame(k,ambient_t); dust(fr,ambient_t,dark)
    SCENES[k](fr,t)
    lt=t-B[k]; u=e_io(clamp(lt/(B[k+1]-B[k])))
    z=1+0.04*u if k%2==0 else 1.04-0.04*u
    sx,sy,fl=shake_flash(t)
    fr=camera(fr,z,14*math.sin(t*0.5+k)+sx,sy)
    if fl>0: fill_rect(fr,0,0,W,H,(243,242,241),fl)
    draw_caption(fr,t)
    if CHIP: paste(fr,chip_spr(CHIP),540,128,alpha=prog(t,0.05,0.4))
    fill_rect(fr,60,64,W-60,70,(243,242,241) if dark else (10,10,10),0.18); fill_rect(fr,60,64,60+(W-120)*t/B[-1],70,RED,1.0)
    wipe(fr,t)
    return np.clip(fr,0,255).astype(np.uint8)
