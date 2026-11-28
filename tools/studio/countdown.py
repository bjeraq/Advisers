#!/usr/bin/env python3
"""عد تنازلي محلي (بدون كريدت): أرقام كبيرة N←1، تكة كل ثانية، بدون كلام — بعد سؤال لغز المتابعين.

    python3 tools/studio/countdown.py <bg.png> <out.mp4> [--disc disc.png] [--n 5] [--res 720]
الخلفية تتعتم، والرقم بالنص بدائرة ذهبية، وشريط الإخلاء (disc.png من build) فوقه لو انعطى.
الترميز نفس build.py (h264 30fps + aac 44.1k ستيريو) عشان يندمج بـ concat copy كمشهد precomp.
"""
import os, sys, argparse, subprocess, tempfile
from PIL import Image, ImageDraw, ImageFont, ImageEnhance

HERE = os.path.dirname(os.path.abspath(__file__))
GOLD = (212, 167, 71, 255)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('bg'); ap.add_argument('out')
    ap.add_argument('--disc'); ap.add_argument('--n', type=int, default=5)
    ap.add_argument('--res', type=int, default=720)
    a = ap.parse_args()
    S = 1 if a.res == 720 else 1.5
    W, H = round(720 * S), round(1280 * S)
    bg = Image.open(a.bg).convert('RGB')
    r = max(W / bg.width, H / bg.height)
    bg = bg.resize((round(bg.width * r), round(bg.height * r)), Image.LANCZOS)
    bg = bg.crop(((bg.width - W) // 2, (bg.height - H) // 2, (bg.width - W) // 2 + W, (bg.height - H) // 2 + H))
    bg = ImageEnhance.Brightness(bg).enhance(0.45).convert('RGBA')
    disc = Image.open(a.disc).convert('RGBA').resize((W, H)) if a.disc else None
    font = ImageFont.truetype(os.path.join(HERE, 'fonts', 'PlexArabic-Bold.ttf'), round(300 * S))
    tmp = tempfile.mkdtemp()
    cy = round(H * 0.27)
    for i, k in enumerate(range(a.n, 0, -1)):
        im = bg.copy(); d = ImageDraw.Draw(im)
        R = round(190 * S)
        d.ellipse((W // 2 - R, cy - R, W // 2 + R, cy + R), fill=(10, 22, 26, 200), outline=GOLD, width=round(10 * S))
        d.text((W // 2, cy), str(k), font=font, fill=(255, 255, 255, 255), anchor='mm')
        if disc:
            im = Image.alpha_composite(im, disc)
        im.convert('RGB').save(f'{tmp}/f{i}.png')
    lst = ''.join(f"file '{tmp}/f{i}.png'\nduration 1\n" for i in range(a.n)) + f"file '{tmp}/f{a.n - 1}.png'\n"
    open(f'{tmp}/l.txt', 'w').write(lst)
    tick = "0.5*sin(2*PI*1800*t)*exp(-40*t)"
    subprocess.run(
        f"ffmpeg -v error -y -f concat -safe 0 -i {tmp}/l.txt "
        f"-f lavfi -t 1 -i \"aevalsrc='{tick}':s=44100\" "
        f"-filter_complex \"[1:a]aloop=loop={a.n - 1}:size=44100,atrim=0:{a.n},aformat=channel_layouts=stereo,volume=-6dB[a];"
        f"[0:v]fps=30,format=yuv420p[v]\" -map \"[v]\" -map \"[a]\" -t {a.n} -r 30 "
        f"-c:v libx264 -crf {20 if a.res == 720 else 18} -preset fast -c:a aac -b:a 192k -ar 44100 {a.out}",
        shell=True, check=True)
    print('countdown', a.out)


if __name__ == '__main__':
    main()
