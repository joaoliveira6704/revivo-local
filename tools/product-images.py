#!/usr/bin/env python3
"""
Gera as ilustrações dos produtos de demonstração (design/products/<imagem>.jpg).

Cada imagem é um SVG desenhado aqui (traço escuro, laranja da marca, linhas de
camada a lembrar a impressão 3D) convertido com rsvg-convert e depois para JPG.

Uso:
  python3 -I tools/product-images.py            # gera todas
  python3 -I tools/product-images.py vaso farol # só estas
"""
import json
import math
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'design' / 'products'

INK, O, O2, G, CREAM, LINE = '#1E2329', '#F2611D', '#FF9A3C', '#1F9D6B', '#FFFFFF', '#E4DCD1'
SW = 'stroke="%s" stroke-width="12" stroke-linejoin="round" stroke-linecap="round"' % INK


def frame(body, glow=O2):
    """Fundo comum: creme quente, grelha de pontos, brilho e sombra de base."""
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1000" width="1000" height="1000">
<defs>
  <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#FBF8F4"/><stop offset="1" stop-color="#F0E8DE"/></linearGradient>
  <radialGradient id="glow" cx=".78" cy=".2" r=".55"><stop offset="0" stop-color="{glow}" stop-opacity=".28"/><stop offset="1" stop-color="{glow}" stop-opacity="0"/></radialGradient>
  <radialGradient id="shadow" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="#1E2329" stop-opacity=".18"/><stop offset="1" stop-color="#1E2329" stop-opacity="0"/></radialGradient>
  <pattern id="dots" width="40" height="40" patternUnits="userSpaceOnUse"><circle cx="2" cy="2" r="2" fill="#1E2329" opacity=".07"/></pattern>
  <pattern id="layers" width="12" height="12" patternUnits="userSpaceOnUse"><rect width="12" height="5" fill="#000" opacity=".07"/></pattern>
  <linearGradient id="og" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{O}"/><stop offset="1" stop-color="{O2}"/></linearGradient>
