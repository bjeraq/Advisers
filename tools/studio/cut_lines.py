"""Cut an intone clip into per-line clips by locating each source line in the clip audio
(envelope cross-correlation, searched in order). usage: cut_lines.py clip.mp4 out_prefix line1.mp3:name1 line2.mp3:name2 ..."""
import sys, subprocess, numpy as np
SR = 8000
def pcm(path):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-ac', '1', '-ar', str(SR), '-f', 's16le', '-'],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.int16).astype(np.float32)
def env(x, hop=80):  # 10 ms
    n = len(x) // hop
    e = np.sqrt((x[:n * hop].reshape(n, hop) ** 2).mean(1))
    return (e - e.mean()) / (e.std() + 1e-6)
clip, prefix, items = sys.argv[1], sys.argv[2], [a.split(':') for a in sys.argv[3:]]
ce = env(pcm(clip)); clip_dur = len(ce) / 100
cursor, res = 0, []
for path, name in items:
    le = env(pcm(path)); L = len(le)
    best, bi = -1e9, cursor
    for i in range(cursor, max(cursor + 1, len(ce) - L // 2)):
        seg = ce[i:i + L]
        if len(seg) < L // 2: break
        s = float(np.dot(seg, le[:len(seg)]) / len(seg))
        if s > best: best, bi = s, i
    res.append((name, bi / 100, L / 100, best)); cursor = bi + int(L * 0.8)
for k, (name, st, d, sc) in enumerate(res):
    a = max(0, st - 0.25)
    nxt = res[k + 1][1] - 0.1 if k + 1 < len(res) else clip_dur
    b = min(nxt, st + d + 0.6, clip_dur)
    out = f'{prefix}{name}.mp4'
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{a:.3f}', '-i', clip, '-t', f'{b - a:.3f}',
                    '-c:v', 'libx264', '-crf', '16', '-preset', 'fast', '-c:a', 'aac', out], check=True)
    print(f'{name}: line at {st:.2f}s (len {d:.2f}, score {sc:.2f}) -> cut {a:.2f}-{b:.2f} -> {out}')
