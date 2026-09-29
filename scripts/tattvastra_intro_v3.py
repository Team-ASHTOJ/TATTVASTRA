#!/usr/bin/env python3
"""Render locally: /opt/homebrew/bin/python3.10 scripts/tattvastra_intro_v3.py"""
from pathlib import Path
import math
import subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'apps/dashboard/public'
OUT = ROOT / 'output/tattvastra_intro_v3.mp4'
W, H, FPS, DURATION = 1920, 1080, 60, 8.5
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
team, presents = text('TEAM ASHTOJ', 36, 10), text('PRESENTS', 19, 7)
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
event_particles = rng.uniform([0, 300, 0], [2*math.pi, 690, .24], (30,3))
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
OUT.parent.mkdir(exist_ok=True)
cmd = ['ffmpeg','-y','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24',
       '-s',f'{W}x{H}','-r',str(FPS),'-i','-','-an','-c:v','libx264',
       '-preset','fast','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(OUT)]
proc = subprocess.Popen(cmd,stdin=subprocess.PIPE)
try:
    for index in range(round(FPS*DURATION)):
        t = index/FPS
        # Breathe only the radial lighting, leaving the palette and black floor intact.
        breathing = 1+.035*math.sin(t*.8)
        lit = bg.copy()
        for channel, gain in enumerate((8,18,29)):
            lit[:,:,channel] = np.clip(bg[:,:,channel].astype(np.float32)+gain*radial*(breathing-1),0,255)
        frame = Image.fromarray(lit).convert('RGBA')
        tech = Image.new('RGBA',(W,H)); d = ImageDraw.Draw(tech)
        push = 1+0.025*ramp(t,0,DURATION)
        def point(p, depth=1.):
            z=1+(push-1)*depth
            return (960+(p[0]-960)*z,540+(p[1]-540)*z)
        emergence=.22+.78*ramp(t,0,1.1)
        # Visible scientific data fabric: broad slow waves, fine perspective mesh.
        def surface(u,v):
            lateral=38*math.sin(t*.30)
            spread=.28+.80*v
            height=(36+32*v)*math.sin(u/340-t*.72+v*3.2)
            height+=24*math.cos(u/570+t*.48-v*4.1)
            return point((960+(u+lateral)*spread,605+480*v**1.55+height),.5)
        for j,u in enumerate(range(-2300,2301,85)):
            d.line([surface(u,v) for v in np.linspace(0,1.12,72)],
                   fill=(120,165,200,round(42*emergence)),width=1)
        for j,v in enumerate(np.linspace(0,1.12,28)):
            highlight=j%7==3
            d.line([surface(u,v) for u in np.linspace(-2300,2300,150)],
                   fill=((183,213,234,round(76*emergence)) if highlight else
                         (120,165,200,round(49*emergence))),width=1)
        # One broad S-shaped data trajectory, with a continuously travelling packet.
        def trajectory(q):
            bend=ramp(t,2.4,3.6)*(1-ramp(t,3.7,4.8))
            px=-130+2180*q
            py=735+180*math.sin(2*math.pi*q+.3)+38*math.sin(t*.38+q*3)
            py-=125*bend*math.exp(-((q-.5)/.21)**2)
            return point((px,py),.85)
        drawn=.08+.92*ramp(t,0,2.6)
        curve=[trajectory(q) for q in np.linspace(0,drawn,230)]
        d.line(curve,fill=(120,165,200,round(88*emergence)),width=1)
        packet=(t*.125+.04)%1
        if packet<drawn:
            for q in np.linspace(max(0,packet-.025),packet,14):
                px,py=trajectory(q)
                strength=(q-max(0,packet-.025))/.025
                d.ellipse((px-1,py-1,px+1,py+1),fill=(183,213,234,round(150*strength)))
        # Slowly rotating polyhedral form resolves into curved inbound signals.
        angle=t*.19
        rotation=np.array([[math.cos(angle),0,math.sin(angle)],
                           [0,1,0],[-math.sin(angle),0,math.cos(angle)]])
        rotated=anchors@rotation.T
        tilt=.22+.10*math.sin(t*.3)
        projected=[]
        converge=ramp(t,2.55,3.8)
        for k,(ax,ay,az) in enumerate(rotated):
            vy=ay*math.cos(tilt)-az*math.sin(tilt)
            depth=1/(1+az*.17)
            px=960+ax*365*depth; py=485+vy*245*depth
            px=px*(1-converge)+960*converge+45*math.sin(math.pi*converge)*math.sin(k)
            py=py*(1-converge)+510*converge-65*math.sin(math.pi*converge)
            projected.append((px,py))
        edge_alpha=round(45*emergence*(1-ramp(t,2.45,3.15)))
        for i,j in edges:
            d.line([projected[i],projected[j]],fill=(120,165,200,edge_alpha),width=1)
        node_alpha=round((65+45*ramp(t,2.4,3.0))*emergence*(1-ramp(t,3.5,3.9)))
        for px,py in projected:
            d.ellipse((px-1.5,py-1.5,px+1.5,py+1.5),fill=(183,213,234,node_alpha))
        for k,path in enumerate(paths):
            pts = [point(p) for p in path]
            opacity = ramp(t,0.15+k*.11,.8+k*.11)
            d.line(pts,fill=(78,127,160,round(35*opacity)),width=1)
            px,py = pts[0]
            d.ellipse((px-3,py-3,px+3,py+3),fill=(120,165,200,round(110*opacity*(.85+.15*math.sin(t*1.2+k)))))
            # A single quiet packet travels toward the logo on each path.
            progress = ramp(t,2.15+k*.035,3.75) if t<4 else .6+.22*math.sin(t*.17+k)
            if 2.15<t<3.9:
                pts += [point((900 if k%2==0 else 1020,510))]
            lengths = [math.dist(a,b) for a,b in zip(pts,pts[1:])]
            distance = progress*sum(lengths)
            for a,b,length in zip(pts,pts[1:],lengths):
                if distance <= length:
                    q=distance/length; px=a[0]+q*(b[0]-a[0]); py=a[1]+q*(b[1]-a[1]); break
                distance-=length
            d.ellipse((px-1,py-1,px+1,py+1),fill=(183,213,234,round(110*opacity)))
        for k,(px,py) in enumerate(particles):
            px,py = point((px,py),1.0)
            py += 7*math.sin(t*.25+k)
            d.ellipse((px,py,px+1.5,py+1.5),fill=(120,165,200,35))
        # One restrained convergence event, confined to the logo reveal.
        for k,(angle,radius,delay) in enumerate(event_particles):
            q=ramp(t,2.25+delay,3.7+delay*.4)
            strength=ramp(t,2.25+delay,2.55+delay)*(1-ramp(t,3.45,3.85))
            r=radius*(1-.90*q)
            px=960+math.cos(angle)*r; py=510+math.sin(angle)*r*.57
            d.ellipse((px-1,py-1,px+1,py+1),fill=(183,213,234,round(80*strength)))
        # The presenter scan line contracts and travels toward the resolve point.
        line_in=ramp(t,1.05,1.5); inward=ramp(t,2.15,2.85)
        half=225*line_in*(1-inward)
        line_alpha=line_in*(1-ramp(t,2.65,2.9))
        line_y=529-19*inward
        d.line((960-half,line_y,960+half,line_y),fill=(183,213,234,round(115*line_alpha)),width=1)
        d.arc((690,300,1230,760),205,325,fill=(120,165,200,round(17*line_alpha)),width=1)
        if 3.68<t<4.35:
            pulse=ramp(t,3.68,4.35); radius=90+350*pulse
            d.ellipse((960-radius,510-radius*.58,960+radius,510+radius*.58),
                      outline=(120,165,200,round(45*math.sin(math.pi*pulse)*(1-pulse))),width=1)
        frame = Image.alpha_composite(frame,tech)
        title_alpha = ramp(t,1.1,1.55)*(1-ramp(t,2.2,2.65))
        place(frame,sweep_reveal(team,ramp(t,1.1,1.7)),(960,492+12*(1-ramp(t,1.1,1.65))),title_alpha)
        place(frame,presents,(960,558+8*(1-ramp(t,1.3,1.8))),title_alpha*ramp(t,1.3,1.7))
        reveal = ramp(t,2.65,3.8)
        cy = 510-115*ramp(t,3.8,4.7)
        scale = .975+.025*reveal
        mark = logo.resize((round(logo.width*scale),round(logo.height*scale)),Image.Resampling.LANCZOS)
        place(frame,glow,(960,cy),reveal*(.13+.025*math.sin(t*1.5)))
        mark = sweep_reveal(mark,ramp(t,2.6,3.8),edge_first=True)
        # Vertical light sweep is clipped to the asset's alpha, keeping it crisp.
        sweep = max(1-abs((t-3.3)/.55),0)+max(1-abs((t-6.95)/.65),0)
        if sweep:
            yy=np.arange(mark.height)[:,None]
            phase=(t-2.75)/1.1 if t<4 else (t-6.3)/1.3
            band=np.exp(-((yy-phase*mark.height)/36)**2)
            mask=Image.fromarray(np.repeat((band*48*sweep).astype('uint8'),mark.width,axis=1))
            mask=ImageChops.multiply(mask,mark.getchannel('A'))
            light=Image.new('RGBA',mark.size,(232,242,248,0)); light.putalpha(mask)
            mark=Image.alpha_composite(mark,light)
        place(frame,mark,(960,cy),reveal)
        hero=ramp(t,4.05,4.95)
        place(frame,sweep_reveal(wordmark,hero),(960,718+6*(1-hero)),ramp(t,4.05,4.35))
        place(frame,subtitle,(960,823+9*(1-ramp(t,4.65,5.45))),ramp(t,4.65,5.45))
        if t<1.1:
            frame=Image.blend(Image.new('RGBA',(W,H),(0,0,0,255)),frame,ramp(t,0,1.1))
        proc.stdin.write(frame.convert('RGB').tobytes())
        if index%120==0: print(f'Rendered {index}/{FPS*DURATION}',flush=True)
finally:
    proc.stdin.close()
if proc.wait(): raise RuntimeError('FFmpeg failed')
print(OUT)
