"""Draw a correct vertically-hanging Kuwait flag (hoist at top): black trapezoid on top,
then vertical stripes left red, middle white, right green (Bader 25 Nov)."""
from PIL import Image, ImageDraw, ImageFilter
import numpy as np
GREEN, WHITE, RED, BLACK = (0, 122, 61), (245, 245, 240), (206, 17, 38), (12, 12, 12)

def flag(w, h, ss=4):
    W, H = w * ss, h * ss
    im = Image.new('RGB', (W, H)); d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W / 3, H], fill=RED)
    d.rectangle([W / 3, 0, 2 * W / 3, H], fill=WHITE)
    d.rectangle([2 * W / 3, 0, W, H], fill=GREEN)
    dep = W * 0.5  # trapezoid depth = 1/4 of flag length (length = 2x width when hanging)
    d.polygon([(0, 0), (W, 0), (W * 0.75, dep), (W * 0.25, dep)], fill=BLACK)
    im = im.resize((w, h), Image.LANCZOS)
    # soft fabric shading: gentle vertical folds
    a = np.asarray(im).astype(float)
    xs = np.linspace(0, 3 * np.pi, w)
    shade = 0.9 + 0.1 * np.cos(xs)
    a *= shade[None, :, None]
    return Image.fromarray(a.clip(0, 255).astype('uint8'))

def paste(img, box, blur=0.8, warm=(1.0, 0.97, 0.9)):
    x0, y0, x1, y1 = [int(round(v)) for v in box]
    f = flag(max(2, x1 - x0), max(2, y1 - y0))
    a = np.asarray(f).astype(float) * np.array(warm)[None, None, :]
    f = Image.fromarray(a.clip(0, 255).astype('uint8')).filter(ImageFilter.GaussianBlur(blur))
    img.paste(f, (x0, y0))
    return img
