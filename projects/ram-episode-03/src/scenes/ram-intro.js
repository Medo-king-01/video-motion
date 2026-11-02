// S01 — three consistent RAM modules, revealed right-to-left.
import { PALETTE as C } from '../lib/brand.js';
import { useFonts,family } from '../lib/fonts.js';
import { drawWordCaption } from '../lib/captions.js';
import { CAPTIONS_S01 } from '../captions-s01.js';
const clamp=(v,a=0,b=1)=>Math.max(a,Math.min(b,v));
const out=p=>1-Math.pow(1-clamp(p),3);
function rr(c,x,y,w,h,r){c.beginPath();c.roundRect(x,y,w,h,r);}
function poly(c,p,color){c.beginPath();c.moveTo(...p[0]);for(let i=1;i<p.length;i++)c.lineTo(...p[i]);c.closePath();c.fillStyle=color;c.fill();}
export async function init(){await useFonts([['Inter',800],['Inter',400],['Cairo',800]]);}
function module(c,cx,cy,t,at,label){
 const p=clamp((t-at)/.72);if(!p)return;
 const a=clamp(p*2.2),s=.78+.22*out(p),rise=100*(1-out(p)),w=154,h=570,x=cx-w/2,y=cy-h/2+rise;
 c.save();c.globalAlpha=a;c.translate(cx,cy+rise);c.scale(s,s);c.translate(-cx,-cy-rise);
 poly(c,[[x+w,y+18],[x+w+18,y+8],[x+w+18,y+h-20],[x+w,y+h]],C.inkShadow);
 poly(c,[[x+9,y],[x+w,y+18],[x+w+18,y+8],[x+26,y-10]],C.inkSoft);
 rr(c,x,y,w,h,12);c.fillStyle=C.ink;c.fill();c.lineWidth=5;c.strokeStyle=C.inkSoft;c.stroke();
 c.fillStyle=C.gray3;
 for(let i=0;i<6;i++){const yy=y+62+i*72;rr(c,x+29,yy,96,48,7);c.fill();c.fillStyle=C.gray1;rr(c,x+39,yy+9,76,30,4);c.fill();c.fillStyle=C.gray3;}
 c.fillStyle=C.inkShadow;rr(c,x+57,y-3,42,16,5);c.fill();
 for(let i=0;i<9;i++){rr(c,x+12+i*15,y+h-34,9,28,2);c.fillStyle=i%2?C.gray1:C.blush;c.fill();}
 c.fillStyle=C.red;rr(c,x+w-9,y+38,5,86,2);c.fill();c.restore();
 c.save();c.globalAlpha=a;c.textAlign='center';c.textBaseline='middle';c.direction='ltr';c.font=`800 72px ${family('Inter','latin')}`;c.fillStyle=C.salmon;c.fillText(label,cx,y-68);c.restore();
}
function background(c,W,H,t){
 const g=c.createLinearGradient(0,0,0,H);g.addColorStop(0,C.ink);g.addColorStop(1,C.inkShadow);c.fillStyle=g;c.fillRect(0,0,W,H);
 c.save();c.strokeStyle='rgba(201,197,194,.08)';c.lineWidth=1;const d=(t*7)%40;
 for(let x=-40+d;x<W+40;x+=40){c.beginPath();c.moveTo(x,0);c.lineTo(x,H);c.stroke();}
 for(let y=-40+d;y<H+40;y+=40){c.beginPath();c.moveTo(0,y);c.lineTo(W,y);c.stroke();}c.restore();
 const glow=c.createRadialGradient(W*.5,H*.47,20,W*.5,H*.47,W*.68);glow.addColorStop(0,'rgba(203,39,27,.08)');glow.addColorStop(1,'rgba(203,39,27,0)');c.fillStyle=glow;c.fillRect(0,0,W,H);
}
export function draw(c,t,{W,H}){
 background(c,W,H,t);c.save();c.textAlign='center';c.textBaseline='middle';c.direction='ltr';c.font=`800 30px ${family('Inter','latin')}`;c.fillStyle=C.gray3;c.fillText('MEMORY CAPACITY',W/2,310);c.restore();
 module(c,820,925,t,.55,'8GB');module(c,540,925,t,3.95,'16GB');module(c,260,925,t,7.45,'32GB');
 const p=clamp((t-9.5)/1.2);if(p){const x=-200+1480*out(p),g=c.createLinearGradient(x-90,0,x+90,0);g.addColorStop(0,'rgba(203,39,27,0)');g.addColorStop(.5,'rgba(203,39,27,.65)');g.addColorStop(1,'rgba(203,39,27,0)');c.fillStyle=g;c.fillRect(0,1290,1080,3);}
 c.save();c.textAlign='center';c.textBaseline='middle';c.direction='ltr';c.font=`600 26px ${family('Inter','latin')}`;c.fillStyle=C.gray4;c.globalAlpha=clamp((t-10.1)/.35);c.fillText('8GB     16GB     32GB',W/2,1370);c.restore();
 drawWordCaption(c,t,CAPTIONS_S01,{W,H,family:'Cairo',size:76,y:1455,color:C.paper,shadow:'rgba(0,0,0,.8)'});
}
