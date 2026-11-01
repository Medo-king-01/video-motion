import functools, math
from lib import *
from PIL import ImageFilter
OL=(18,16,20)
# ================= DEVICES =================
@functools.lru_cache(maxsize=None)
def laptop(w=520,screen='glow',tilt_open=True):
    lh=int(w*0.62); bh=int(w*0.05); tot=lh+bh+6; d=D(int(w*1.1),tot); ox=int(w*0.05)
    d.rrect((ox,0,ox+w,lh),w*0.035,fill=(34,34,40),outline=OL,width=4)
    sx0,sy0,sx1,sy1=ox+w*0.035,w*0.035,ox+w*0.965,lh-w*0.035
    col={'glow':(14,60,52),'bad':(70,14,18),'blank':(22,24,30),'dark':(16,16,20)}[screen]
    d.rrect((sx0,sy0,sx1,sy1),w*0.012,fill=col)
    cx,cy=(sx0+sx1)/2,(sy0+sy1)/2
    if screen=='glow':
        for i,(ww,c) in enumerate([(0.55,EMER),(0.38,TEAL),(0.46,(60,90,86))]):
            y=sy0+(sy1-sy0)*(0.22+i*0.17); d.rrect((sx0+w*0.06,y,sx0+w*0.06+w*ww,y+w*0.045),6,fill=c)
        d.circ(sx1-w*0.15,sy0+w*0.13,w*0.055,fill=YEL)
    elif screen=='bad':
        d.circ(cx,cy,w*0.15,fill=RED); d.line([(cx-w*.07,cy-w*.07),(cx+w*.07,cy+w*.07)],(255,255,255),w*.035); d.line([(cx+w*.07,cy-w*.07),(cx-w*.07,cy+w*.07)],(255,255,255),w*.035)
    elif screen=='blank': d.circ(cx,cy,w*0.05,fill=(70,74,84))
    d.rrect((0,lh+2,w*1.1,lh+2+bh),bh/2,fill=(196,196,204),outline=OL,width=3)
    d.rrect((w*0.55-w*0.09,lh+2,w*0.55+w*0.09,lh+2+bh*0.5),bh/3,fill=(150,150,158))
    return d.done()
@functools.lru_cache(maxsize=None)
def desktop(w=420):
    h=int(w*1.0); d=D(int(w*1.25),h+10)
    mw=int(w*0.78); mh=int(mw*0.6)
    d.rrect((0,0,mw,mh),12,fill=(34,34,40),outline=OL,width=4)
    d.rrect((14,14,mw-14,mh-14),6,fill=(14,60,52))
    for i,(ww,c) in enumerate([(0.5,EMER),(0.34,TEAL)]): d.rrect((34,36+i*48,34+mw*ww,60+i*48),6,fill=c)
    d.rect((mw/2-18,mh,mw/2+18,mh+int(w*0.14)),fill=(150,150,158),outline=OL,width=3)
    d.rrect((mw/2-int(w*0.18),mh+int(w*0.14),mw/2+int(w*0.18),mh+int(w*0.17)),8,fill=(196,196,204),outline=OL,width=3)
    kx=mw/2-int(w*0.3)
    d.rrect((kx,mh+int(w*0.24),kx+int(w*0.6),mh+int(w*0.31)),8,fill=(60,60,68),outline=OL,width=3)
    tx=int(w*0.84); th=int(w*0.88)
    d.rrect((tx,int(w*0.08),tx+int(w*0.4),int(w*0.08)+th),12,fill=(44,44,52),outline=OL,width=4)
    d.circ(tx+int(w*0.2),int(w*0.2),int(w*0.05),fill=RED)
    for i in range(3): d.rrect((tx+int(w*0.07),int(w*0.34)+i*int(w*0.06),tx+int(w*0.33),int(w*0.34)+i*int(w*0.06)+8),4,fill=(80,80,90))
    return d.done()
