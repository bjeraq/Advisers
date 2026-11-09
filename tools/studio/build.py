#!/usr/bin/env python3
"""مُجمِّع الحلقة: من ملف الحلقة (episode.json) إلى فيديو ريلز جاهز — مجاني بالكامل (ساندبوكس هيغزفيلد).

الخطوات: توقيت الكلمات لكل سطر ← محاذاة كل مشهد تزامن مع تسجيله الأصلي (تمطيط الفيديو)
← رسومات تفاعلية وبطاقات ← ترانسكريبت كلمة-كلمة ← تركيب كل مشهد ← دمج ← manifest.json.

    python3 tools/studio/build.py <episode.json> --res 720 --stage draft     # مسودة للمراجعة
    python3 tools/studio/build.py <episode.json> --res 1080 --stage final    # بعد «كل شي تمام» فقط
خيارات: --reuse (يعيد استخدام المحاذاة والرسومات الموجودة) • --scenes bull,judge (يعيد بناء مشاهد محددة فقط)

يشتغل من مجلد العمل اللي فيه src/ و fonts/ (مسارات ملف الحلقة نسبية له)، والمخرجات في build/<stage><res>/.
أنواع المشاهد: lipsync (متحدث واحد) • clash (متحدثان بمقطع واحد) • vo_clip (مقطع متحرك + تعليق صوتي)
• still_vo (صورة ثابتة بزووم بطيء + تعليق صوتي — للصقر لأن نموذج الشفاه يرفض المنقار).
"""
import os, sys, json, re, argparse, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault('HF_HOME', '/home/user/.hfcache')
import captions, fx, cards  # noqa: E402

FPS = 30


def sh(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"FAILED: {cmd[:400]}\n{r.stderr[-1500:]}")
    return r.stdout


def gain_db(audio):
    r = subprocess.run(f"ffmpeg -hide_banner -i '{audio}' -vn -af volumedetect -f null - 2>&1",
                       shell=True, capture_output=True, text=True)
    mv = float(re.search(r'mean_volume: ([-0-9.]+)', r.stdout + r.stderr).group(1))
    return max(-8, min(8, -18 - mv))   # كسب ثابت فقط — ممنوع loudnorm أو أي ضغط ديناميكي


def find_cue(ws, sub, scene):
    for w in ws:
        if sub in w['w']:
            return w['s']
    raise SystemExit(f"[{scene}] كلمة الإشارة «{sub}» مو موجودة: {' '.join(w['w'] for w in ws)}")


def shake(t0, W, H, S):
    sw, sh_ = round(742 * S), round(1320 * S)
    ax, ox, ay, oy = round(10 * S), round(11 * S), round(7 * S), round(20 * S)
    win = f"between(t,{t0:.2f},{t0:.2f}+0.4)"
    return (f"scale={sw}:{sh_},crop={W}:{H}:x='{ox}+{ax}*sin(45*t)*{win}'"
            f":y='{oy}+{ay}*sin(53*t)*{win}'")


def ensure_words(ep):
    import words as wordmod
    os.makedirs('build/words', exist_ok=True)
    paths = {}
    for name, ln in ep['lines'].items():
        p = ln.get('words') or f'build/words/{name}.json'
        if not os.path.exists(p):
            json.dump(wordmod.word_times(ln['audio'], ln['text']), open(p, 'w'), ensure_ascii=False)
            print('words', name)
        paths[name] = p
    return paths


