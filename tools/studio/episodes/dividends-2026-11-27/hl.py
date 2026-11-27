import sys;sys.path.insert(0,'/tmp/claude-0')
from boardfx import *
from PIL import Image,ImageDraw,ImageFont
OUT='/root/majlis_local/src/dv/ov'
import os;os.makedirs(OUT,exist_ok=True)
rows=[475,615,755,895];right=682;fs=48;ns=50
def layer(hi,note=False):
    L=Image.new('RGBA',(752,1344),(0,0,0,0));d=ImageDraw.Draw(L)
    for i in range(hi):
        y=rows[i]
        d.rounded_rectangle((150,y-46,right+12,y+46),radius=20,fill=(255,200,0,150) if i==hi-1 else (255,200,0,70))
    if note:
        f=ImageFont.truetype(F,30)
        d.rounded_rectangle((150,rows[0]+44,right+12,rows[0]+92),radius=14,fill=(25,90,170,235))
        d.text(((150+right)/2,rows[0]+68),"قبل الاستحقاق بـ3 أيام تداول (T+3)",font=f,fill='white',anchor='mm',direction='rtl')
    # crisp text on top (same as board)
    pass
    return L
def write_rgba(L):
    d=ImageDraw.Draw(L);f=ImageFont.truetype(F,fs);fn=ImageFont.truetype(F,ns)
    for i,(t,c) in enumerate(zip(items,cols)):
        y=rows[i];r=ns*0.75
        d.ellipse((right-2*r,y-r,right,y+r),outline=c+(255,),width=max(2,ns//8),fill=(255,255,255,255))
        d.text((right-r,y),str(i+1),font=fn,fill=c,anchor='mm')
        d.text((right-2*r-ns*0.4,y),t,font=f,fill=(30,30,35),anchor='rm',direction='rtl')
def to_frame(L,sx,ox,sy,oy):
    W,H=L.size
    big=L.resize((round(W*sx),round(H*sy)),Image.LANCZOS)
    fr=Image.new('RGBA',(720,1280),(0,0,0,0));fr.alpha_composite(big,(round(ox),round(oy)) if ox>=0 and oy>=0 else (0,0)) if ox>=0 and oy>=0 else None
    if ox<0 or oy<0:
        fr=Image.new('RGBA',(720,1280),(0,0,0,0));fr.paste(big,(round(ox),round(oy)),big)
    return fr
if __name__=='__main__':
    sx,ox,sy,oy=[float(v) for v in sys.argv[1:5]]
    for n in range(1,5): to_frame(layer(n),sx,ox,sy,oy).save(f'{OUT}/hl{n}.png')
    to_frame(layer(4),sx,ox,sy,oy).save(f'{OUT}/hl4b.png')
    to_frame(layer(1,True),sx,ox,sy,oy).save(f'{OUT}/hlT3.png')
    print('ok')