# ================= PART ICONS (200x200) =================
@functools.lru_cache(maxsize=None)
def icon(kind,s=170,color=WHITE):
    d=D(s,s); c=s/2; k=s/200.0; ac=RED
    if kind=='cpu':
        for i in range(5):
            p=40+i*30*1
            d.line([(p*k,22*k),(p*k,40*k)],color,6*k,False); d.line([(p*k,160*k),(p*k,178*k)],color,6*k,False)
            d.line([(22*k,p*k),(40*k,p*k)],color,6*k,False); d.line([(160*k,p*k),(178*k,p*k)],color,6*k,False)
        d.rrect((40*k,40*k,160*k,160*k),16*k,fill=(44,44,52),outline=color,width=6*k)
        d.rrect((72*k,72*k,128*k,128*k),8*k,fill=ac)
    elif kind=='ram':
        d.rrect((12*k,62*k,188*k,138*k),8*k,fill=(44,44,52),outline=color,width=6*k)
        for i in range(4): d.rrect(((28+i*38)*k,78*k,(54+i*38)*k,106*k),4*k,fill=ac if i%2==0 else color)
        for i in range(12): d.rect(((20+i*13.5)*k,138*k,(26+i*13.5)*k,152*k),fill=YEL)
    elif kind=='ssd':
        d.rrect((26*k,50*k,174*k,150*k),12*k,fill=(44,44,52),outline=color,width=6*k)
        d.rrect((44*k,68*k,100*k,100*k),6*k,fill=ac); d.rrect((112*k,68*k,156*k,100*k),6*k,fill=color)
        d.rrect((44*k,112*k,156*k,126*k),6*k,fill=GRAY); d.circ(158*k,134*k,6*k,fill=EMER)
    elif kind=='display':
        d.rrect((14*k,34*k,186*k,142*k),12*k,fill=(44,44,52),outline=color,width=6*k)
        d.rrect((28*k,48*k,172*k,128*k),6*k,fill=TEAL)
        d.poly([(28*k,128*k),(80*k,86*k),(110*k,112*k),(132*k,94*k),(172*k,128*k)],fill=EMER)
        d.circ(142*k,70*k,10*k,fill=YEL); d.rrect((70*k,150*k,130*k,162*k),5*k,fill=color)
    elif kind=='gpu':
        d.rrect((10*k,56*k,190*k,142*k),10*k,fill=(44,44,52),outline=color,width=6*k)
        for fx in (62,128):
            d.circ(fx*k,99*k,28*k,fill=(30,30,36),outline=color,width=5*k)
            for a in range(0,360,72):
                d.line([(fx*k,99*k),((fx+20*math.cos(math.radians(a)))*k,(99+20*math.sin(math.radians(a)))*k)],ac,5*k,False)
            d.circ(fx*k,99*k,5*k,fill=color)
        for i in range(10): d.rect(((22+i*10)*k,142*k,(27+i*10)*k,156*k),fill=YEL)
    elif kind=='battery':
        d.rrect((14*k,56*k,170*k,144*k),14*k,fill=(44,44,52),outline=color,width=6*k)
        d.rrect((170*k,82*k,188*k,118*k),5*k,fill=color)
        for i in range(3): d.rrect(((28+i*42)*k,70*k,(60+i*42)*k,130*k),6*k,fill=EMER)
        d.poly([(104*k,62*k),(84*k,104*k),(100*k,104*k),(92*k,142*k),(124*k,92*k),(106*k,92*k)],fill=YEL,outline=OL,width=2*k)
    return d.done()
# ================= PEOPLE =================
def _hair(d,cx,cy,r,col,style='curly'):
    if style=='curly':
        import random; rnd=random.Random(7)
        for a in range(190,351,16):
            x=cx+(r+4)*math.cos(math.radians(a)); y=cy+(r+4)*math.sin(math.radians(a))*0.95
            d.circ(x,y,r*0.40,fill=col,outline=OL,width=3)
        for a in range(205,336,22): d.circ(cx+(r*0.62)*math.cos(math.radians(a)),cy+(r*0.7)*math.sin(math.radians(a)),r*0.42,fill=col)
        d.circ(cx,cy-r*0.55,r*0.7,fill=col)
    else:
        d.ell((cx-r-6,cy-r-12,cx+r+6,cy+r*0.35),fill=col,outline=OL,width=3)
