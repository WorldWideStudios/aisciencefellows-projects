import numpy as np, cv2, math, random, sys, subprocess
from PIL import Image, ImageDraw, ImageFont
W,H,FPS=1280,720,20
S=1.2; BENCH=640
BG=(20,32,31); TEAL=(93,202,165); CORAL=(240,153,123); AMB=(239,159,39); WHITE=(246,245,240); GREY=(154,161,158)
FD="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"; FB="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
_f={}
def font(sz,b=False):
    k=(sz,b)
    if k not in _f: _f[k]=ImageFont.truetype(FB if b else FD,sz)
    return _f[k]
ss=lambda x:x*x*(3-2*x)
cl=lambda x,a=0,b=1:max(a,min(b,x))
# ---------- scene constants
TRAYH=24; ARS=(600,540); L1=L2=270; HOME=(640,330)
LEDGE=[BENCH-S*z for z in (4,69,149,229)]
SHA,SHB=30,200; SHW=156
RX=865; RLEDGE=[626,562,498,434]
BOXX=[960,1014,1068,1122]; BOXTOP=580
PAD=(450,BENCH)
TR={'PERF-5':((140,160,160),'A',0),'GRID-4':(AMB,'A',2),'HEX-2':(TEAL,'B',2),'SCREEN-1':((133,183,235),'B',1),'PAN':((180,185,182),'B',0)}
def src(n):
    c,sh,lv=TR[n]; x=(SHA if sh=='A' else SHB)+SHW/2; return (x,LEDGE[lv]-TRAYH)
STACK=['PAN','SCREEN-1','HEX-2','GRID-4']
SLOT={n:RLEDGE[i] for i,n in enumerate(STACK)}
# ---------- dots
rng=random.Random(7); dots=[]
for cls,n in enumerate([24,30,40,30]):
    for _ in range(n):
        dots.append(dict(cls=cls,ux=rng.uniform(-1,1),uy=rng.random(),th=0.0 if cls==0 else rng.uniform(0,0.58),
          dx=rng.uniform(-1,1),dy=rng.uniform(-1,1),s=rng.random(),fx=rng.uniform(-1,1),fy=rng.uniform(-1,1),fl=rng.uniform(0,1),bj=rng.uniform(-1,1)))
for d in [d for d in dots if d['cls']==1][:5]: d['th']=rng.uniform(.72,.88)
[d for d in dots if d['cls']==2][0]['th']=.95
P1,P2=.65,.9
DCOL=[(120,84,50),(196,160,100),(150,160,70),(130,130,125)]; DR=[4.2,3.4,2.6,2.2]
FINAL=['GRID-4','HEX-2','SCREEN-1','PAN']
# ---------- timeline
segs=[]; cur=HOME; T=0.0; ev={n:[] for n in TR}; PH={}; tilt={}; gone={}; holds=[]
def mv(p,dur,hold=0):
    global T,cur
    segs.append((T,T+dur,cur,p)); T+=dur; cur=p
    if hold: segs.append((T,T+hold,p,p)); T+=hold
def stay(until):
    global T
    if until>T: mv(cur,until-T)
stay(10.0); PH['stack']=[T]
for n in STACK:
    sx,sy=src(n); gy=sy; ry=SLOT[n]-TRAYH
    mv((sx,gy-70),1.0); mv((sx,gy),.4); tg=T; mv((sx,gy-60),.35); mv((RX,ry-70),1.1); mv((RX,ry),.45); tr=T; mv((RX,ry-60),.3)
    ev[n].append(dict(g=tg-.0,r=tr,dest=(RX,SLOT[n]-TRAYH),src=(sx,sy)))
mv(HOME,.9); PH['stack'].append(T); PH['sample']=[T,T+1.6]; stay(T+1.6)
def agit(name,dur): 
    global T
    PH[name]=[T,T+dur]; stay(T+dur)
def verify(name):
    global T
    t0=T; gy=SLOT['GRID-4']-TRAYH
    mv((RX,gy-70),.7); mv((RX,gy),.35); tg=T; mv((RX,gy-60),.3); mv((450,500),.9); h0=T; mv((450,500),1.3); h1=T
    mv((RX,gy-60),.9); mv((RX,gy),.35); tr=T; mv((RX,gy-70),.3); mv(HOME,.5)
    ev['GRID-4'].append(dict(g=tg,r=tr,dest=(RX,SLOT['GRID-4']-TRAYH),src=(RX,SLOT['GRID-4']-TRAYH))); PH[name]=[t0,T]; holds.append((name,h0,h1))
