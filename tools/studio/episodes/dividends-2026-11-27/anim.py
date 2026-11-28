import sys,math,subprocess
sys.path.insert(0,'/tmp/claude-0')
from boardfx import *
from PIL import Image,ImageDraw,ImageFont
D='/root/majlis_local/src/dv/'
rows=[475,615,755,895];right=682;fs=44;ns=48
plate=Image.open(D+'plate_raw.png').convert('RGB')
plate=write(plate,rows,right,fs,ns)
plate.save(D+'plate_text.png')
# left end of each row text (plate coords)
d=ImageDraw.Draw(plate);f=ImageFont.truetype(F,fs)
lefts=[]
for t in items:
    bb=d.textbbox((0,0),t,font=f,direction='rtl');w=bb[2]-bb[0]
    lefts.append(right-2*ns*0.75-ns*0.4-w)
S=1.1012;OX=-53.9;OY=-200
def state(k):
    L=plate.convert('RGBA');H=Image.new('RGBA',L.size,(0,0,0,0));dh=ImageDraw.Draw(H)
    for i in range(k):
        y=rows[i];dh.rounded_rectangle((lefts[i]-22,y-42,right+12,y+42),radius=20,fill=(255,200,0,150) if i==k-1 else (255,200,0,70))
    L=Image.alpha_composite(L,H)
    # redraw text on top of the band so it stays crisp
    L=write(L.convert('RGB'),rows,right,fs,ns)
    b=L.resize((round(752*S),round(1344*S)),Image.LANCZOS)
    fr=Image.new('RGB',(720,1280));fr.paste(b,(round(OX),round(OY)));return fr
states=[state(k) for k in range(5)]
hand=Image.open(D+'hand.png').convert('RGBA')
HS=0.46*S;hand=hand.resize((round(1024*HS),round(1024*HS)),Image.LANCZOS)
tipx,tipy=1003*HS,96*HS
targets=[((lefts[i]-14)*S+OX,(rows[i]+4)*S+OY) for i in range(4)]
delay=0.15;cues=[0.0,5.812,11.42,20.495];cues=[c+delay for c in cues]
dur=float(sys.argv[1]);fps=30
def ease(u): return 0.5-0.5*math.cos(math.pi*max(0,min(1,u)))
def pos(t):
    x,y=targets[0]
    for i in range(1,4):
        st=cues[i]-0.5; u=ease((t-st)/1.0)
        if u>0:
            x=targets[i-1][0]+(targets[i][0]-targets[i-1][0])*u
            y=targets[i-1][1]+(targets[i][1]-targets[i-1][1])*u
    return x,y+2.0*math.sin(2*math.pi*0.4*t)
p=subprocess.Popen(f"ffmpeg -loglevel error -y -f rawvideo -pix_fmt rgb24 -s 720x1280 -r {fps} -i - -c:v libx264 -crf 16 -pix_fmt yuv420p {D}point.mp4",shell=True,stdin=subprocess.PIPE)
for n in range(int(dur*fps)):
    t=n/fps;k=sum(1 for c in cues if t>=c);fr=states[k].copy();x,y=pos(t)
    fr.paste(hand,(round(x-tipx),round(y-tipy)),hand)
    p.stdin.write(fr.tobytes())
p.stdin.close();p.wait();print('ok',targets)