def scene_track(sc, ep, wpaths, video, B, reuse):
    """يرجع (كلمات المشهد بتوقيتها النهائي، meta{f,dur}, مسار الصوت أو None)."""
    sid, t = sc['id'], sc['type']
    trk = f'{B}/trk/{sid}'
    if t in ('lipsync', 'clash'):
        if not (reuse and os.path.exists(trk + '_m.json')):
            if t == 'lipsync':
                import align1
                ln = ep['lines'][sc['line']]
                align1.main(video, ln['audio'], wpaths[sc['line']], trk + '.wav', trk + '_w.json', trk + '_m.json')
            else:
                import align2
                a, b = sc['lines']
                align2.main(video, ep['lines'][a]['audio'], wpaths[a], ep['lines'][b]['audio'], wpaths[b],
                            trk + '.wav', trk + '_w.json', trk + '_m.json')
        return json.load(open(trk + '_w.json')), json.load(open(trk + '_m.json')), trk + '.wav'
    d = sc.get('delay', 0.5)
    ws = [{'w': w['w'], 's': round(w['s'] + d, 3), 'e': round(w['e'] + d, 3)}
          for w in json.load(open(wpaths[sc['line']]))]
    return ws, {'f': 1, 'dur': sc['duration']}, None


def render_scene(sc, ep, wpaths, a, B, geo):
    W, H, S, crf, fonts = geo
    sid, t = sc['id'], sc['type']
    video = None
    if t != 'still_vo':
        v = sc['video']
        video = v[a.stage] if isinstance(v, dict) else v
        if not os.path.exists(video):
            raise SystemExit(f"[{sid}] ملف الفيديو ناقص: {video}")
    ws, meta, wav = scene_track(sc, ep, wpaths, video, B, a.reuse)
    ass = f'{B}/trk/{sid}.ass'
    captions.write(ass, [(ws, 0.0)], a.res)

    inputs, chain = [], []

    def add(arg):
        inputs.append(arg)
        return len(inputs) - 1

    if t in ('lipsync', 'clash'):
        iv, ia = add(f"-i {video}"), add(f"-i {wav}")
        chain.append(f"[{iv}:v]setpts=PTS*{meta['f']},fps={FPS},scale={W}:{H}[b]")
        amap = f"{ia}:a"
    else:
        audio = ep['lines'][sc['line']]['audio']
        ms = int(sc.get('delay', 0.5) * 1000)
        if t == 'vo_clip':
            iv = add(f"-i {video}")
            chain.append(f"[{iv}:v]fps={FPS},scale={W}:{H}[b]")
        else:
            iv = add(f"-loop 1 -i {sc['image']}")
            N = int(sc['duration'] * FPS)
            chain.append(f"[{iv}:v]scale={2 * W}:{2 * H},zoompan=z='1.12-0.10*on/{N}':d={N}:"
                         f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={W}x{H}:fps={FPS},format=yuv420p[b]")
        ia = add(f"-i {audio}")
        chain.append(f"[{ia}:a]volume={gain_db(audio):.1f}dB,aresample=44100,"
                     f"aformat=channel_layouts=stereo,adelay={ms}|{ms},apad[a]")
        amap = "[a]"

    cur, n = 'b', 0

    def step(expr):
        nonlocal cur, n
        n += 1
        chain.append(f"[{cur}]{expr}[v{n}]")
        cur = f'v{n}'

    cue = gdur = None
    g = sc.get('graphic')
    if g:
        cue = find_cue(ws, g['cue'], sid)
        gdur = ep['graphics'][g['name']]['dur']
        x, y, bw = g['box']                       # بإحداثيات 720 — الوجه ما ينغطى
        bh = round(bw * fx.BASE_H / fx.BASE_W)
        X, Y, BW, BH = round(x * S), round(y * S), round(bw * S), round(bh * S)
        ig = add(f"-i {B}/fx/{g['name']}.mov")
        chain.append(f"[{ig}:v]setpts=PTS+{cue:.2f}/TB,format=rgba,scale={BW}:{BH}[g]")
        n += 1
        chain.append(f"[{cur}][g]overlay={X}:{Y}:enable='between(t,{cue:.2f},{cue + gdur:.2f})'[v{n}]")
        cur = f'v{n}'
    c = sc.get('card')
    if c:
        at = c.get('at', 'cue')
        st = cue if at == 'cue' else (cue + gdur if at == 'after_graphic' else float(at))
        ic = add(f"-loop 1 -i {B}/ov/{c['name']}.png")
        chain.append(f"[{ic}:v]format=rgba,fade=t=in:st={st:.2f}:d={c.get('fade', 0.5)}:alpha=1[c]")
        n += 1
        chain.append(f"[{cur}][c]overlay=0:0[v{n}]")
        cur = f'v{n}'
    idc = add(f"-loop 1 -i {B}/ov/disc.png")
    chain.append(f"[{idc}:v]format=rgba[d]")
    n += 1
    chain.append(f"[{cur}][d]overlay=0:0[v{n}]")
    cur = f'v{n}'
    pre = shake(find_cue(ws, sc['shake'], sid), W, H, S) + ',' if sc.get('shake') else ''
    chain.append(f"[{cur}]{pre}subtitles={ass}:fontsdir={fonts},format=yuv420p[v]")

    out = f'{B}/scenes/{sid}.mp4'
    sh(f"ffmpeg -v error -y {' '.join(inputs)} -filter_complex \"{';'.join(chain)}\" "
       f"-map \"[v]\" -map \"{amap}\" -t {meta['dur']} -r {FPS} -c:v libx264 -crf {crf} -preset fast "
       f"-c:a aac -b:a 192k {out}")
    print(f"scene {sid}: {meta['dur']}s F={meta['f']}" + (f" cue {cue:.2f}" if cue is not None else ''))
    return out


def duration(p):
    return float(sh(f"ffprobe -v error -show_entries format=duration -of csv=p=0 {p}").strip())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('episode')
    ap.add_argument('--res', type=int, default=720, choices=[720, 1080])
    ap.add_argument('--stage', default='draft', choices=['draft', 'final'])
    ap.add_argument('--reuse', action='store_true')
    ap.add_argument('--scenes')
    a = ap.parse_args()
    ep = json.load(open(a.episode))
    S = 1 if a.res == 720 else 1.5
    W, H = (720, 1280) if a.res == 720 else (1080, 1920)
    fonts = ep.get('fonts', 'fonts')
    geo = (W, H, S, 20 if a.res == 720 else 18, fonts)
    B = f"build/{a.stage}{a.res}"
    for sub in ('trk', 'fx', 'ov', 'scenes'):
        os.makedirs(f'{B}/{sub}', exist_ok=True)

    wpaths = ensure_words(ep)
    have_fx = all(os.path.exists(f'{B}/fx/{k}.mov') for k in ep['graphics'])
    if not (a.reuse and have_fx):
        for name, spec in ep['graphics'].items():
            fx.render(name, spec, f'{B}/fx', S, bold=f'{fonts}/PlexArabic-Bold.ttf')
    if not (a.reuse and os.path.exists(f'{B}/ov/disc.png')):
        cards.render_all(ep['cards'], f'{B}/ov', S, fonts)

    only = set(a.scenes.split(',')) if a.scenes else None
    files = []
    for sc in ep['scenes']:
        out = f"{B}/scenes/{sc['id']}.mp4"
        if only is None or sc['id'] in only:
            render_scene(sc, ep, wpaths, a, B, geo)
        elif not os.path.exists(out):
            raise SystemExit(f"مشهد ناقص ولم يُطلب بناؤه: {out}")
        files.append(out)

    with open(f'{B}/scenes/list.txt', 'w') as fh:
        fh.writelines(f"file '{os.path.basename(p)}'\n" for p in files)
    final = f"{B}/{ep['slug']}_{a.stage}{a.res}.mp4"
    sh(f"ffmpeg -v error -y -f concat -safe 0 -i {B}/scenes/list.txt -c copy {final}")
    manifest = {'output': final, 'res': a.res, 'stage': a.stage,
                'scenes': [{'id': sc['id'], 'file': p, 'dur': round(duration(p), 3),
                            'lines': sc.get('lines') or [sc['line']]}
                           for sc, p in zip(ep['scenes'], files)]}
    json.dump(manifest, open(f'{B}/manifest.json', 'w'), ensure_ascii=False, indent=1)
    print(f"BUILT {final} {duration(final):.2f}s")


if __name__ == '__main__':
    main()