</defs>
<rect width="1000" height="1000" fill="url(#bg)"/>
<rect width="1000" height="1000" fill="url(#dots)"/>
<rect width="1000" height="1000" fill="url(#glow)"/>
<ellipse cx="500" cy="815" rx="330" ry="46" fill="url(#shadow)"/>
{body}
</svg>'''


def orange(shape):
    """Forma laranja com linhas de camada por cima e contorno escuro."""
    return f'<g>{shape.replace("FILL", "url(#og)")}{shape.replace("FILL", "url(#layers)").replace(SW, "")}{shape.replace("FILL", "none")}</g>'


def gear(cx, cy, r_out, r_in, teeth, rot=0):
    pts = []
    for i in range(teeth * 4):
        a = math.radians(rot) + i * math.pi * 2 / (teeth * 4)
        r = r_out if i % 4 in (1, 2) else r_in
        pts.append(f'{cx + r * math.cos(a):.1f},{cy + r * math.sin(a):.1f}')
    return 'M' + ' L'.join(pts) + ' Z'


ART = {
    'puxador': lambda: frame(
        f'<rect x="255" y="540" width="80" height="170" rx="22" fill="{CREAM}" {SW}/>'
        f'<rect x="665" y="540" width="80" height="170" rx="22" fill="{CREAM}" {SW}/>'
        + orange(f'<path d="M210 470 Q500 330 790 470 L790 545 Q500 420 210 545 Z" fill="FILL" {SW}/>')
        + f'<circle cx="295" cy="745" r="14" fill="{INK}"/><circle cx="705" cy="745" r="14" fill="{INK}"/>'),

    'botoes': lambda: frame(''.join(
        f'<g transform="translate({x} {y}) rotate({r})">'
        f'<circle r="150" fill="{CREAM}" {SW}/>'
        + orange(f'<rect x="-42" y="-130" width="84" height="260" rx="38" fill="FILL" {SW}/>')
        + f'<circle cy="-92" r="13" fill="{CREAM}"/></g>'
        for x, y, r in ((360, 560, -30), (650, 430, 25)))),

    'suportes': lambda: frame(''.join(
        f'<g transform="translate({x} {y})">'
        + (orange(f'<path d="M0 0 H60 V150 H190 V210 H0 Z" fill="FILL" {SW}/>') if i % 2 == 0
           else f'<path d="M0 0 H60 V150 H190 V210 H0 Z" fill="{CREAM}" {SW}/>')
        + f'<circle cx="30" cy="45" r="11" fill="{INK}"/></g>'
        for i, (x, y) in enumerate(((250, 230), (540, 230), (250, 520), (540, 520))))),

    'clip': lambda: frame(
        orange(f'<path d="M360 300 H640 A70 70 0 0 1 710 370 V640 A70 70 0 0 1 640 710 H560 V620 H620 V390 H380 V620 H440 V710 H360 A70 70 0 0 1 290 640 V370 A70 70 0 0 1 360 300 Z" fill="FILL" {SW}/>')
        + f'<rect x="440" y="460" width="120" height="70" rx="20" fill="{CREAM}" {SW}/>'
        + f'<circle cx="500" cy="345" r="14" fill="{INK}"/>'),

    'engrenagem': lambda: frame(
        orange(f'<path d="{gear(430, 520, 250, 210, 24)}" fill="FILL" {SW}/>')
        + f'<circle cx="430" cy="520" r="95" fill="{CREAM}" {SW}/><circle cx="430" cy="520" r="32" fill="{INK}"/>'
        + f'<path d="{gear(735, 300, 125, 98, 12, 7)}" fill="{CREAM}" {SW}/>'
        + f'<circle cx="735" cy="300" r="30" fill="{INK}"/>'),

    'cabos': lambda: frame(
        f'<path d="M150 380 C320 300 420 470 560 400 S800 330 860 420" fill="none" stroke="{INK}" stroke-width="26" stroke-linecap="round"/>'
        f'<path d="M150 560 C330 640 450 500 590 580 S780 660 860 580" fill="none" stroke="#8C949E" stroke-width="26" stroke-linecap="round"/>'
        + ''.join(f'<g transform="translate({x} {y}) rotate({r})">'
                  + orange(f'<rect x="-38" y="-70" width="76" height="140" rx="26" fill="FILL" {SW}/>')
                  + f'<rect x="-14" y="-24" width="28" height="48" rx="10" fill="{CREAM}"/></g>'
                  for x, y, r in ((330, 375, 12), (585, 395, -8), (380, 590, -10), (650, 600, 8)))),

    'ferramentas': lambda: frame(
        orange(f'<rect x="170" y="250" width="660" height="80" rx="24" fill="FILL" {SW}/>')
        + ''.join(f'<path d="M{x} 330 V420 Q{x} 455 {x + 35} 455" fill="none" stroke="{INK}" stroke-width="20" stroke-linecap="round"/>'
                  for x in (250, 380, 510, 640, 760))
        + f'<rect x="352" y="440" width="56" height="150" rx="20" fill="{CREAM}" {SW}/>'
          f'<path d="M380 590 V760" stroke="{INK}" stroke-width="18" stroke-linecap="round"/>'
          f'<rect x="612" y="440" width="56" height="150" rx="20" fill="{CREAM}" {SW}/>'
          f'<path d="M640 590 V730 M620 730 H660" stroke="{INK}" stroke-width="18" stroke-linecap="round"/>'),

    'vaso': lambda: frame(
        '<defs><clipPath id="v"><path d="M410 230 H590 C590 300 560 330 560 380 C560 440 720 480 720 620 C720 730 630 790 500 790 C370 790 280 730 280 620 C280 480 440 440 440 380 C440 330 410 300 410 230 Z"/></clipPath></defs>'
        + orange(f'<path d="M410 230 H590 C590 300 560 330 560 380 C560 440 720 480 720 620 C720 730 630 790 500 790 C370 790 280 730 280 620 C280 480 440 440 440 380 C440 330 410 300 410 230 Z" fill="FILL" {SW}/>')
        + '<g clip-path="url(#v)">' + ''.join(
            f'<path d="M{x} {y} l{a} {b} l{c} {e} l{f} {g} l{h} {k} Z" fill="{CREAM}" stroke="{INK}" stroke-width="8" stroke-linejoin="round"/>'
            for x, y, a, b, c, e, f, g, h, k in (
                (330, 560, 60, -40, 60, 30, -10, 70, -80, 20), (470, 520, 70, -20, 40, 60, -60, 50, -40, -40),
                (590, 560, 70, 10, 20, 80, -70, 20, -30, -60), (360, 680, 70, -30, 50, 60, -60, 50, -50, -30),
                (500, 650, 80, -10, 20, 70, -80, 40, -20, -50), (620, 680, 60, 0, 0, 70, -70, 10, 10, -40),
                (470, 400, 40, -20, 30, 40, -40, 30, -30, -20))) + '</g>'
        + f'<path d="M470 230 C450 160 400 130 360 120 C390 170 420 200 470 230 Z" fill="{G}" {SW}/>'
          f'<path d="M530 230 C560 150 620 120 670 120 C640 180 590 210 530 230 Z" fill="{G}" {SW}/>', glow='#FFD08A'),

    'candeeiro': lambda: frame(
        '<circle cx="500" cy="380" r="260" fill="#FFD27A" opacity=".35"/>'
        + f'<rect x="330" y="740" width="340" height="60" rx="26" fill="{CREAM}" {SW}/>'
          f'<path d="M500 740 V560" stroke="{INK}" stroke-width="18" stroke-linecap="round"/>'
        + ''.join(f'<rect x="{360 + i * 6}" y="{230 + i * 52}" width="{280 - i * 12}" height="40" rx="20" '
                  f'transform="rotate({-6 if i % 2 else 6} 500 {250 + i * 52})" '
                  f'fill="{"url(#og)" if i % 2 == 0 else CREAM}" {SW}/>' for i in range(6)),
        glow='#FFC75A'),

    'telemovel': lambda: frame(
        orange(f'<path d="M270 760 H730 L730 700 L560 700 L470 380 L405 400 L490 700 H270 Z" fill="FILL" {SW}/>')
        + f'<g transform="rotate(-16 520 470)"><rect x="410" y="200" width="230" height="440" rx="40" fill="{INK}"/>'
          f'<rect x="428" y="232" width="194" height="376" rx="24" fill="{CREAM}"/>'
          f'<rect x="458" y="282" width="134" height="90" rx="14" fill="{O}" opacity=".85"/>'
          f'<rect x="458" y="392" width="134" height="18" rx="9" fill="{LINE}"/><rect x="458" y="424" width="96" height="18" rx="9" fill="{LINE}"/></g>'),

    'auscultadores': lambda: frame(
        f'<rect x="330" y="740" width="340" height="60" rx="26" fill="{CREAM}" {SW}/>'
        + orange(f'<path d="M470 740 V330 Q470 270 500 270 Q530 270 530 330 V740 Z" fill="FILL" {SW}/>')
        + f'<path d="M300 520 V420 A200 200 0 0 1 700 420 V520" fill="none" stroke="{INK}" stroke-width="34" stroke-linecap="round"/>'
          f'<rect x="250" y="480" width="110" height="170" rx="44" fill="{CREAM}" {SW}/><rect x="285" y="515" width="40" height="100" rx="18" fill="{O}"/>'
          f'<rect x="640" y="480" width="110" height="170" rx="44" fill="{CREAM}" {SW}/><rect x="675" y="515" width="40" height="100" rx="18" fill="{O}"/>'),

    'farol': lambda: frame(
        '<path d="M500 250 L900 160 L900 300 Z" fill="#FFD27A" opacity=".55"/><path d="M500 250 L100 160 L100 300 Z" fill="#FFD27A" opacity=".55"/>'
        + f'<path d="M300 800 Q330 720 420 730 Q470 690 540 720 Q640 700 700 800 Z" fill="#B9B2A7" {SW}/>'
        + '<defs><clipPath id="t"><path d="M430 340 H570 L620 760 H380 Z"/></clipPath></defs>'
        + f'<path d="M430 340 H570 L620 760 H380 Z" fill="{CREAM}"/>'
        + '<g clip-path="url(#t)">' + ''.join(f'<rect x="350" y="{380 + i * 120}" width="300" height="60" fill="url(#og)"/>' for i in range(4)) + '</g>'
        + f'<path d="M430 340 H570 L620 760 H380 Z" fill="none" {SW}/>'
          f'<rect x="440" y="220" width="120" height="120" rx="14" fill="#FFD27A" {SW}/>'
          f'<path d="M425 220 L500 150 L575 220 Z" fill="{INK}" {SW}/>'
          f'<rect x="410" y="330" width="180" height="26" rx="10" fill="{INK}"/>'
          f'<rect x="478" y="640" width="44" height="80" rx="18" fill="{INK}"/>', glow='#FFC75A'),
}


def main():
    if not shutil.which('rsvg-convert'):
        sys.exit('Falta o rsvg-convert (pacote librsvg).')
    names = sys.argv[1:] or [p['image'] for p in json.loads((OUT / 'catalog.json').read_text())]
    with tempfile.TemporaryDirectory() as tmp:
        for name in names:
            if name not in ART:
                sys.exit(f'sem desenho para "{name}"')
            svg, png = Path(tmp) / f'{name}.svg', Path(tmp) / f'{name}.png'
            svg.write_text(ART[name]())
            subprocess.run(['rsvg-convert', '-w', '1000', '-h', '1000', '-o', str(png), str(svg)], check=True)
            out = OUT / f'{name}.jpg'
            Image.open(png).convert('RGB').save(out, 'JPEG', quality=88, optimize=True, progressive=True)
            print(f'{out.relative_to(ROOT)}  {out.stat().st_size // 1024} KB')


if __name__ == '__main__':
    main()
