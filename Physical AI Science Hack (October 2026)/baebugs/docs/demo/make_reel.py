import subprocess, numpy as np, wave, json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
R = Path("/home/claude/baebugs"); O = Path(__file__).parent; W, H, FPS = 1280, 720, 30
BG = (16, 22, 40); INK = (244, 241, 251); CORAL = (242, 84, 91); MUTE = (170, 178, 205)
FD = "/tmp/claude-0/-home-claude/c015c63d-cbe8-5a31-959f-828cd3f1cdf6/scratchpad/node_modules/@fontsource/bricolage-grotesque/files/"
def font(sz, w=800):
    try: return ImageFont.truetype(FD + f"bricolage-grotesque-latin-{w}-normal.woff", sz)
    except Exception: return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", sz)
logo = Image.open(R / "assets/brand/baebugs_mark_512.png").convert("RGBA")
def card(n, title, sub, out):
    im = Image.new("RGB", (W, H), BG); d = ImageDraw.Draw(im)
    m = logo.resize((150, 150)); im.paste(m, (90, 90), m)
    if n: d.text((96, 300), f"STEP {n}", font=font(30, 700), fill=CORAL)
    d.text((96, 345), title, font=font(78), fill=INK)
    y = 455
    for line in sub: d.text((98, y), line, font=font(30, 700), fill=MUTE); y += 44
    im.save(out)
def fit(src, out, caption):
    im = Image.open(src).convert("RGB"); im.thumbnail((W, H - 80)); c = Image.new("RGB", (W, H), BG)
    c.paste(im, ((W - im.width) // 2, (H - 80 - im.height) // 2)); d = ImageDraw.Draw(c)
    d.text((40, H - 62), caption, font=font(28, 700), fill=INK); c.save(out)
def filters_sheet(out):
    import trimesh, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    names = ["RND-1-4", "HEX-1-4", "SLOT-1-8x1-2", "HEART-1-4", "SS-HEX-2.5AF", "SS-MESH-2.0"]
    fig, ax = plt.subplots(2, 3, figsize=(12.8, 6.4), facecolor="#101628")
    for a, n in zip(ax.flat, names):
        m = trimesh.load(R / f"print/filters/stl/{n}.stl"); s = m.section(plane_origin=m.bounds.mean(0), plane_normal=[0, 0, 1])
        p, _ = s.to_planar()
        for e in p.discrete: a.plot(e[:, 0], e[:, 1], color="#f2545b" if n.startswith("SS") else "#cfd6f2", lw=0.6)
        a.set_aspect("equal"); a.axis("off"); a.set_title(n + ("  316L" if n.startswith("SS") else "  printed"), color="#f4f1fb", fontsize=13)
    fig.savefig(out, dpi=100, facecolor=fig.get_facecolor()); plt.close(fig)
def seg_img(src, out, dur):
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-loop", "1", "-i", str(src), "-t", str(dur), "-vf",
                    f"scale={W}:{H},zoompan=z='min(zoom+0.0006,1.05)':d={int(dur*FPS)}:s={W}x{H}:fps={FPS},fade=t=in:d=0.4,fade=t=out:st={dur-0.4}:d=0.4,format=yuv420p",
                    "-r", str(FPS), "-c:v", "libx264", "-preset", "veryfast", "-crf", "22", str(out)], check=True)
def seg_vid(src, out, start, dur, caption):
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", str(start), "-i", str(src), "-t", str(dur), "-an", "-vf",
                    f"scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=0x101628,fps={FPS},"
                    f"drawbox=y={H-80}:h=80:w={W}:color=0x101628@0.85:t=fill,"
                    f"fade=t=in:d=0.4,fade=t=out:st={dur-0.4}:d=0.4,format=yuv420p",
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "22", str(out)], check=True)
S = []; k = 0
def add_card(n, t, sub, dur=2.6):
    global k; k += 1; p = O / f"c{k:02d}.png"; card(n, t, sub, p); v = O / f"s{k:02d}.mp4"; seg_img(p, v, dur); S.append(v)
def add_img(src, cap, dur=3.6):
    global k; k += 1; p = O / f"i{k:02d}.png"; fit(src, p, cap); v = O / f"s{k:02d}.mp4"; seg_img(p, v, dur); S.append(v)
def add_vid(src, start, dur, cap_img=None):
    global k; k += 1; v = O / f"s{k:02d}.mp4"; seg_vid(src, v, start, dur, ""); S.append(v)
