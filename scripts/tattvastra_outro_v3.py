#!/usr/bin/env python3
"""Render locally: /opt/homebrew/bin/python3.10 scripts/tattvastra_outro_v3.py"""
from pathlib import Path
import math
import subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'apps/dashboard/public'
OUT = ROOT / 'output/tattvastra_outro_v3.mp4'
W, H, FPS, DURATION = 1920, 1080, 60, 6.2
SUBTITLE = 'JOCKY-based cross-platform forensic scripting language'
FONT = '/System/Library/Fonts/Supplemental/Arial.ttf'

def ease(x):
    x = max(0., min(1., x))
    return x*x*(3-2*x)

def ramp(t, a, b):
    return ease((t-a)/(b-a))

def text(s, size, tracking=0):
    font = ImageFont.truetype(FONT, size)
    widths = [font.getlength(c) for c in s]
    im = Image.new('RGBA', (math.ceil(sum(widths)+tracking*(len(s)-1))+8, size*2))
    d = ImageDraw.Draw(im)
    x = 4
    for c, width in zip(s, widths):
        d.text((x, 0), c, font=font, fill=(215,233,246,255))
        x += width+tracking
    return im.crop(im.getbbox())

def place(frame, asset, center, opacity=1.):
    if opacity <= 0: return
    asset = asset.copy()
    if opacity < 1: asset.putalpha(asset.getchannel('A').point(lambda v: round(v*opacity)))
    frame.alpha_composite(asset, (round(center[0]-asset.width/2), round(center[1]-asset.height/2)))

def fit(path, width=None, height=None):
    im = Image.open(path).convert('RGBA')
    im = im.crop(im.getbbox())
    factor = width/im.width if width else height/im.height
    return im.resize((round(im.width*factor),round(im.height*factor)), Image.Resampling.LANCZOS)

def sweep_reveal(asset, progress, edge_first=False):
    """Soft left-to-right materialization; original RGB and silhouette stay intact."""
    width, height = asset.size
    xx = np.arange(width, dtype=np.float32)[None, :]
    front = -90 + (width+180)*progress
    body = np.clip((front-xx)/70+.5, 0, 1)
    body = body*body*(3-2*body)
    mask = Image.fromarray(np.repeat((body*255).astype('uint8'),height,axis=0))
    original_alpha = asset.getchannel('A')
    resolved = asset.copy()
    resolved.putalpha(ImageChops.multiply(original_alpha,mask))
    if edge_first:
        ahead = np.exp(-((xx-front-10)/22)**2)
        band = Image.fromarray(np.repeat((ahead*110).astype('uint8'),height,axis=0))
        edges = ImageChops.lighter(original_alpha.filter(ImageFilter.FIND_EDGES),
                                   asset.convert('L').filter(ImageFilter.FIND_EDGES))
        highlight = Image.new('RGBA',asset.size,(183,213,234,0))
        highlight.putalpha(ImageChops.multiply(ImageChops.multiply(edges,original_alpha),band))
        resolved = Image.alpha_composite(resolved,highlight)
    return resolved

logo = fit(ASSETS/'tattvastra-mark.png', height=470)
wordmark = fit(ASSETS/'tattvastra-wordmark.png', width=1080)
team = text('TEAM ASHTOJ', 25, 7)
motto = text('One Language. Every Endpoint. No Noise.', 21)
subtitle = text(SUBTITLE, 29)
y, x = np.mgrid[:H,:W].astype(np.float32)
radial = np.exp(-(((x-960)/690)**2+((y-440)/500)**2)*1.6)
bg = np.zeros((H,W,3),dtype=np.uint8)
for c, (base, gain) in enumerate(((5,8),(8,18),(13,29))):
    bg[:,:,c] = base+gain*radial
background = Image.fromarray(bg).convert('RGBA')
paths = [ [(100,300),(360,300),(460,400),(680,400)],
          [(1820,300),(1560,300),(1460,400),(1240,400)],
          [(170,730),(430,730),(520,640),(710,640)],
          [(1750,730),(1490,730),(1400,640),(1210,640)],
          [(520,120),(520,220),(680,380)],
          [(1400,120),(1400,220),(1240,380)] ]
