#!/usr/bin/env python3
"""Gera as imagens dos produtos de demonstração (SVG → PNG 800×800) no estilo Revivo."""
import subprocess
from pathlib import Path

OUT = Path(__file__).parent / 'img'
OUT.mkdir(exist_ok=True)

BGS = {  # fundo por categoria (claro → escuro)
    'pecas': ('#FFF1E8', '#FBD9C4'), 'deco': ('#F6F1EA', '#E9DFD1'), 'util': ('#EEF3EF', '#D6E6DC'),
    'cole': ('#EFEDF7', '#DCD7EE'), 'tech': ('#EDF1F5', '#D5DEE8'), 'medida': ('#1C1F24', '#0D0F12'),
}

LAYERS = '''<pattern id="L" width="10" height="9" patternUnits="userSpaceOnUse">
<rect width="10" height="9" fill="#F2611D"/><rect y="7" width="10" height="2" fill="#D24F12"/></pattern>
<pattern id="G" width="10" height="9" patternUnits="userSpaceOnUse">
<rect width="10" height="9" fill="#2B3036"/><rect y="7" width="10" height="2" fill="#1A1D21"/></pattern>'''

SHAPES = {
    'gear': '<g transform="translate(400 410)"><circle r="190" fill="none" stroke="url(#L)" stroke-width="70" stroke-dasharray="58 62"/>'
            '<circle r="160" fill="url(#L)"/><circle r="58" fill="{hole}"/></g>',
    'knob': '<g transform="translate(400 410)"><circle r="200" fill="url(#G)"/><circle r="170" fill="url(#L)"/>'
            '<rect x="-18" y="-160" width="36" height="110" rx="18" fill="#fff" opacity=".9"/></g>',
    'handle': '<g transform="translate(400 410)"><rect x="-230" y="-60" width="460" height="120" rx="60" fill="url(#L)"/>'
              '<rect x="-250" y="-110" width="70" height="220" rx="24" fill="url(#G)"/><rect x="180" y="-110" width="70" height="220" rx="24" fill="url(#G)"/></g>',
    'hinge': '<g transform="translate(400 410)"><rect x="-210" y="-150" width="190" height="300" rx="26" fill="url(#L)"/>'
             '<rect x="20" y="-150" width="190" height="300" rx="26" fill="url(#G)"/><rect x="-40" y="-170" width="80" height="340" rx="40" fill="url(#L)"/>'
             '<circle cx="-115" cy="-70" r="22" fill="{hole}"/><circle cx="-115" cy="70" r="22" fill="{hole}"/><circle cx="115" cy="-70" r="22" fill="#5F6670"/><circle cx="115" cy="70" r="22" fill="#5F6670"/></g>',
    'vase': '<g transform="translate(400 420)"><path d="M-90 -230h180l40 70 -40 120 110 120 -60 150h-260l-60 -150 110 -120 -40 -120z" fill="url(#L)"/>'
            '<path d="M-90 -230h180l40 70 -40 120 110 120 -60 150" fill="none" stroke="#fff" stroke-opacity=".35" stroke-width="6"/></g>',
    'lamp': '<g transform="translate(400 420)"><path d="M-200 -40 Q0 -300 200 -40z" fill="url(#L)"/><rect x="-14" y="-40" width="28" height="220" fill="url(#G)"/>'
            '<rect x="-130" y="170" width="260" height="50" rx="25" fill="url(#G)"/><circle cy="-30" r="34" fill="#FFE2A8"/></g>',
    'tray': '<g transform="translate(400 430)"><rect x="-260" y="-60" width="520" height="190" rx="34" fill="url(#L)"/>'
            '<rect x="-230" y="-200" width="150" height="250" rx="24" fill="url(#G)"/><rect x="-60" y="-140" width="130" height="190" rx="24" fill="url(#L)"/>'
            '<rect x="90" y="-230" width="140" height="280" rx="24" fill="url(#G)"/></g>',
    'hook': '<g transform="translate(400 410)"><rect x="-260" y="-200" width="520" height="90" rx="30" fill="url(#G)"/>'
            '<path d="M-150 -110v170a70 70 0 0 0 140 0" fill="none" stroke="url(#L)" stroke-width="56" stroke-linecap="round"/>'
            '<path d="M80 -110v170a70 70 0 0 0 140 0" fill="none" stroke="url(#L)" stroke-width="56" stroke-linecap="round"/></g>',
    'figure': '<g transform="translate(400 430)"><path d="M-170 220 Q-200 40 -60 -20 Q-140 -120 -40 -220 Q60 -280 120 -180 Q200 -60 90 0 Q220 80 170 220z" fill="url(#L)"/>'
              '<circle cx="40" cy="-170" r="16" fill="#1C1F23"/><rect x="-220" y="210" width="440" height="50" rx="25" fill="url(#G)"/></g>',
    'tower': '<g transform="translate(400 430)"><path d="M-70 -230h140l50 420h-240z" fill="url(#L)"/><rect x="-90" y="-280" width="180" height="70" rx="16" fill="url(#G)"/>'
             '<rect x="-40" y="-120" width="80" height="40" rx="10" fill="#fff" opacity=".9"/><rect x="-200" y="190" width="400" height="60" rx="28" fill="url(#G)"/></g>',
    'stand': '<g transform="translate(400 430)"><path d="M-200 200 L40 -200 L120 -200 L-90 200z" fill="url(#L)"/><rect x="-240" y="180" width="480" height="70" rx="30" fill="url(#G)"/>'
             '<rect x="40" y="-260" width="150" height="300" rx="26" fill="#2B3036" transform="rotate(28 115 -110)"/></g>',
    'clip': '<g transform="translate(400 420)">' + ''.join(
        f'<g transform="translate({x} {y})"><circle r="70" fill="url(#L)"/><circle r="30" fill="{{hole}}"/><rect x="-14" y="-90" width="28" height="60" fill="{{hole}}"/></g>'
        for x, y in ((-170, -100), (0, -100), (170, -100), (-170, 110), (0, 110), (170, 110))) + '</g>',
    'cube': '<g transform="translate(400 420)"><path d="M0 -230 200 -115 0 0 -200 -115z" fill="#FF9A62"/><path d="M-200 -115 0 0v230l-200 -115z" fill="url(#L)"/>'
            '<path d="M200 -115 0 0v230l200 -115z" fill="#C94B10"/><path d="M0 -230 200 -115 0 0 -200 -115z" fill="none" stroke="#fff" stroke-opacity=".5" stroke-width="4"/></g>',
}