agit('ag1',3.0); verify('v1'); agit('ag2',2.6); verify('v2'); PH['collect']=[T]
for i,n in enumerate(reversed(STACK)):
    gy=SLOT[n]-TRAYH; bx=BOXX[i]
    mv((RX,gy-70),.8); mv((RX,gy),.35); tg=T; mv((RX,gy-60),.3); mv((bx,500),.9); tl=T+.1; mv((bx,500),1.3); tgone=T
    ev[n].append(dict(g=tg,r=1e9,dest=None,src=(RX,SLOT[n]-TRAYH))); tilt[n]=(tl,i); gone[n]=tgone
mv(HOME,.9); PH['collect'].append(T); PH['outro']=[T,T+3.5]; TOTAL=T+3.5
PH['observe']=[2.5,5.5]; PH['plan']=[5.5,7.5]; PH['pre']=[7.5,10.0]
def eff(t):
    for a,b,p,q in segs:
        if a<=t<=b:
            u=ss((t-a)/(b-a)) if b>a else 1
            return (p[0]+(q[0]-p[0])*u,p[1]+(q[1]-p[1])*u)
    return cur if t>0 else HOME
def tray_loc(n,t):
    pos=src(n); att=False
    for e in ev[n]:
        if t<e['g']: return pos,False,e
        if t<e['r']: x,y=eff(t); return (x,y),True,e
        pos=e['dest'] if e['dest'] else pos
    return pos,False,None
# ---------- drawing
tx=[]
def text(x,y,s,sz=16,col=WHITE,b=False,anc='l'): tx.append((x,y,s,sz,col,b,anc))
def rect(im,x0,y0,x1,y1,col,th=-1): cv2.rectangle(im,(int(x0),int(y0)),(int(x1),int(y1)),col,th,cv2.LINE_AA)
def poly(im,pts,col): cv2.fillPoly(im,[np.array(pts,np.int32)],col,cv2.LINE_AA)
def circ(im,x,y,r,col,th=-1): cv2.circle(im,(int(x),int(y)),max(1,int(round(r))),col,th,cv2.LINE_AA)
def line(im,a,b,col,th): cv2.line(im,(int(a[0]),int(a[1])),(int(b[0]),int(b[1])),col,th,cv2.LINE_AA)
def blend(im,over,a): im[:]=cv2.addWeighted(im,1-a,over,a,0)
def draw_tray(im,n,pos,ang=0,alpha=1.0,pivot=None):
    col=TR[n][0]; x,y=pos   # top-center
    hw=65
    pts=np.array([[-hw,0],[hw,0],[hw-6,TRAYH],[-hw+6,TRAYH]],float)
    if ang:
        a=math.radians(ang); R=np.array([[math.cos(a),-math.sin(a)],[math.sin(a),math.cos(a)]]); pts=pts@R.T
    pts=pts+np.array([x,y])
    ov=im.copy() if alpha<1 else im
    poly(ov,pts,col)
    for k in range(-5,6):   # mesh ticks
        p=np.array([[k*11,3],[k*11,TRAYH-4]],float)
        if ang: p=p@R.T
        p=p+np.array([x,y]); line(ov,p[0],p[1],tuple(int(c*.6) for c in col),1)
    if alpha<1: blend(im,ov,alpha)
    if ang==0: text(x,y+TRAYH/2,n.replace('PAN','CATCH PAN'),11,(20,32,31),True,'c')
def dot_tray(d,t):
    """which tray (or special) the dot is on"""
    if t<PH['sample'][0]: return 'dish'
    p=P1 if t<PH['v1'][0]+.0 else None
    return None
def prog(t):
    if t<PH['ag1'][0]: return 0.0
    if t<PH['ag1'][1]: return P1*ss((t-PH['ag1'][0])/3.0)
    if t<PH['ag2'][0]: return P1
    if t<PH['ag2'][1]: return P1+(P2-P1)*ss((t-PH['ag2'][0])/2.6)
    if t<PH['collect'][0]: return P2
    return 1.01
def purity(t):
    p=prog(t); top=[d for d in dots if d['cls']==0 or d['th']>p]; return 100*24/len(top)