rng = np.random.default_rng(26)
particles = rng.uniform([130,150],[1790,940],(14,2))
# Deterministic irregular network sculpture, with sparse nearest-neighbour edges.
anchors=rng.normal(size=(16,3))
anchors/=np.linalg.norm(anchors,axis=1)[:,None]
anchors*=rng.uniform(.8,1.1,(16,1))
edges=sorted({tuple(sorted((i,int(j)))) for i in range(16)
              for j in np.argsort(np.linalg.norm(anchors-anchors[i],axis=1))[1:4]})
# Padded glow retains all edges of the original transparent mark.
glow = Image.new('RGBA',(logo.width+80,logo.height+80))
glow.alpha_composite(logo,(40,40))
alpha = glow.getchannel('A').filter(ImageFilter.GaussianBlur(13))
glow = Image.new('RGBA',glow.size,(120,165,200,0)); glow.putalpha(alpha)
# Helpers, assets, palette and procedural environment reused from the intro.
OUT.parent.mkdir(exist_ok=True)
cmd = ['ffmpeg','-y','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24',
       '-s',f'{W}x{H}','-r',str(FPS),'-i','-','-an','-c:v','libx264',
       '-preset','fast','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(OUT)]
proc = subprocess.Popen(cmd,stdin=subprocess.PIPE)
black = Image.new('RGBA',(W,H),(0,0,0,255))
frames = round(FPS*DURATION)
try:
    for index in range(frames):
        t = index/FPS
        details = 1-ramp(t,4.95,5.2)
        lit=bg.copy()
        for channel,gain in enumerate((8,18,29)):
            lit[:,:,channel]=np.clip(bg[:,:,channel].astype(np.float32)+gain*radial*.03*math.sin(t*.8),0,255)
        frame = Image.blend(black,Image.fromarray(lit).convert('RGBA'),1-ramp(t,5.25,5.6))
        tech = Image.new('RGBA',(W,H)); d = ImageDraw.Draw(tech)
        push = 1+0.025*ramp(t,0,DURATION)
        def point(p, depth=1.):
            z=1+(push-1)*depth
            return (960+(p[0]-960)*z,540+(p[1]-540)*z)
        emergence=1.
        # Visible scientific data fabric: broad slow waves, fine perspective mesh.
        def surface(u,v):
            lateral=38*math.sin(t*.30)
            spread=.28+.80*v
            height=(36+32*v)*math.sin(u/340-t*.72+v*3.2)
            height+=24*math.cos(u/570+t*.48-v*4.1)
            px,py=point((960+(u+lateral)*spread,605+480*v**1.55+height),.5)
            return (px,605+(py-605)*(1-ramp(t,5.45,5.8)))
        fabric=Image.new('RGBA',(W,H)); fd=ImageDraw.Draw(fabric)
        for j,u in enumerate(range(-2300,2301,85)):
            fd.line([surface(u,v) for v in np.linspace(0,1.12,72)],
                   fill=(120,165,200,round(42*emergence)),width=1)
        for j,v in enumerate(np.linspace(0,1.12,28)):
            highlight=j%7==3
            fd.line([surface(u,v) for u in np.linspace(-2300,2300,150)],
                   fill=((183,213,234,round(76*emergence)) if highlight else
                         (120,165,200,round(49*emergence))),width=1)
        if t>5.1:
            remaining=1-ramp(t,5.1,5.8)
            envelope=np.clip((remaining-np.abs(np.arange(W)-960)/1100)/.18,0,1)
            mask=Image.fromarray(np.repeat((envelope[None,:]*255).astype('uint8'),H,axis=0))
            fabric.putalpha(ImageChops.multiply(fabric.getchannel('A'),mask))
        tech=Image.alpha_composite(tech,fabric); d=ImageDraw.Draw(tech)
        # Sequential endpoint activity on the same parametric surface.
        for k,u in enumerate([-1250,1100,-650,700]):
            px,py=surface(u,.44+k*.1)
            a=ramp(t,2.6+k*.16,2.85+k*.16)*(1-ramp(t,4.8+k*.035,4.98+k*.035))
            d.ellipse((px-2,py-2,px+2,py+2),fill=(183,213,234,round(150*a)))
        if 2.8<t<4.8:
            q=ramp(t,2.8,4.65)
            px,py=surface(-1250*(1-q),.5*(1-q))
            py=py*(1-q*q)+340*q*q
            a=ramp(t,2.8,3.0)*(1-ramp(t,4.65,4.8))
            d.ellipse((px-2,py-2,px+2,py+2),fill=(183,213,234,round(180*a)))
        # One broad S-shaped data trajectory, with a continuously travelling packet.
        def trajectory(q):
            bend=ramp(t,2.4,3.6)*(1-ramp(t,3.7,4.8))
            px=-130+2180*q
            py=735+180*math.sin(2*math.pi*q+.3)+38*math.sin(t*.38+q*3)
            py-=125*bend*math.exp(-((q-.5)/.21)**2)
            return point((px,py),.85)
        drawn=1.
        retract=.5*ramp(t,5.38,5.58)
        curve=[trajectory(q) for q in np.linspace(retract,1-retract,230)]
        d.line(curve,fill=(120,165,200,round(88*(1-ramp(t,5.25,5.4)))),width=1)
        packet=(t*.125+.04)%1
        if packet<drawn and t<5.02:
            for q in np.linspace(max(0,packet-.025),packet,14):
                px,py=trajectory(q)
                strength=(q-max(0,packet-.025))/.025
                d.ellipse((px-1,py-1,px+1,py+1),fill=(183,213,234,round(150*strength*(1-ramp(t,4.9,5.02)))))
        # Slowly rotating polyhedral form resolves into curved inbound signals.
        angle=t*.19
        rotation=np.array([[math.cos(angle),0,math.sin(angle)],
                           [0,1,0],[-math.sin(angle),0,math.cos(angle)]])
        rotated=anchors@rotation.T
        tilt=.22+.10*math.sin(t*.3)
        projected=[]
        converge=.18*ramp(t,4.95,5.3)
        for k,(ax,ay,az) in enumerate(rotated):
            vy=ay*math.cos(tilt)-az*math.sin(tilt)
            depth=1/(1+az*.17)
            px=960+ax*365*depth; py=390+vy*245*depth
            px=px*(1-converge)+960*converge+45*math.sin(math.pi*converge)*math.sin(k)
            py=py*(1-converge)+510*converge-65*math.sin(math.pi*converge)
            projected.append((px,py))
        edge_alpha=round(45*emergence*(1-ramp(t,4.95,5.17)))
        for i,j in edges:
            d.line([projected[i],projected[j]],fill=(120,165,200,edge_alpha),width=1)
        node_alpha=round(65*(1-ramp(t,5.1,5.35)))
        for px,py in projected:
            d.ellipse((px-1.5,py-1.5,px+1.5,py+1.5),fill=(183,213,234,node_alpha))
        for k,path in enumerate(paths):
            pts = [point(p) for p in path]
            activation = .18+.82*ramp(t,k*.055,.55+k*.055)
            path_alpha = activation*(1-ramp(t,5.05,5.3))
            # Retract the path from its outer endpoint toward its destination.
            retract=ramp(t,5.0+k*.015,5.3)
            lengths=[math.dist(a,b) for a,b in zip(pts,pts[1:])]
            cut=retract*sum(lengths); tail=[]
            for j,(a,b,length) in enumerate(zip(pts,pts[1:],lengths)):
                if cut<=length:
                    q=cut/length
                    tail=[(a[0]+q*(b[0]-a[0]),a[1]+q*(b[1]-a[1]))]+pts[j+1:]; break
                cut-=length
            if len(tail)>1: d.line(tail,fill=(78,127,160,round(35*path_alpha)),width=1)
            px,py=pts[0]
            node_alpha = activation*(1-ramp(t,4.8+k*.025,4.96+k*.025))
            d.ellipse((px-3,py-3,px+3,py+3),fill=(120,165,200,round(115*node_alpha*(.86+.14*math.sin(t*1.3+k)))))
            # Two slow, non-looping convergence passes; no packet reset flashes.
            for start,end in [(k*.05,1.2+k*.05),(2.6+k*.09,4.4+k*.025)]:
                progress=ramp(t,start,end)
                packet_alpha=path_alpha*ramp(t,start,start+.15)*(1-ramp(t,end-.2,end))
                distance=progress*sum(math.dist(a,b) for a,b in zip(pts,pts[1:]))
                for a,b in zip(pts,pts[1:]):
                    length=math.dist(a,b)
                    if distance<=length:
                        q=distance/length; px=a[0]+q*(b[0]-a[0]); py=a[1]+q*(b[1]-a[1]); break
                    distance-=length
                d.ellipse((px-1,py-1,px+1,py+1),fill=(183,213,234,round(110*packet_alpha)))
        for k,(px,py) in enumerate(particles):
            px,py=point((px,py),1.)
            py+=7*math.sin(t*.25+k)
            d.ellipse((px,py,px+1.5,py+1.5),fill=(120,165,200,round(35*details)))
        if 4.1<t<4.8:
            q=ramp(t,4.1,4.8); radius=90+330*q
            d.ellipse((960-radius,340-radius*.6,960+radius,340+radius*.6),
                      outline=(120,165,200,round(42*math.sin(math.pi*q)*(1-q))),width=1)
        frame=Image.alpha_composite(frame,tech)
        reveal=ramp(t,.1,1.2)
        linger=1-ramp(t,5.65,5.88)
        scale=.975+.025*reveal
        mark=logo.resize((round(logo.width*scale),round(logo.height*scale)),Image.Resampling.LANCZOS)
        mark=sweep_reveal(mark,ramp(t,.05,1.2),edge_first=True)
        contraction=1-.24*ramp(t,5.55,5.9)
        tight_glow=glow.resize((round(glow.width*contraction),round(glow.height*contraction)),Image.Resampling.LANCZOS)
        place(frame,tight_glow,(960,340),reveal*(1-ramp(t,5.55,5.9))*(.13+.02*math.sin(t*1.5)))
        if 4.1<t<4.8:
            phase=ramp(t,4.1,4.8)
            yy=np.arange(mark.height)[:,None]
            band=np.exp(-((yy-phase*mark.height)/36)**2)
            strength=math.sin(math.pi*phase)*48
            mask=Image.fromarray(np.repeat((band*strength).astype('uint8'),mark.width,axis=1))
            mask=ImageChops.multiply(mask,mark.getchannel('A'))
            light=Image.new('RGBA',mark.size,(232,242,248,0)); light.putalpha(mask)
            mark=Image.alpha_composite(mark,light)
        place(frame,mark,(960,340),reveal*linger)
        # Brief illuminated silhouette contracts horizontally to one quiet trace.
        if 5.65<t<6.15:
            edge=logo.getchannel('A').filter(ImageFilter.FIND_EDGES)
            outline=Image.new('RGBA',logo.size,(183,213,234,0)); outline.putalpha(edge)
            collapse=ramp(t,5.88,6.04)
            outline=outline.resize((max(1,round(logo.width*(1-collapse))),
                                    max(1,round(logo.height*(1-collapse)))),Image.Resampling.LANCZOS)
            place(frame,outline,(960,340),.48*ramp(t,5.65,5.86)*(1-ramp(t,6.03,6.15)))
        if 5.98<t<6.15:
            dot=Image.new('RGBA',(7,7)); dd=ImageDraw.Draw(dot)
            a=ramp(t,5.98,6.04)*(1-ramp(t,6.04,6.15))
            dd.ellipse((2,2,4,4),fill=(120,165,200,round(95*a)))
            place(frame,dot,(960,340))
        hero=ramp(t,1.2,2.05)
        place(frame,sweep_reveal(wordmark,hero),(960,650+6*(1-hero)),ramp(t,1.2,1.5)*(1-ramp(t,5.58,5.86)))
        sub=ramp(t,1.65,2.6)
        place(frame,subtitle,(960,748+7*(1-sub)),sub*(1-ramp(t,5.38,5.58)))
        secondary=ramp(t,2.6,3.2)*(1-ramp(t,5.22,5.42))
        line=Image.new('RGBA',(W,H)); ld=ImageDraw.Draw(line)
        half=155*ramp(t,2.6,3.3)
        ld.line((960-half,806,960+half,806),fill=(120,165,200,round(120*secondary)),width=1)
        frame=Image.alpha_composite(frame,line)
        place(frame,team,(960,856+6*(1-ramp(t,2.8,3.45))),ramp(t,2.8,3.45)*(1-ramp(t,5.22,5.42)))
        place(frame,motto,(960,904),.65*ramp(t,3.2,3.85)*(1-ramp(t,5.18,5.38)))
        proc.stdin.write(frame.convert('RGB').tobytes())
        if index%120==0: print(f'Rendered {index}/{frames}',flush=True)
finally:
    proc.stdin.close()
if proc.wait(): raise RuntimeError('FFmpeg failed')
print(OUT)
