"""Build the Free My ID walkthrough video: cards + real wizard screenshots + local TTS + captions.
Usage: tts/bin/python build.py <workdir> <out.mp4>"""
import json
import pathlib
import subprocess
import sys
import textwrap
import wave

from PIL import Image, ImageDraw, ImageFont

W = pathlib.Path(sys.argv[1])
OUT = pathlib.Path(sys.argv[2])
SH = W / "shots"
TMP = W / "build"
TMP.mkdir(exist_ok=True)
VOICE = W / "voices" / "en_US-lessac-medium.onnx"
NAVY, RED, WHITE, INK, SOFT = (27, 47, 91), (163, 32, 46), (255, 255, 255), (20, 24, 31), (243, 245, 249)
FB = "/usr/share/fonts/liberation-sans-fonts/LiberationSans-Bold.ttf"
FR = "/usr/share/fonts/liberation-sans-fonts/LiberationSans-Regular.ttf"
SIZE = (1920, 1080)
URL = "freemyid.github.io/freemyid"

# (kind, payload, narration). Narration spells "I.D." so the voice says the letters.
SCENES = [
    ("card", ("Free My ID", "Take your name off the websites that sell it."),
     "This is Free My I.D. It takes your name off the websites that sell it."),
    ("card", ("You may have seen this post", "“I do not give permission to use my information…”"),
     "Maybe you've seen the post: I do not give permission to use my information. The instinct is right. "
     "But that post never reaches the companies that sell your details."),
    ("card", ("Your details are for sale", "Home address · phone number · age · relatives"),
     "People-search sites list your home address, phone number, age and relatives, and sell them to anyone "
     "who pays. A federal consumer agency has warned that includes scammers and stalkers."),
    ("card", ("Free My ID asks them to remove you", "Then it keeps checking. Setup is six short screens."),
     "Free My I.D. asks each of those sites to remove you, the way that site takes requests, and keeps "
     "checking. Here's what setup looks like. It's six short screens."),
    ("shot", "02_welcome_sign", "Step one. Choose who this is for, type your name to sign, and agree."),
    ("shot", "03_name", "Step two. Their name. Add maiden or earlier names if they have any."),
    ("shot", "04_address", "Step three. Where they live. A city and state is enough."),
    ("shot", "05_about", "Step four. A few optional details, like year of birth. These only help tell them "
     "apart from people with the same name, and they're never sent to anyone."),
    ("shot", "06_mailbox", "Step five. Pick an email service for replies. Or choose skip, and Free My I.D. "
     "opens each message for you to send yourself."),
    ("shot", "07_finish", "Step six. Let it keep checking automatically, once a day, quietly in the background."),
    ("shot", "08_dashboard", "That's it. It starts in practice mode, so nothing is sent until you say so."),
    ("shot", "09_settings", "When you're ready, turn on real requests in Settings. If a website ever needs a "
     "real person, a card appears with one big button."),
    ("card", ("No account. No cloud.", "Never asks for your Social Security number, bank or card details."),
     "No account. No cloud. It never asks for your Social Security number, bank, or card details. "
     "Your records stay on your computer."),
    ("card", ("Honest about results", "Asked · Confirmed · Still waiting"),
     "Some sites take weeks, and some list people again later. That's why it keeps checking, and it always "
     "shows you which sites confirmed and which are still waiting."),
    ("card", ("Free My ID", f"Free and open source · {URL}"),
     "Free My I.D. is free and open source. The download link is below this video."),
]


def font(path, n):
    return ImageFont.truetype(path, n)


def flag(d):
    d.rectangle([0, 0, SIZE[0] // 3, 14], fill=NAVY)
    d.rectangle([SIZE[0] // 3, 0, 2 * SIZE[0] // 3, 14], fill=WHITE)
    d.rectangle([2 * SIZE[0] // 3, 0, SIZE[0], 14], fill=RED)


def centered(d, y, text, f, fill, width=36):
    for line in textwrap.wrap(text, width):
        w = d.textlength(line, font=f)
        d.text(((SIZE[0] - w) / 2, y), line, font=f, fill=fill)
        y += f.size * 1.25
    return y


def card(title, sub, path):
    im = Image.new("RGB", SIZE, NAVY)
    d = ImageDraw.Draw(im)
    flag(d)
    y = centered(d, 190, title, font(FB, 104), WHITE, 26)
    centered(d, y + 40, sub, font(FR, 56), (214, 224, 245), 44)
    im.save(path)


def framed(shot, path):
    im = Image.new("RGB", SIZE, SOFT)
    d = ImageDraw.Draw(im)
    flag(d)
    s = Image.open(SH / f"{shot}.png").convert("RGB")
    s.thumbnail((1500, 780))
    x, y = (SIZE[0] - s.width) // 2, 50
    d.rectangle([x - 3, y - 3, x + s.width + 2, y + s.height + 2], fill=(205, 211, 222))
    im.paste(s, (x, y))
    im.save(path)


def tts(text, path):
    subprocess.run([str(W / "tts/bin/piper"), "-m", str(VOICE), "-f", str(path),
                    "--length_scale", "1.08", "--sentence_silence", "0.35"],
                   input=text.encode(), check=True, capture_output=True)
    with wave.open(str(path)) as w:
        return w.getnframes() / w.getframerate()


def ts(t):
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h):02}:{int(m):02}:{int(s):02},{int((s % 1) * 1000):03}"


segs, srt, t0 = [], [], 0.0
for i, (kind, payload, say) in enumerate(SCENES):
    img, wav, mp4 = TMP / f"s{i:02}.png", TMP / f"s{i:02}.wav", TMP / f"s{i:02}.mp4"
    (card(*payload, img) if kind == "card" else framed(payload, img))
    dur = tts(say, wav) + 0.9
    caption = say.replace("I.D.", "ID")
    srt.append(f"{i + 1}\n{ts(t0 + 0.2)} --> {ts(t0 + dur - 0.3)}\n{caption}\n")
    # Burned-in caption bar for viewers watching without sound.
    vf = (f"scale=1920:1080,format=yuv420p,"
          f"fade=t=in:st=0:d=0.35,fade=t=out:st={dur - 0.35:.2f}:d=0.35")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", str(img), "-i", str(wav),
                    "-af", "apad", "-t", f"{dur:.2f}", "-vf", vf, "-r", "30", "-c:v", "libx264",
                    "-preset", "medium", "-crf", "20", "-c:a", "aac", "-b:a", "160k", "-ar", "48000",
                    str(mp4)], check=True)
    segs.append(mp4)
    t0 += dur

(TMP / "list.txt").write_text("".join(f"file '{p}'\n" for p in segs))
srt_path = OUT.with_suffix(".srt")
srt_path.write_text("\n".join(srt))
raw = TMP / "joined.mp4"
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i",
                str(TMP / "list.txt"), "-c", "copy", str(raw)], check=True)
style = "FontName=Liberation Sans,FontSize=13,PrimaryColour=&H00FFFFFF,BackColour=&H99000000,BorderStyle=4,MarginV=28"
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(raw), "-vf",
                f"subtitles={srt_path}:force_style='{style}'", "-c:v", "libx264", "-crf", "20",
                "-preset", "medium", "-c:a", "copy", "-movflags", "+faststart", str(OUT)], check=True)
print(json.dumps({"video": str(OUT), "captions": str(srt_path), "seconds": round(t0, 1)}))