def shakeoff(t):
    for k in ('ag1','ag2'):
        a,b=PH[k]
        if a<=t<=b: u=(t-a)/(b-a); return 5*math.sin(2*math.pi*3.2*(t-a))*math.sin(math.pi*u)**.5
    return 0
def render(t):
    global tx; tx=[]
    im=np.full((H,W,3),BG,np.uint8)
    rect(im,0,BENCH,W,H,(26,42,40)); line(im,(0,BENCH),(W,BENCH),(58,74,71),2)
    # shelves
    for x0,nm in ((SHA,'SHELF A'),(SHB,'SHELF B')):
        rect(im,x0,BENCH-S*304,x0+SHW,BENCH,(48,64,68)); rect(im,x0,BENCH-S*304,x0+SHW,BENCH,(70,92,98),2)
        for y in LEDGE: rect(im,x0-4,y,x0+SHW+4,y+5,(140,170,180))
        text(x0+SHW/2,BENCH+22,nm,14,GREY,True,'c')
    # camera + pad
    rect(im,PAD[0]-50,BENCH-8,PAD[0]+50,BENCH,(90,110,110)); line(im,(PAD[0]+60,BENCH),(PAD[0]+60,300),(90,110,110),6); line(im,(PAD[0]+60,300),(PAD[0],300),(90,110,110),6)
    rect(im,PAD[0]-22,288,PAD[0]+22,312,(200,200,195)); circ(im,PAD[0],312,8,(30,40,40))
    imaging=any(a<=t<=b for _,a,b in holds) or PH['observe'][0]<=t<PH['stack'][0]
    if imaging:
        ov=im.copy(); poly(ov,[(PAD[0]-6,318),(PAD[0]+6,318),(PAD[0]+55,BENCH-8),(PAD[0]-55,BENCH-8)],TEAL); blend(im,ov,.12)
    text(PAD[0],BENCH+22,'CAMERA',14,GREY,True,'c')
    # rack
    sh=shakeoff(t)
    for sx in (RX-78,RX+78): rect(im,sx-3+sh,400,sx+3+sh,BENCH,(110,120,118))
    rect(im,RX-82+sh,396,RX+82+sh,402,(110,120,118))
    for y in RLEDGE: rect(im,RX-76+sh,y,RX+76+sh,y+4,(70,84,84))
    text(RX,BENCH+22,'SIEVE RACK',14,GREY,True,'c')
    # boxes
    for i,bx in enumerate(BOXX):
        rect(im,bx-23,BOXTOP,bx+23,BENCH,(40,56,58)); rect(im,bx-23,BOXTOP,bx+23,BENCH,(150,170,170),2); text(bx,BENCH+22,'L%d'%(i+1),14,GREY,True,'c')
    text((BOXX[0]+BOXX[-1])/2,BOXTOP-14,'COLLECTION BOXES',12,GREY,True,'c')
    # trays
    pos={}; 
    for n in TR:
        p,att,e=tray_loc(n,t)
        inrack=(not att) and n in STACK and t>=ev[n][0]['r']
        if inrack and not (n in gone and t>=gone[n]): p=(p[0]+sh,p[1])
        pos[n]=(p,att)
    # dots -> positions
    p=prog(t); tray_dots={n:[] for n in TR}; free=[]
    for d in dots:
        if t<PH['sample'][0]: free.append((PAD[0]+d['dx']*32,BENCH-12+d['dy']*5,d['cls'])); continue
        cur_t='GRID-4' if (d['cls']==0 or p<d['th']) else FINAL[d['cls']]
        if t<PH['sample'][0]+1.6:
            q=cl((t-PH['sample'][0]-d['s']*.5)/1.0)
            if q<1:
                gp=pos['GRID-4'][0]; ex=gp[0]+d['ux']*50; ey=gp[1]-DR[d['cls']]-d['uy']*9
                sx0=PAD[0]+d['dx']*32; sy0=BENCH-12+d['dy']*5; u=ss(q)
                free.append((sx0+(ex-sx0)*u, sy0+(ey-sy0)*u-90*math.sin(math.pi*u), d['cls'])); continue
        tray_dots[cur_t].append(d)
    tilt_i={n:(tilt[n] if n in tilt else None) for n in TR}
    boxdots=[]
    for n in TR:
        pp,att=pos[n]; fade=1.0
        if n in gone and t>=gone[n]: fade=1-cl((t-gone[n])/.4)
        ang=0
        if n in tilt:
            tl,bi=tilt[n]; ang=100*ss(cl((t-tl)/.5))
        if fade>0:
            draw_tray(im,n,pp,ang if att else 0,fade)
            if ang and att: pass
        for d in tray_dots[n]:
            x=pp[0]+d['ux']*50; y=pp[1]-DR[d['cls']]-d['uy']*9
            if n in tilt:
                tl,bi=tilt[n]; tt=t-(tl+.25+d['s']*.5)
                if tt>=0:
                    bx=BOXX[bi]+d['bj']*16; yf=BENCH-4-DR[d['cls']]-d['fl']*18-bi*0
                    y0=pp[1]; g=900.; tf=math.sqrt(2*max(1,yf-y0)/g)
                    if tt<tf: x=pp[0]+(bx-pp[0])*(tt/tf); y=y0+.5*g*tt*tt
                    else: x,y=bx,yf
            if n in gone and t>=gone[n] and not (n in tilt and t-(tilt[n][0]+.25+d['s']*.5)>=0): continue
            boxdots.append((x,y,d['cls']))
    for x,y,c in boxdots+free: circ(im,x,y,DR[c],DCOL[c])
    # arm
    ex,ey=eff(t); wx,wy=ex,ey-34
    dx,dy=wx-ARS[0],wy-ARS[1]; dd=cl(math.hypot(dx,dy),60,L1+L2-.5); ang=math.atan2(dy,dx)
    A=math.acos(cl((L1*L1+dd*dd-L2*L2)/(2*L1*dd),-1,1)); cands=[(ARS[0]+L1*math.cos(ang+s*A),ARS[1]+L1*math.sin(ang+s*A)) for s in(1,-1)]
    el=min(cands,key=lambda q:q[1]); wxx,wyy=ARS[0]+dd*math.cos(ang),ARS[1]+dd*math.sin(ang)
    rect(im,ARS[0]-40,ARS[1]+10,ARS[0]+40,BENCH,(60,60,58)); rect(im,ARS[0]-26,ARS[1]-14,ARS[0]+26,ARS[1]+30,(232,230,220))
    line(im,ARS,el,(120,118,110),26); line(im,ARS,el,(232,230,220),20)
    line(im,el,(wxx,wyy),(120,118,110),22); line(im,el,(wxx,wyy),(232,230,220),16)
    for q in (ARS,el): circ(im,q[0],q[1],14,(40,40,40)); circ(im,q[0],q[1],9,AMB)
    att_any=any(pos[n][1] for n in TR); gw=22 if att_any else 34
    line(im,(wxx,wyy),(wxx,wyy+22),(60,60,58),12)
    for s in(-1,1): line(im,(wxx+s*gw/2,wyy+14),(wxx+s*gw/2,wyy+36),(240,150,50),5)
    circ(im,wxx,wyy,9,(40,40,40)); circ(im,wxx,wyy,5,AMB)
    text(ARS[0],ARS[1]+52,'SO-101',13,(20,32,31),True,'c')
    return im
