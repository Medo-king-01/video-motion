import numpy as np, cv2, os, sys
from scipy import ndimage as ndi
U=os.environ.get('UPLOADS','uploads/')  # folder holding the original poses
def save(name, rgb, alpha):
    ys,xs=np.where(alpha>8); y0,y1,x0,x1=ys.min(),ys.max(),xs.min(),xs.max()
    out=np.dstack([rgb,alpha])[y0:y1+1,x0:x1+1]
    cv2.imwrite(f'assets/{name}.png', cv2.cvtColor(out, cv2.COLOR_RGBA2BGRA)); print(name,out.shape)
def white_bg(fn,name):
    im=cv2.cvtColor(cv2.imread(U+fn),cv2.COLOR_BGR2RGB); H,W=im.shape[:2]
    mx=im.max(2).astype(int); mn=im.min(2).astype(int)
    white=(mn>=225)
    gray=(mx-mn<14)&(mn>118)&(np.arange(H)[:,None]>1230)
    cand=white|gray
    lab,n=ndi.label(cand)
    border=set(np.unique(np.concatenate([lab[0],lab[-1],lab[:,0],lab[:,-1]])))-{0}
    bg=np.isin(lab,list(border))
    fg=~bg
    fg=ndi.binary_fill_holes(fg)
    fg=ndi.binary_opening(fg,iterations=1)
    lab2,n2=ndi.label(fg); sizes=ndi.sum(fg,lab2,range(1,n2+1)); fg=lab2==(1+int(np.argmax(sizes)))
    a=ndi.binary_erosion(fg,iterations=1).astype(np.float32)
    a=cv2.GaussianBlur(a,(0,0),0.9)
    save(name,im,(a*255).astype(np.uint8))
def green(fn,name):
    im=cv2.cvtColor(cv2.imread(U+fn),cv2.COLOR_BGR2RGB).astype(np.float32)
    r,g,b=im[...,0],im[...,1],im[...,2]
    d=g-np.maximum(r,b)
    a=1-np.clip((d-25)/70,0,1)
    a=cv2.GaussianBlur(a,(0,0),0.7)
    # despill
    g2=np.minimum(g,np.maximum(r,b)+10); im[...,1]=np.where(d>0,g2,g)
    lab,n=ndi.label(a>0.5); sizes=ndi.sum(a>0.5,lab,range(1,n+1)); keep=lab==(1+int(np.argmax(sizes)))
    keep=ndi.binary_fill_holes(keep); a=a*ndi.binary_dilation(keep,iterations=2)
    save(name,im.astype(np.uint8),(a*255).astype(np.uint8))
if __name__=='__main__':
    # usage: python cutout.py white|green <file inside UPLOADS> <out name>   e.g. python cutout.py white wave.png medo_wave
    os.makedirs('assets',exist_ok=True)
    mode,fn,name=sys.argv[1:4]
    (white_bg if mode=='white' else green)(fn,name)