filters_sheet(O / "filters.png")
add_card(None, "baebugs", ["Bags in, barcodes out: a sorting line where every step", "is photographed, judged and hashed."], 3.2)
add_card(1, "Interchangeable filters", ["One tray frame, 32 swappable plates, 316L inserts"])
add_img(O / "filters.png", "32 plates: printed shapes for fit, 316L hex / perf / mesh for wet contact")
add_card(2, "Plastic frame, metal aperture", ["FDM failed on the perforated drum -> zones move to PA12"])
add_img(R / "assets/photos/fdm_trommel_attempt1.jpg", "FDM attempt 1: caps, crank, feet OK; perforated zones failed")
add_img(R / "print/packages/trommel_biokea_x1c/plate_preview.png", "Sized to BioKEA trays: one zone per tray, 85 mm perforated band")
add_card(3, "Toys as test standards", ["91 parametric insects, printed in PA12 today"])
add_vid(R / "assets/videos/sift_tumble_2.mp4", 0.3, 4.0)
add_img(R / "assets/photos/pa12_toys_box.jpg", "Printed, depowdered; every toy has an STL, an OpenSCAD file and a hash")
add_card(4, "Vision at every step", ["Pixels -> tiles -> objects -> frame, all Merkle-hashed"])
add_img(R / "docs/ladder_demo/snapshots/02_sort.png", "Sort: the toy, its box and its hash")
add_img(R / "docs/ladder_demo/snapshots/02_pick.png", "Pick verified: the only change is one box where the toy was")
add_card(5, "Local models, escalation ladder", ["family -> order -> local VLM -> Claude -> human"])
add_img(R / "docs/toy_photo_models/pa12_toys_two_on_floor_models.jpg", "Real toy photo: YOLOE (yellow), OWLv2 + order model (blue)")
add_card(6, "Chain of custody", ["914 file atoms, 45 weight + 176 value hashes, 8 breaks on record"])
add_vid(R / "docs/demo/baebugs_mvp_demo.mp4", 2.0, 9.0)
add_card(7, "Remix it", ["STL -> OpenSCAD, Protocol Board, contest any hash"])
add_img(O.parent / "board_1280.png", "Protocol Board: pin, run step by step, remix, contest")
add_card(None, "baebugs", ["github.com/biobitworks/baebugs", "MIT code  |  AGPL weights  |  museum photos credited"], 3.4)
lst = O / "list.txt"; lst.write_text("".join(f"file '{v}'\n" for v in S))
subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(O / "video.mp4")], check=True)
dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(O / "video.mp4")], capture_output=True, text=True).stdout)
# original soundtrack: soft pads + plucks in D major, 84 bpm, one chord per 2 bars
sr = 44100; t = np.arange(int(sr * (dur + 1))) / sr; out = np.zeros_like(t)
f = lambda n: 440 * 2 ** ((n - 69) / 12)
chords = [[50, 57, 62, 66], [47, 54, 59, 62], [43, 50, 55, 59], [45, 52, 57, 61]]
bar = 60 / 84 * 4
for i in range(int(dur / (2 * bar)) + 2):
    c = chords[i % 4]; s0 = i * 2 * bar; m = (t >= s0) & (t < s0 + 2 * bar + 0.6); tt = t[m] - s0
    env = np.minimum(1, tt / 0.8) * np.exp(-np.maximum(0, tt - 2 * bar) * 3)
    for n in c: out[m] += 0.05 * env * (np.sin(2 * np.pi * f(n) * tt) + 0.3 * np.sin(2 * np.pi * f(n + 12) * tt + 1))
    for j in range(8):
        n = c[[0, 2, 1, 3, 2, 3, 1, 2][j]] + 12; ps = s0 + j * bar / 4; mm = (t >= ps) & (t < ps + 1.2); u = t[mm] - ps
        out[mm] += 0.06 * np.exp(-u * 4.5) * np.sin(2 * np.pi * f(n) * u) * (1 if j % 2 == 0 else 0.6)
out = out / np.max(np.abs(out)) * 0.6; fade = int(sr * 2.5); out[-fade:] *= np.linspace(1, 0, fade); out[:int(sr * .8)] *= np.linspace(0, 1, int(sr * .8))
with wave.open(str(O / "music.wav"), "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes((out * 32767).astype(np.int16).tobytes())
subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(O / "video.mp4"), "-i", str(O / "music.wav"), "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
                "-shortest", "-movflags", "+faststart", str(O / "baebugs_reel.mp4")], check=True)
print(dur, (O / "baebugs_reel.mp4").stat().st_size)
