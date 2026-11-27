from PIL import Image,ImageDraw,ImageFont
import numpy as np,sys
F='/home/user/Advisers/tools/studio/fonts/PlexArabic-Bold.ttf'
items=["آخر يوم شراء","أول يوم بدون توزيع","يوم الاستحقاق","يوم التوزيع"]
cols=[(205,130,10),(190,45,40),(25,90,170),(25,130,70)]
def clean(im,x0,y0,x1,y1):
    a=np.asarray(im).astype(float)
    top=a[y0-2,x0:x1];bot=a[y1+2,x0:x1]
    for y in range(y0,y1+1):
        t=(y-y0)/(y1-y0)
        row=(1-t)*top+t*bot
        seg=a[y,x0:x1]
        hand=(seg[:,0]-seg[:,2]>95)&(seg[:,0]>120)
        seg[~hand]=row[~hand]
        a[y,x0:x1]=seg
    return Image.fromarray(a.clip(0,255).astype('uint8'))
def write(im,rows_y,right,fs,ns):
    d=ImageDraw.Draw(im);f=ImageFont.truetype(F,fs);fn=ImageFont.truetype(F,ns)
    for i,(t,c) in enumerate(zip(items,cols)):
        y=rows_y[i];r=ns*0.75
        d.ellipse((right-2*r,y-r,right,y+r),outline=c,width=max(2,ns//8))
        d.text((right-r,y),str(i+1),font=fn,fill=c,anchor='mm')
        d.text((right-2*r-ns*0.4,y),t,font=f,fill=(30,30,35),anchor='rm',direction='rtl')
        if i<3:
            ay=(rows_y[i]+rows_y[i+1])/2; ax=right-r
            d.line((ax,ay-ns*0.4,ax,ay+ns*0.2),fill=(80,80,80),width=max(2,ns//10))
            d.polygon([(ax-ns*0.2,ay+ns*0.15),(ax+ns*0.2,ay+ns*0.15),(ax,ay+ns*0.45)],fill=(80,80,80))
    return im