def _face(d,cx,cy,expr,skin,blink=False):
    ex=34; ey=-4
    E=(20,16,20)
    def eye(x,y,kind):
        if blink:
            d.line([(x-13,y+2),(x+13,y+2)],E,5); return
        if kind=='open': d.ell((x-12,y-17,x+12,y+17),fill=E); d.circ(x+4,y-7,5,fill=(255,255,255))
        elif kind=='big': d.ell((x-15,y-21,x+15,y+21),fill=E); d.circ(x+5,y-9,7,fill=(255,255,255)); d.circ(x-5,y+8,3.5,fill=(255,255,255))
        elif kind=='half': d.ell((x-12,y-12,x+12,y+14),fill=E); d.rect((x-14,y-14,x+14,y-3),fill=skin); d.line([(x-14,y-3),(x+14,y-3)],OL,4,False); d.circ(x+3,y+3,3.5,fill=(255,255,255))
        elif kind=='side': d.ell((x-12,y-16,x+12,y+16),fill=(255,255,255),outline=OL,width=3); d.circ(x+5,y-6,7,fill=E)
    def brow(x0,y0,x1,y1,w=7): d.line([(x0,y0),(x1,y1)],E,w)
    L,R=cx-ex,cx+ex
    if expr=='excited':
        eye(L,cy+ey,'big'); eye(R,cy+ey,'big')
        brow(L-16,cy-34,L+14,cy-40); brow(R-14,cy-40,R+16,cy-34)
        d.rrect((cx-26,cy+30,cx+26,cy+66),22,fill=(95,22,30),outline=OL,width=3); d.rect((cx-22,cy+33,cx+22,cy+42),fill=(255,255,255)); d.ell((cx-14,cy+50,cx+14,cy+68),fill=(222,80,96))
        d.circ(L-12,cy+28,11,fill=(236,120,110)); d.circ(R+12,cy+28,11,fill=(236,120,110))
    elif expr=='frustrated':
        eye(L,cy+ey+4,'half'); eye(R,cy+ey+4,'half')
        brow(L-18,cy-44,L+14,cy-28,8); brow(R+18,cy-44,R-14,cy-28,8)
        d.arc((cx-24,cy+44,cx+24,cy+84),200,340,E,6)
        for i in (-18,0,18): d.line([(cx+i,cy-96),(cx+i,cy-70)],(60,60,90),4,False)
        d.ell((R+30,cy-20,R+46,cy+8),fill=(120,200,240),outline=OL,width=2); d.poly([(R+38,cy-36),(R+30,cy-16),(R+46,cy-16)],fill=(120,200,240))
    elif expr=='confused':
        eye(L,cy+ey,'side'); eye(R,cy+ey,'side')
        brow(L-16,cy-30,L+14,cy-38); brow(R-14,cy-46,R+16,cy-30)
        d.line([(cx-22,cy+54),(cx-10,cy+46),(cx+2,cy+56),(cx+14,cy+46),(cx+24,cy+54)],E,6)
        d.ell((L-48,cy-12,L-32,cy+16),fill=(120,200,240),outline=OL,width=2); d.poly([(L-40,cy-28),(L-48,cy-8),(L-32,cy-8)],fill=(120,200,240))
    elif expr in('talk1','talk2'):
        eye(L,cy+ey,'open'); eye(R,cy+ey,'open'); brow(L-16,cy-36,L+14,cy-40); brow(R-14,cy-40,R+16,cy-36)
        if expr=='talk1': d.ell((cx-20,cy+36,cx+20,cy+72),fill=(95,22,30),outline=OL,width=3); d.ell((cx-11,cy+54,cx+11,cy+70),fill=(222,80,96))
        else: d.ell((cx-14,cy+44,cx+14,cy+62),fill=(95,22,30),outline=OL,width=3)
    elif expr=='confident':
        eye(L,cy+ey,'open'); eye(R,cy+ey,'open'); brow(L-16,cy-36,L+14,cy-40); brow(R-14,cy-46,R+16,cy-40)
        d.arc((cx-30,cy+22,cx+30,cy+70),20,160,E,7); d.circ(L-12,cy+28,10,fill=(236,120,110)); d.circ(R+12,cy+28,10,fill=(236,120,110))
    else: # smile
        eye(L,cy+ey,'open'); eye(R,cy+ey,'open'); brow(L-16,cy-36,L+14,cy-40); brow(R-14,cy-40,R+16,cy-36)
        d.arc((cx-28,cy+20,cx+28,cy+66),20,160,E,7)