# ---------- HUD
STEPS=['OBSERVE','PLAN','PREFLIGHT','STACK','AGITATE','VERIFY','COLLECT']
def active(t):
    r=lambda k:PH[k][0]<=t<PH[k][1]
    if r('observe'):return 0
    if r('plan'):return 1
    if r('pre'):return 2
    if PH['stack'][0]<=t<PH['sample'][1]:return 3
    if r('ag1') or r('ag2'):return 4
    if r('v1') or r('v2'):return 5
    if PH['collect'][0]<=t<PH['collect'][1]:return 6
    return -1
def feed(im,t):
    x0,y0,w,h=40,108,300,160
    rect(im,x0,y0,x0+w,y0+h,(10,18,18)); rect(im,x0,y0,x0+w,y0+h,(80,100,98),2)
    text(x0+8,y0+6,'CAMERA FEED',11,GREY,True)
    obs=PH['observe'][0]<=t<PH['stack'][0]
    hold=[(n,a,b) for n,a,b in holds if a-.3<=t<=b]
    if obs:
        cx,cy=x0+w/2,y0+h/2+6; ell=lambda c:circ(im,cx,cy,70,c,2); ell((90,110,108))
        for i,d in enumerate(dots):
            fx,fy=cx+d['fx']*50,cy+d['fy']*38*(1 if d['fx']**2+d['fy']**2<1 else .5)
            if d['fx']**2+d['fy']**2>1: fx,fy=cx+d['fx']*35,cy+d['fy']*35
            circ(im,fx,fy,DR[d['cls']]*.8,DCOL[d['cls']])
            k=(t-3.0)/2.2
            if d['cls']<3 and i%6==0 and k>i/len(dots):
                rect(im,fx-7,fy-7,fx+7,fy+7,TEAL,1)
                if i%12==0: text(fx+8,fy-16,['5.2','3.1','1.8'][d['cls']]+' mm',10,TEAL,True)
        text(x0+8,y0+h-20,'YOLO + contours: agree',11,TEAL,True)
    elif hold:
        n,a,b=hold[0]; p=P1 if n=='v1' else P2
        cx,cy=x0+w/2,y0+h/2
        rect(im,cx-90,cy-45,cx+90,cy+45,(40,54,54),2)
        for d in dots:
            if d['cls']==0 or d['th']>p:
                fx,fy=cx+d['ux']*80,cy+(d['uy']-.5)*70
                circ(im,fx,fy,DR[d['cls']]*1.1,DCOL[d['cls']])
                if d['cls']!=0: rect(im,fx-7,fy-7,fx+7,fy+7,CORAL,1)
        pu=purity(t); text(x0+8,y0+h-20,'Purity %d%% (est.)'%round(pu),12,CORAL if pu<95 else TEAL,True)
    else: text(x0+w/2,y0+h/2,'standby',12,(100,115,112),False,'c')
