"""مزامنة شفاه دقيقة بالكلمة: يعيد توقيت فيديو المقطع (تمطيط متغير) بحيث كل كلمة نطقها
النموذج بالمقطع تطلع على نفس الكلمة بتسجيلنا الأصلي، بدل عامل F واحد ينحرف بآخر الجملة.

    python3 retime.py <clip.mp4> <rec.mp3> <rec_words.json> <out.mp4> [pre=0.30] [post=0.45]

المخرج: فيديو بمسار صوتي = تسجيلنا (من قبل أول كلمة بـ pre لين بعد آخر كلمة بـ post)،
فلما يمر عليه align1 يطلع F≈1 والشفاه مركبة كلمة بكلمة. الصوت الأصلي ما يتغير (لا تمطيط ولا طبقة).
"""
import os, sys, json, subprocess, tempfile, difflib, re
import numpy as np

os.environ.setdefault('HF_HOME', '/home/user/.hfcache')
FPS = 24
DIAC = re.compile('[ً-ْـٰ]')


def norm(w):
    w = DIAC.sub('', w)
    w = re.sub('[إأآا]', 'ا', w).replace('ة', 'ه').replace('ى', 'ي').replace('ؤ', 'و').replace('ئ', 'ي')
    w = re.sub(r'[^\w]', '', w)
    for p in ('وال', 'بال', 'لل', 'ال', 'و'):
        if w.startswith(p) and len(w) - len(p) >= 2:
            w = w[len(p):]
            break
    return w


def clip_words(clip):
    from faster_whisper import WhisperModel
    wav = tempfile.mktemp(suffix='.wav')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', clip, '-vn', '-ac', '1', '-ar', '16000', wav], check=True)
    m = WhisperModel('medium', device='cpu', compute_type='int8')
    segs, _ = m.transcribe(wav, language='ar', word_timestamps=True, vad_filter=True)
    return [{'w': w.word.strip(), 's': w.start, 'e': w.end} for s in segs for w in s.words]


def probe(p, what='format=duration'):
    return float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', what, '-of', 'csv=p=0', p],
                                capture_output=True, text=True).stdout.strip().split('\n')[0])


def anchors(cw, rw):
    a = [norm(w['w']) for w in cw]
    b = [norm(w['w']) for w in rw]
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    pairs = []
    for blk in sm.get_matching_blocks():
        for k in range(blk.size):
            i, j = blk.a + k, blk.b + k
            if a[i]:
                pairs.append((cw[i]['s'], rw[j]['s']))
    # fuzzy pass for words difflib missed (whisper spelling noise)
    used_c = {p[0] for p in pairs}
    for j, w in enumerate(rw):
        if any(abs(p[1] - w['s']) < 1e-6 for p in pairs):
            continue
        best = max(((difflib.SequenceMatcher(None, norm(c['w']), b[j]).ratio(), c) for c in cw
                    if c['s'] not in used_c), default=(0, None), key=lambda x: x[0])
        if best[0] >= 0.75:
            pairs.append((best[1]['s'], w['s']))
            used_c.add(best[1]['s'])
    pairs.sort(key=lambda p: p[1])
    # keep a monotonic chain with sane local slopes
    out = []
    for c, r in pairs:
        if out and (c <= out[-1][0] or r <= out[-1][1]):
            continue
        if out:
            sl = (c - out[-1][0]) / (r - out[-1][1])
            if not 0.45 <= sl <= 2.2:
                continue
        out.append((c, r))
    return out


def main(clip, rec, rec_words, out, pre=0.30, post=0.45):
    pre, post = float(pre), float(post)
    # rec_words (from words.py) can be proportional estimates — use real whisper timings of the recording
    rw = [w for w in clip_words(rec) if w['w'].strip()] or [w for w in json.load(open(rec_words)) if w.get('w', '').strip()]
    cw = clip_words(clip)
    cdur = probe(clip)
    rh, rt = rw[0]['s'], rw[-1]['e']
    A = anchors(cw, rw)
    if len(A) < 2:
        raise SystemExit(f'{clip}: only {len(A)} anchors — keep uniform align')
    sl0 = (A[-1][0] - A[0][0]) / max(1e-3, A[-1][1] - A[0][1])
    pre = min(pre, max(0.05, (A[0][0] - 0.0) / max(sl0, 0.5) + (A[0][1] - rh)))  # no frozen lead-in
    T = pre + (rt - rh) + post
    # control points: output time -> clip time
    xs = [pre + (r - rh) for c, r in A]
    ys = [c for c, r in A]
    c_end = min(cdur - 1.0 / FPS, (cw[-1]['e'] if cw else cdur) + post)
    last_slope = (ys[-1] - ys[0]) / max(1e-3, xs[-1] - xs[0])
    x0, y0 = 0.0, max(0.0, ys[0] - xs[0] * last_slope)
    xs = [x0] + xs + [T]
    ys = [y0] + ys + [max(ys[-1] + 0.05, min(c_end, ys[-1] + (T - xs[-2]) * last_slope))]
    tq = np.arange(int(round(T * FPS))) / FPS
    src_t = np.clip(np.interp(tq, xs, ys), 0, cdur - 1.0 / FPS)
    idx = np.round(src_t * FPS).astype(int)

    W, H = [int(v) for v in subprocess.run(
        ['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height', '-of', 'csv=p=0', clip],
        capture_output=True, text=True).stdout.strip().split(',')]
    raw = tempfile.mktemp(suffix='.rgb')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', clip, '-vf', f'fps={FPS}', '-f', 'rawvideo', '-pix_fmt', 'rgb24', raw], check=True)
    fr = np.memmap(raw, dtype=np.uint8, mode='r').reshape(-1, H, W, 3)
    idx = np.clip(idx, 0, len(fr) - 1)
    a0 = max(0.0, rh - pre)
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                          '-i', rec, '-filter_complex', f"[1:a]atrim={a0:.3f}:{rt + post:.3f},asetpts=PTS-STARTPTS,adelay={int(max(0, pre - rh) * 1000)}|{int(max(0, pre - rh) * 1000)},apad,atrim=0:{T:.3f}[a]",
                          '-map', '0:v', '-map', '[a]', '-c:v', 'libx264', '-crf', '14', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k', '-t', f'{T:.3f}', out],
                         stdin=subprocess.PIPE)
    for i in idx:
        p.stdin.write(fr[i].tobytes())
    p.stdin.close(); p.wait()
    os.remove(raw)
    sl = np.diff(ys) / np.maximum(1e-3, np.diff(xs))
    if os.environ.get("RT_DEBUG"): print("xs", np.round(xs, 2).tolist(), "\nys", np.round(ys, 2).tolist())
    print(f'{os.path.basename(clip)}: anchors {len(A)}/{len(rw)} words, out {T:.2f}s, '
          f'slope {sl.min():.2f}-{sl.max():.2f}')


if __name__ == '__main__':
    main(*sys.argv[1:])
