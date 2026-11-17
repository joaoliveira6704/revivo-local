#!/usr/bin/env python3
"""
Empacota o tema Revivo (theme/revivo) num zip instalável no site real.

  python3 -I tools/build-theme.py                    # dist/revivo-theme.zip
  python3 -I tools/build-theme.py --bump patch       # sobe a versão e empacota
  python3 -I tools/build-theme.py --set-version 1.2.0
  python3 -I tools/build-theme.py --keep-local-urls  # para testar noutro local

No pacote, os URLs locais (http://localhost:8080) passam a ser os do site real,
tal como o push.py faz com páginas e templates. O site real NÃO é alterado:
o zip é instalado (inativo) em WP-Admin → Aparência → Temas → Adicionar → Carregar.
"""
import argparse
import json
import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'theme' / 'revivo'
DIST = ROOT / 'dist'
TEXT_EXT = {'.html', '.css', '.js', '.php', '.json', '.svg', '.txt', '.md'}


def load_env():
    env = {}
    p = ROOT / '.env'
    if not p.exists():
        return env
    for line in p.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            env[k.strip()] = v.strip()
    return env


def live_url(env):
    api = env.get('WP_LIVE_API', '').rstrip('/')
    if not api:
        sys.exit('WP_LIVE_API em falta no .env')
    return api.split('/index.php/wp-json')[0].split('/wp-json')[0]


def version():
    m = re.search(r'^Version:\s*(\S+)', (SRC / 'style.css').read_text(), re.M)
    return m.group(1) if m else '0.0.0'


def set_version(new):
    p = SRC / 'style.css'
    css = p.read_text()
    css = re.sub(r'^Version:\s*\S+', f'Version: {new}', css, count=1, flags=re.M)
    p.write_text(css)


def bump(kind):
    major, minor, patch = (int(x) for x in version().split('.'))
    if kind == 'major':
        major, minor, patch = major + 1, 0, 0
    elif kind == 'minor':
        minor, patch = minor + 1, 0
    else:
        patch += 1
    return f'{major}.{minor}.{patch}'


def rewrite(text, local, live):
    """Substitui URLs locais pelos do site real, incluindo a forma escapada em JSON."""
    n = 0
    for a, b in ((local, live), (local.replace('/', '\\/'), live.replace('/', '\\/'))):
        n += text.count(a)
        text = text.replace(a, b)
    return text, n


def main():
    ap = argparse.ArgumentParser(description='Empacota o tema Revivo para instalar no site real.')
    ap.add_argument('--set-version')
    ap.add_argument('--bump', choices=('major', 'minor', 'patch'))
    ap.add_argument('--keep-local-urls', action='store_true')
    ap.add_argument('--out', default=None, help='caminho do zip (por omissão dist/revivo-theme.zip)')
    args = ap.parse_args()

    if not SRC.is_dir():
        sys.exit(f'não encontrei o tema em {SRC}')
    if args.set_version:
        set_version(args.set_version)
    elif args.bump:
        set_version(bump(args.bump))

    env = load_env()
    local = env.get('WP_LOCAL_URL', 'http://localhost:8080').rstrip('/')
    live = live_url(env)
    out = Path(args.out) if args.out else DIST / 'revivo-theme.zip'
    out.parent.mkdir(parents=True, exist_ok=True)

    ver = version()
    files = 0
    replacements = 0
    with tempfile.TemporaryDirectory() as tmp:
        stage = Path(tmp) / 'revivo'
        shutil.copytree(SRC, stage, ignore=shutil.ignore_patterns('.DS_Store', '__pycache__', '*.pyc'))

        if not args.keep_local_urls:
            for f in stage.rglob('*'):
                if f.is_file() and f.suffix in TEXT_EXT:
                    t = f.read_text()
                    new, n = rewrite(t, local, live)
                    if n:
                        f.write_text(new)
                        replacements += n

        with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
            for f in sorted(stage.rglob('*')):
                if f.is_file():
                    z.write(f, Path('revivo') / f.relative_to(stage))
                    files += 1

    size = out.stat().st_size / 1024
    print(f'tema:      revivo {ver}')
    print(f'ficheiros: {files}')
    if args.keep_local_urls:
        print('URLs:      locais (não reescritos)')
    else:
        print(f'URLs:      {replacements} substituições {local} → {live}')
    print(f'zip:       {out.relative_to(ROOT)} ({size:.0f} KB)')
    print('\nInstalar no site real: WP-Admin → Aparência → Temas → Adicionar → Carregar tema.')
    print('O tema fica INATIVO até o ativares; o site continua igual.')


if __name__ == '__main__':
    main()