def panel(im,t):
    x0,y0,w,h=930,108,320,160
    rect(im,x0,y0,x0+w,y0+h,(10,18,18)); rect(im,x0,y0,x0+w,y0+h,(80,100,98),2)
    L=[];T0=TEAL
    if PH['observe'][0]<=t<PH['pre'][0]:
        text(x0+10,y0+8,'PLAN',11,GREY,True)
        if t>=5.5:
            for i,s in enumerate(['1  GRID-4  (~4 mm)','2  HEX-2   (~2.2 mm)','3  SCREEN-1 (~1.2 mm)','4  CATCH PAN']): text(x0+14,y0+34+i*26,s,15,WHITE,True)
        else: text(x0+14,y0+60,'measuring sizes...',15,GREY)
    elif PH['pre'][0]<=t<PH['pre'][1]:
        text(x0+10,y0+8,'PREFLIGHT (digital twin)',11,GREY,True)
        for i,s in enumerate(['Sieves exist and are free','Coarse to fine order','Rack slots available','Water above reserve']):
            ok=t>=PH['pre'][0]+.35+i*.45; text(x0+14,y0+34+i*24,('[x] ' if ok else '[ ] ')+s,14,TEAL if ok else GREY,ok)
        if t>=PH['pre'][0]+2.2: text(x0+w-14,y0+h-30,'GO',24,TEAL,True,'r')
    elif PH['stack'][0]<=t<PH['sample'][1]:
        n=sum(1 for q in STACK if t>=ev[q][0]['r']); text(x0+10,y0+8,'STACK',11,GREY,True)
        text(x0+14,y0+50,'Trays placed %d / 4'%n,20,WHITE,True)
        if t>=PH['sample'][0]: text(x0+14,y0+90,'Sample added to top sieve',14,TEAL,True)
    elif PH['ag1'][0]<=t<PH['ag1'][1] or PH['ag2'][0]<=t<PH['ag2'][1]:
        c=1 if t<PH['ag2'][0] else 2; text(x0+10,y0+8,'AGITATE',11,GREY,True); text(x0+14,y0+50,'Cycle %d'%c,24,WHITE,True); text(x0+14,y0+96,'Water rinse + shake',14,GREY)
    elif PH['v1'][0]<=t<PH['collect'][0]:
        v=2 if t>=PH['ag2'][0] else 1; pu=purity(PH['v%d'%v][0]+2.0) if False else (80 if v==1 else 96)
        lab=any(a-.3<=t<=b for _,a,b in holds)
        text(x0+10,y0+8,'VERIFY (GRID-4 layer)',11,GREY,True); text(x0+14,y0+44,'Purity %d%%'%pu,28,CORAL if pu<95 else TEAL,True); text(x0+14,y0+92,'Target 95%',14,GREY)
        if lab: text(x0+14,y0+120,('Below target: agitate again' if pu<95 else 'PASS: collect layers'),15,CORAL if pu<95 else TEAL,True)
    elif PH['collect'][0]<=t<PH['collect'][1]:
        k=min(4,1+sum(1 for n in gone if t>=gone[n])); text(x0+10,y0+8,'COLLECT',11,GREY,True); text(x0+14,y0+50,'Layer %d / 4'%k,24,WHITE,True); text(x0+14,y0+96,'Pour into collection box',14,GREY)
    else: return
