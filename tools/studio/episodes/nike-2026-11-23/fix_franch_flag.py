import subprocess, sys, numpy as np
sys.path.insert(0, __import__('os').path.dirname(__file__))
from kwflag import flag
from PIL import Image, ImageFilter
W, H = 720, 1280
src, out = sys.argv[1], sys.argv[2]
raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', src, '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True).stdout
n = len(raw) // (W * H * 3)
fr = np.frombuffer(raw, np.uint8).reshape(n, H, W, 3).copy()
B0 = (584, 167, 635, 292)   # flag box in frame 0
bw, bh = B0[2] - B0[0], B0[3] - B0[1]
cxs, cys, ws = [], [], []
for i in range(n):
    a = fr[i, 120:260, 520:].astype(int); r, g, b = a[..., 0], a[..., 1], a[..., 2]
    m = (g > 80) & (r < 70) & (g - b > 30) & (g - r > 50)
    ys, xs = np.nonzero(m)
    if len(xs) > 60 and np.percentile(xs, 98) + 520 < 716:
        cxs.append(xs.mean() + 520); cys.append(ys.min() + 120); ws.append(np.percentile(xs, 98) - np.percentile(xs, 2))
    else:
        cxs.append(np.nan); cys.append(np.nan); ws.append(np.nan)
cxs, cys, ws = map(np.array, (cxs, cys, ws))
t = np.arange(n); ok = ~np.isnan(cxs)
# fit smooth quadratic motion on valid frames, extrapolate beyond
pcx = np.polyfit(t[ok], cxs[ok], 2); pcy = np.polyfit(t[ok], cys[ok], 1); pw = np.polyfit(t[ok], ws[ok], 1)
cx0, cy0, w0 = np.polyval(pcx, 0), np.polyval(pcy, 0), np.polyval(pw, 0)
print('valid', ok.sum(), 'of', n)
for i in range(n):
    s = np.polyval(pw, i) / w0
    dx = np.polyval(pcx, i) - cx0; dy = np.polyval(pcy, i) - cy0
    x0 = (B0[0] + B0[2]) / 2 + dx - bw * s / 2; y0 = B0[1] + dy
    w, h = int(round(bw * s)) + 2, int(round(bh * s)) + 2
    x0, y0 = int(round(x0)) - 1, int(round(y0)) - 1
    if x0 >= W: continue
    f = np.asarray(flag(w, h)).astype(float) * np.array([1.0, 0.97, 0.92])
    f = np.asarray(Image.fromarray(f.clip(0, 255).astype('uint8')).filter(ImageFilter.GaussianBlur(1.3)))
    xe = min(W, x0 + w)
    fr[i, y0:y0 + h, x0:xe] = f[:, :xe - x0]
p = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', '24', '-i', '-',
                      '-i', src, '-map', '0:v', '-map', '1:a', '-c:v', 'libx264', '-crf', '14', '-pix_fmt', 'yuv420p', '-c:a', 'copy', out], stdin=subprocess.PIPE)
p.stdin.write(fr.tobytes()); p.stdin.close(); p.wait()
print('wrote', out)
