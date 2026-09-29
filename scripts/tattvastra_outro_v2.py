#!/usr/bin/env python3
"""Render locally: /opt/homebrew/bin/python3.10 scripts/tattvastra_outro_v2.py"""
from pathlib import Path
import math
import subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'apps/dashboard/public'
OUT = ROOT / 'output/tattvastra_outro_v2.mp4'
W, H, FPS, DURATION = 1920, 1080, 60, 6.5
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
        details = 1-ramp(t,4.7,5.05)
        lit=bg.copy()
        for channel,gain in enumerate((8,18,29)):
            lit[:,:,channel]=np.clip(bg[:,:,channel].astype(np.float32)+gain*radial*.03*math.sin(t*.8),0,255)
        frame = Image.blend(black,Image.fromarray(lit).convert('RGBA'),1-ramp(t,4.85,5.5))
        tech = Image.new('RGBA',(W,H)); d = ImageDraw.Draw(tech)
        push = 1+0.025*ramp(t,0,DURATION)
        def point(p, depth=1.):
            z=1+(push-1)*depth
            return (960+(p[0]-960)*z,540+(p[1]-540)*z)
        grid_alpha = round(18*details)
        # Curved perspective data surface: tiny travelling deformations at depth.
        def surface(u,v):
            spread=.20+.80*v
            return point((960+u*spread, 690+390*v*v+
                          (5+11*v)*math.sin(u/270+t*.24+v*3)),.45)
        for u in range(-1600,1601,160):
            d.line([surface(u,v) for v in np.linspace(0,1,40)],fill=(53,91,122,grid_alpha),width=1)
        for v in np.linspace(.08,1,11):
            d.line([surface(u,v) for u in np.linspace(-1700,1700,90)],fill=(53,91,122,grid_alpha),width=1)
        # Partial, gently tracing elliptical paths, never complete spinning rings.
        for k,(rx,ry,start) in enumerate([(740,305,2.8),(850,380,5.65),(640,450,.35)]):
            length=(.28+.37*ramp(t,.3+k*.3,4.5+k*.4))
            theta=start+t*(.013+.006*k)
            angles=np.linspace(theta,theta+length,85)
            arc=[point((960+rx*math.cos(a),500+ry*math.sin(a)),.65+k*.12) for a in angles]
            d.line(arc,fill=(120,165,200,round((14-k*2)*details)),width=1)
            a=theta+length*(.5+.35*math.sin(t*.23+k))
            px,py=point((960+rx*math.cos(a),500+ry*math.sin(a)),.65+k*.12)
            d.ellipse((px-1,py-1,px+1,py+1),fill=(183,213,234,round(22*details)))
        for k,path in enumerate(paths):
            pts = [point(p) for p in path]
            activation = .18+.82*ramp(t,k*.055,.55+k*.055)
            path_alpha = activation*(1-ramp(t,4.65,4.95))
            # Retract the path from its outer endpoint toward its destination.
            retract=ramp(t,4.4+k*.025,4.9)
            lengths=[math.dist(a,b) for a,b in zip(pts,pts[1:])]
            cut=retract*sum(lengths); tail=[]
            for j,(a,b,length) in enumerate(zip(pts,pts[1:],lengths)):
                if cut<=length:
                    q=cut/length
                    tail=[(a[0]+q*(b[0]-a[0]),a[1]+q*(b[1]-a[1]))]+pts[j+1:]; break
                cut-=length
            if len(tail)>1: d.line(tail,fill=(78,127,160,round(35*path_alpha)),width=1)
            px,py=pts[0]
            node_alpha = activation*(1-ramp(t,4.05+k*.035,4.35+k*.035))
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
        if 3.95<t<4.65:
            q=ramp(t,3.95,4.65); radius=90+330*q
            d.ellipse((960-radius,340-radius*.6,960+radius,340+radius*.6),
                      outline=(120,165,200,round(42*math.sin(math.pi*q)*(1-q))),width=1)
        frame=Image.alpha_composite(frame,tech)
        reveal=ramp(t,.1,1.2)
        linger=1-ramp(t,5.65,5.95)
        scale=.975+.025*reveal
        mark=logo.resize((round(logo.width*scale),round(logo.height*scale)),Image.Resampling.LANCZOS)
        mark=sweep_reveal(mark,ramp(t,.05,1.2),edge_first=True)
        contraction=1-.24*ramp(t,5.5,5.95)
        tight_glow=glow.resize((round(glow.width*contraction),round(glow.height*contraction)),Image.Resampling.LANCZOS)
        place(frame,tight_glow,(960,340),reveal*(1-ramp(t,5.5,5.95))*(.13+.02*math.sin(t*1.5)))
        if 3.85<t<4.55:
            phase=ramp(t,3.85,4.55)
            yy=np.arange(mark.height)[:,None]
            band=np.exp(-((yy-phase*mark.height)/36)**2)
            strength=math.sin(math.pi*phase)*48
            mask=Image.fromarray(np.repeat((band*strength).astype('uint8'),mark.width,axis=1))
            mask=ImageChops.multiply(mask,mark.getchannel('A'))
            light=Image.new('RGBA',mark.size,(232,242,248,0)); light.putalpha(mask)
            mark=Image.alpha_composite(mark,light)
        place(frame,mark,(960,340),reveal*linger)
        # Brief illuminated silhouette contracts horizontally to one quiet trace.
        if 5.65<t<6.38:
            edge=logo.getchannel('A').filter(ImageFilter.FIND_EDGES)
            outline=Image.new('RGBA',logo.size,(183,213,234,0)); outline.putalpha(edge)
            collapse=ramp(t,5.98,6.22)
            outline=outline.resize((max(1,round(logo.width*(1-collapse))),
                                    max(1,round(logo.height*(1-.9*collapse)))),Image.Resampling.LANCZOS)
            place(frame,outline,(960,340),.48*ramp(t,5.65,5.92)*(1-ramp(t,6.18,6.38)))
        hero=ramp(t,1.2,2.05)
        place(frame,sweep_reveal(wordmark,hero),(960,650+6*(1-hero)),ramp(t,1.2,1.5)*(1-ramp(t,5.5,5.85)))
        sub=ramp(t,1.65,2.6)
        place(frame,subtitle,(960,748+7*(1-sub)),sub*(1-ramp(t,5.05,5.4)))
        secondary=ramp(t,2.6,3.2)*(1-ramp(t,4.9,5.2))
        line=Image.new('RGBA',(W,H)); ld=ImageDraw.Draw(line)
        half=155*ramp(t,2.6,3.3)
        ld.line((960-half,806,960+half,806),fill=(120,165,200,round(120*secondary)),width=1)
        frame=Image.alpha_composite(frame,line)
        place(frame,team,(960,856+6*(1-ramp(t,2.8,3.45))),ramp(t,2.8,3.45)*(1-ramp(t,4.9,5.2)))
        place(frame,motto,(960,904),.65*ramp(t,3.2,3.85)*(1-ramp(t,4.85,5.15)))
        proc.stdin.write(frame.convert('RGB').tobytes())
        if index%120==0: print(f'Rendered {index}/{frames}',flush=True)
finally:
    proc.stdin.close()
if proc.wait(): raise RuntimeError('FFmpeg failed')
print(OUT)
