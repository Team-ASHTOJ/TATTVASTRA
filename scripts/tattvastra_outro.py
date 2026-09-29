#!/usr/bin/env python3
"""Render locally: /opt/homebrew/bin/python3.10 scripts/tattvastra_outro.py"""
from pathlib import Path
import math
import subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'apps/dashboard/public'
OUT = ROOT / 'output/tattvastra_outro.mp4'
W, H, FPS, DURATION = 1920, 1080, 60, 5.6
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
        details = 1-ramp(t,4.65,5.15)
        frame = Image.blend(black,background,1-ramp(t,4.6,5.4))
        tech = Image.new('RGBA',(W,H)); d = ImageDraw.Draw(tech)
        push = 1+.012*ramp(t,0,5.6)
        def point(p): return (960+(p[0]-960)*push,540+(p[1]-540)*push)
        grid_alpha = round(13*details)
        for gx in range(-600,2600,160):
            d.line([point((960+(gx-960)*.22,580)),point((gx,1080))],fill=(53,91,122,grid_alpha))
        for gy in [603,639,687,753,840,956,1070]:
            d.line([point((0,gy)),point((W,gy))],fill=(53,91,122,grid_alpha))
        for k,path in enumerate(paths):
            pts = [point(p) for p in path]
            activation = ramp(t,k*.055,.55+k*.055)
            path_alpha = activation*(1-ramp(t,4.45,4.95))
            d.line(pts,fill=(78,127,160,round(35*path_alpha)),width=1)
            px,py=pts[0]
            node_alpha = activation*(1-ramp(t,4.2+k*.035,4.6+k*.035))
            d.ellipse((px-3,py-3,px+3,py+3),fill=(120,165,200,round(140*node_alpha)))
            # Two slow, non-looping convergence passes; no packet reset flashes.
            for start,end in [(k*.05,1.2+k*.05),(2.6+k*.09,4.05+k*.035)]:
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
            py+=7*math.sin(t*.25+k)
            d.ellipse((px,py,px+1.5,py+1.5),fill=(120,165,200,round(35*details)))
        frame=Image.alpha_composite(frame,tech)
        reveal=ramp(t,.1,1.2)
        linger=1-ramp(t,4.85,5.55)
        scale=.96+.04*reveal
        mark=logo.resize((round(logo.width*scale),round(logo.height*scale)),Image.Resampling.LANCZOS)
        place(frame,glow,(960,340),reveal*linger*(.13+.02*math.sin(t*1.5)))
        if 4.15<t<4.95:
            phase=ramp(t,4.15,4.95)
            yy=np.arange(mark.height)[:,None]
            band=np.exp(-((yy-phase*mark.height)/36)**2)
            strength=math.sin(math.pi*phase)*48
            mask=Image.fromarray(np.repeat((band*strength).astype('uint8'),mark.width,axis=1))
            mask=ImageChops.multiply(mask,mark.getchannel('A'))
            light=Image.new('RGBA',mark.size,(232,242,248,0)); light.putalpha(mask)
            mark=Image.alpha_composite(mark,light)
        place(frame,mark,(960,340),reveal*linger)
        hero=ramp(t,1.2,2.05)
        place(frame,wordmark,(960,650+10*(1-hero)),hero*linger)
        sub=ramp(t,1.65,2.6)
        place(frame,subtitle,(960,748+7*(1-sub)),sub*linger)
        secondary=ramp(t,2.6,3.2)*(1-ramp(t,4.5,5.1))
        line=Image.new('RGBA',(W,H)); ld=ImageDraw.Draw(line)
        half=155*ramp(t,2.6,3.3)
        ld.line((960-half,806,960+half,806),fill=(120,165,200,round(120*secondary)),width=1)
        frame=Image.alpha_composite(frame,line)
        place(frame,team,(960,856+6*(1-ramp(t,2.8,3.45))),ramp(t,2.8,3.45)*(1-ramp(t,4.5,5.1)))
        place(frame,motto,(960,904),.65*ramp(t,3.2,3.85)*(1-ramp(t,4.45,5.05)))
        proc.stdin.write(frame.convert('RGB').tobytes())
        if index%120==0: print(f'Rendered {index}/{frames}',flush=True)
finally:
    proc.stdin.close()
if proc.wait(): raise RuntimeError('FFmpeg failed')
print(OUT)