def svg(bg, shape):
    a, b = BGS[bg]
    hole = b
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="800" height="800" viewBox="0 0 800 800">
<defs>{LAYERS}<radialGradient id="bg" cx="35%" cy="25%" r="90%"><stop offset="0" stop-color="{a}"/><stop offset="1" stop-color="{b}"/></radialGradient>
<filter id="s" x="-20%" y="-20%" width="140%" height="150%"><feDropShadow dx="0" dy="30" stdDeviation="28" flood-color="#000" flood-opacity=".22"/></filter></defs>
<rect width="800" height="800" fill="url(#bg)"/>
<ellipse cx="400" cy="690" rx="250" ry="34" fill="#000" opacity=".08"/>
<g filter="url(#s)">{SHAPES[shape].replace('{hole}', hole)}</g></svg>'''


PRODUCTS = {  # ficheiro: (fundo, forma)
    'botao-maquina': ('pecas', 'knob'), 'puxador-frigorifico': ('pecas', 'handle'), 'engrenagem-batedeira': ('pecas', 'gear'),
    'dobradica-microondas': ('pecas', 'hinge'), 'vaso-facetas': ('deco', 'vase'), 'candeeiro-onda': ('deco', 'lamp'),
    'organizador-secretaria': ('util', 'tray'), 'suporte-ferramentas': ('util', 'hook'), 'dragao-articulado': ('cole', 'figure'),
    'miniatura-farol': ('cole', 'tower'), 'suporte-telemovel': ('tech', 'stand'), 'organizador-cabos': ('tech', 'clip'),
    'impressao-medida': ('medida', 'cube'), 'roda-prato': ('pecas', 'gear'),
}

SWIFT = r'''
import AppKit
let a = CommandLine.arguments
for i in stride(from: 1, to: a.count, by: 2) {
  guard let img = NSImage(contentsOfFile: a[i]) else { print("falhou: \(a[i])"); continue }
  let n = 800
  let rep = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: n, pixelsHigh: n, bitsPerSample: 8, samplesPerPixel: 4, hasAlpha: true, isPlanar: false, colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0)!
  NSGraphicsContext.saveGraphicsState(); NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: rep)
  img.draw(in: NSRect(x: 0, y: 0, width: n, height: n)); NSGraphicsContext.restoreGraphicsState()
  try! rep.representation(using: .png, properties: [:])!.write(to: URL(fileURLWithPath: a[i + 1]))
}
'''

if __name__ == '__main__':
    args = []
    for name, (bg, shape) in PRODUCTS.items():
        s = OUT / f'{name}.svg'
        s.write_text(svg(bg, shape))
        args += [str(s), str(OUT / f'{name}.png')]
    (OUT / 'render.swift').write_text(SWIFT)
    subprocess.run(['swift', str(OUT / 'render.swift'), *args], check=True)
    print(len(PRODUCTS), 'imagens em', OUT)