def hud(im,t):
    rect(im,0,0,W,70,(14,24,23)); text(40,20,'SO-101 sieving demo',22,WHITE,True); text(W-40,26,'ANIMATED SIMULATION  |  illustrative values',13,CORAL,True,'r')
    a=active(t); x=40
    for i,s in enumerate(STEPS):
        w=len(s)*9+22; on=i==a
        rect(im,x,76,x+w,76+22,TEAL if on else (40,56,56)); text(x+w/2,76+11,s,11,(20,32,31) if on else GREY,True,'c'); x+=w+6
    if PH['observe'][0]<=t: feed(im,t); panel(im,t)
    cap=''
    if PH['stack'][0]<=t<PH['stack'][1]:
        for n in STACK:
            if ev[n][0]['g']-1.9<=t<ev[n][0]['r']+.3: cap='Arm fetches %s from shelf %s and places it on the rack'%(n,TR[n][1]);break
    elif PH['collect'][0]<=t<PH['collect'][1]: cap='Arm pours each layer into its own collection box'
    elif any(a2-.3<=t<=b for _,a2,b in holds): cap='Arm lifts the top tray under the camera'
    if cap: text(W/2,BENCH+54,cap,17,WHITE,True,'c')
def finish(im,t):
    if t<2.5:
        ov=im.copy(); rect(ov,0,0,W,H,(14,24,23),-1); a=.85*(1-cl((t-1.8)/.7)); blend(im,ov,a)
        al=1-cl((t-1.8)/.7)
        if al>0:
            c=lambda v:tuple(int(BG[i]+(v[i]-BG[i])*al) for i in range(3))
            text(W/2,290,'Camera-guided sieving with SO-101',40,c(WHITE),True,'c'); text(W/2,350,'Animated demo built around the 2x shelf STL',20,c(TEAL),False,'c')
    if t>=PH['outro'][0]:
        al=cl((t-PH['outro'][0])/.6); ov=im.copy(); rect(ov,0,0,W,H,(14,24,23),-1); blend(im,ov,.9*al)
        c=lambda v:tuple(int(BG[i]+(v[i]-BG[i])*al) for i in range(3))
        text(W/2,250,'Bags in, barcodes out',54,c(WHITE),True,'c')
        for i,s in enumerate(['Camera sizes the sample and plans the sieve stack','Arm builds the stack from two shelves','Shake, re-image and repeat until purity target','Each layer poured into its own box']): text(W/2,330+i*36,s,22,c(TEAL if i==3 else (200,205,200)),False,'c')
        text(W/2,H-60,'ANIMATED SIMULATION, NOT REAL FOOTAGE. Purity values are illustrative.',16,c(CORAL),True,'c')
def frame(t):
    im=render(t); hud(im,t); finish(im,t)
    pil=Image.fromarray(im); dr=ImageDraw.Draw(pil)
    for x,y,s,sz,col,b,anc in tx:
        f=font(sz,b); w=dr.textlength(s,font=f); xx=x-(w/2 if anc=='c' else w if anc=='r' else 0)
        yy=y-(sz/2 if anc=='c' else 0) if anc=='c' else y
        dr.text((xx,yy),s,font=f,fill=tuple(int(v) for v in col))
    return np.array(pil)
if __name__=='__main__':
    print('total',TOTAL,{k:[round(x,1) for x in v] for k,v in PH.items()},flush=True)
    if sys.argv[1]=='test':
        for t in map(float,sys.argv[2:]): Image.fromarray(frame(t)).save('f_%05.1f.png'%t)
    else:
        n=int(TOTAL*FPS)
        p=subprocess.Popen(['ffmpeg','-y','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24','-s','%dx%d'%(W,H),'-r',str(FPS),'-i','-','-c:v','libx264','-pix_fmt','yuv420p','-crf','20','-preset','fast','sieving_demo.mp4'],stdin=subprocess.PIPE)
        for i in range(n):
            p.stdin.write(frame(i/FPS).tobytes())
            if i%100==0: print(i,n,flush=True)
        p.stdin.close(); p.wait(); print('done')