@functools.lru_cache(maxsize=None)
def person(shirt,expr='smile',pose='stand',skin=(196,138,96),pants=(40,42,52),hair=(26,20,22),hairstyle='curly',tie=None,collar=None,blink=False):
    w,h=400,780; d=D(w,h); cx,cy=200,150
    arm_col=shirt
    def arm(pts,hand):
        d.line(pts,OL,60); d.line(pts,arm_col,52); d.circ(hand[0],hand[1],30,fill=OL); d.circ(hand[0],hand[1],26,fill=skin)
    # legs
    for x in (155,245):
        d.rrect((x-42,470,x+42,730),30,fill=pants,outline=OL,width=4); d.rrect((x-50,716,x+50,758),20,fill=(26,26,30),outline=OL,width=4)
    # back arms (drawn before torso for some poses)
    poses={
     'stand':[([(104,290),(84,410),(86,500)],(86,512)),([(296,290),(316,410),(314,500)],(314,512))],
     'hold':[([(104,290),(70,410),(150,440)],(160,446)),([(296,290),(330,410),(250,440)],(240,446))],
     'shrug':[([(104,290),(52,400),(40,330)],(38,316)),([(296,290),(348,400),(360,330)],(362,316))],
     'talk':[([(104,290),(84,410),(86,500)],(86,512)),([(296,290),(350,380),(360,296)],(362,270))],
     'paper':[([(104,290),(84,410),(86,500)],(86,512)),([(296,290),(350,350),(318,260)],(316,240))],
     'scratch':[([(104,290),(84,410),(86,500)],(86,512)),([(296,290),(356,210),(300,100)],(292,88))],
     'cross':[([(104,290),(90,400),(190,380)],(200,384)),([(296,290),(310,400),(210,380)],(200,384))],
    }
    arms=poses[pose]
    # torso
    d.rrect((84,246,316,500),70,fill=shirt,outline=OL,width=4)
    if collar: d.poly([(170,246),(230,246),(200,300)],fill=collar,outline=OL,width=3)
    if tie: d.poly([(190,296),(210,296),(218,380),(200,404),(182,380)],fill=tie,outline=OL,width=3)
    for pts,hand in arms: arm(pts,hand)
    # neck + head
    d.rrect((172,214,228,268),16,fill=skin,outline=OL,width=3)
    _hair(d,cx,cy,100,hair,hairstyle) if hairstyle=='curly' else None
    d.circ(cx,cy,100,fill=skin,outline=OL,width=4)
    d.circ(cx-100,cy+6,16,fill=skin,outline=OL,width=3); d.circ(cx+100,cy+6,16,fill=skin,outline=OL,width=3)
    if hairstyle=='curly':
        for a in range(205,336,26): d.circ(cx+(86)*math.cos(math.radians(a)),cy+(78)*math.sin(math.radians(a)),26,fill=hair)
        d.rect((cx-88,cy-6-70,cx+88,cy-60),fill=None)
    else:
        d.poly([(cx-102,cy-10),(cx-96,cy-72),(cx-40,cy-104),(cx+40,cy-108),(cx+98,cy-70),(cx+102,cy-10),(cx+70,cy-46),(cx-20,cy-62),(cx-70,cy-36)],fill=hair,outline=OL,width=3)
    _face(d,cx,cy,expr,skin,blink)
    return d.done()
@functools.lru_cache(maxsize=None)
def paper_spec(w=200,checks=5):
    h=int(w*1.25); d=D(w,h+10)
    d.rrect((0,0,w,h),10,fill=(250,248,242),outline=OL,width=4)
    for i in range(5):
        y=26+i*int(h/6.4); d.rrect((w*0.30,y,w*0.88,y+10),4,fill=(190,190,196))
        if i<checks: d.line([(w*0.08,y+6),(w*0.14,y+14),(w*0.24,y-2)],EMER,5)
    return d.done()
@functools.lru_cache(maxsize=None)
def follow_button(w=520,h=150,pressed=False,done=False):
    d=D(w,h); col=(60,60,68) if done else RED
    d.rrect((0,0,w,h),h*0.5,fill=col,outline=(255,255,255) if not done else (120,120,128),width=4)
    if done: d.line([(w*0.16,h*.52),(w*0.2,h*.66),(w*0.28,h*.36)],EMER,10); d.text((w*0.62,h*.5),'تمت المتابعة',46,WHITE,rtl=True)
    else:
        d.circ(w*0.17,h/2,h*0.28,fill=(255,255,255)); d.line([(w*0.17-15,h/2),(w*0.17+15,h/2)],RED,8); d.line([(w*0.17,h/2-15),(w*0.17,h/2+15)],RED,8)
        d.text((w*0.60,h*.5),'تابع',64,WHITE,rtl=True)
    return d.done()
@functools.lru_cache(maxsize=None)
def cursor(s=90):
    d=D(s,s); d.poly([(8,6),(8,62),(24,48),(36,76),(48,70),(36,44),(58,44)],fill=(255,255,255),outline=OL,width=4); return d.done()
