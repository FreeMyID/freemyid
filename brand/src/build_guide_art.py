"""Spot illustrations for the guides (phone number, helping a parent, credit freeze). Light + dark SVG.
Run: .venv/bin/python brand/src/build_guide_art.py"""
from pathlib import Path
B = Path(__file__).resolve().parent.parent
LIGHT = dict(i="#14264a", p="#ffffff", t="#e6edf8", b="#1b3366", r="#a3202e", o="#1c6639", sk="#d9a273", h="#cfd5df", k="#4a3a30", s="#fbe9c0")
DARK = dict(i="#dde7fb", p="#172131", t="#1d2b45", b="#a9c3f3", r="#f5a3ab", o="#8fd6a6", sk="#c98f62", h="#b8c0cf", k="#2b221d", s="#4a3f22")
def sw(c): return f'stroke="{c["i"]}" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"'
def person(c, x, y, sc, hair):
    return (f'<g transform="translate({x} {y}) scale({sc})"><path d="M-34 70c0-26 14-40 34-40s34 14 34 40z" fill="{c["b"]}" {sw(c)}/>'
            f'<circle r="24" fill="{c["sk"]}" {sw(c)}/><path d="M-24 -4c2-22 46-24 48 0c-10-10-30-12-48 0z" fill="{hair}" {sw(c)}/></g>')
def phone(c):
    return (f'<ellipse cx="160" cy="125" rx="150" ry="105" fill="{c["t"]}"/>'
      f'<rect x="108" y="30" width="104" height="190" rx="16" fill="{c["p"]}" {sw(c)}/>'
      f'<path d="M144 46h32" stroke="{c["i"]}" stroke-width="4" stroke-linecap="round"/>'
      f'<rect x="122" y="70" width="76" height="34" rx="8" fill="{c["t"]}" {sw(c)}/>'
      + "".join(f'<circle cx="{138+i*14}" cy="87" r="4" fill="{c["i"]}"/>' for i in range(4)) +
      f'<path d="M122 132h76M122 152h56" stroke="{c["h"]}" stroke-width="6" stroke-linecap="round"/>'
      f'<circle cx="212" cy="190" r="26" fill="{c["o"]}" {sw(c)}/>'
      f'<path d="M200 190l8 8 15-17" fill="none" stroke="{c["p"]}" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/>'
      f'<path d="M30 226h260" stroke="{c["r"]}" stroke-width="6" stroke-linecap="round"/>')
def parent(c):
    return (f'<ellipse cx="160" cy="125" rx="150" ry="105" fill="{c["t"]}"/>'
      + person(c, 92, 66, .9, c["h"]) + person(c, 228, 78, .8, c["k"]) +
      f'<rect x="96" y="150" width="128" height="66" rx="8" fill="{c["p"]}" {sw(c)}/>'
      f'<path d="M78 224h164" stroke="{c["i"]}" stroke-width="6" stroke-linecap="round"/>'
      f'<path d="M122 172h50M122 192h34" stroke="{c["h"]}" stroke-width="6" stroke-linecap="round"/>'
      f'<path d="M184 176l8 8 16-17" fill="none" stroke="{c["o"]}" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/>'
      f'<path d="M30 238h260" stroke="{c["r"]}" stroke-width="6" stroke-linecap="round"/>')
def freeze(c):
    flake = "".join(f'<path d="M0 -26V26" transform="rotate({a})" stroke="{c["b"]}" stroke-width="5" stroke-linecap="round"/>' for a in (0, 60, 120))
    return (f'<ellipse cx="160" cy="125" rx="150" ry="105" fill="{c["t"]}"/>'
      f'<rect x="60" y="62" width="200" height="126" rx="14" fill="{c["p"]}" {sw(c)}/>'
      f'<path d="M60 92h200" stroke="{c["i"]}" stroke-width="3.5"/>'
      f'<path d="M80 160h56M80 174h36" stroke="{c["h"]}" stroke-width="6" stroke-linecap="round"/>'
      f'<g transform="translate(206 138)">{flake}</g>'
      f'<path d="M30 218h260" stroke="{c["r"]}" stroke-width="6" stroke-linecap="round"/>')
ART = [("phone-number", "A phone with its number hidden and a green check", phone),
       ("help-a-parent", "A grown child and a parent checking a laptop together", parent),
       ("credit-freeze", "A credit card with a snowflake showing a frozen file", freeze)]
for n, t, fn in ART:
    for m, c in (("light", LIGHT), ("dark", DARK)):
        (B / f"illustrations/{n}-{m}.svg").write_text(
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 250" role="img" aria-labelledby="t"><title id="t">{t}</title>{fn(c)}</svg>')
