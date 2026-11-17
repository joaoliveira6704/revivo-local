#!/usr/bin/env python3
"""
Carrega dist/revivo-theme.zip no site real com sessão de admin do WordPress.

NÃO ativa o tema: fica instalado e inativo.

Credenciais (no .env, que está no .gitignore):
  WP_LIVE_USER=<utilizador admin>
  WP_LIVE_ADMIN_PASSWORD=<password de login do wp-admin>
  WP_LIVE_API / WP_LIVE_USER / WP_LIVE_PASSWORD  (application password, para verificar)

Uso:
  python3 -I tools/upload-theme.py --dry-run   # só testa o login e o nonce
  python3 -I tools/upload-theme.py             # carrega o zip
"""
import base64
import http.cookiejar
import json
import re
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ZIP = ROOT / 'dist' / 'revivo-theme.zip'


def env():
    d = {}
    for line in (ROOT / '.env').read_text().splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            d[k.strip()] = v.strip()
    return d


def main():
    E = env()
    if not E.get('WP_LIVE_ADMIN_PASSWORD'):
        sys.exit('Falta WP_LIVE_ADMIN_PASSWORD no .env (password de login do wp-admin).')
    if not ZIP.exists():
        sys.exit(f'Falta o zip: {ZIP.relative_to(ROOT)} — corre python3 -I tools/build-theme.py')

    API = E['WP_LIVE_API'].rstrip('/')
    BASE = API.split('/index.php/wp-json')[0].split('/wp-json')[0].rstrip('/')

    ctx = ssl.create_default_context()
    ctx.load_verify_locations(str(ROOT / 'config' / 'harica-geant-tls-r1.pem'))
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(jar), urllib.request.HTTPSHandler(context=ctx))
    opener.addheaders = [('User-Agent', 'Mozilla/5.0 (Macintosh) revivo-deploy')]

    def get(url):
        with opener.open(url, timeout=60) as r:
            return r.status, r.read().decode('utf-8', 'replace')

    def post_form(url, data):
        req = urllib.request.Request(url, data=urllib.parse.urlencode(data).encode(), method='POST')
        req.add_header('Content-Type', 'application/x-www-form-urlencoded')
        with opener.open(req, timeout=120) as r:
            return r.status, r.read().decode('utf-8', 'replace')

    def logged_in():
        return any(c.name.startswith('wordpress_logged_in') for c in jar)

    print(f'site: {BASE}')

    # 1) login
    get(f'{BASE}/wp-login.php')
    s, body = post_form(f'{BASE}/wp-login.php', {
        'log': E['WP_LIVE_USER'], 'pwd': E['WP_LIVE_ADMIN_PASSWORD'],
        'wp-submit': 'Log In', 'redirect_to': f'{BASE}/wp-admin/', 'testcookie': '1',
    })
    if not logged_in():
        m = re.search(r'id="login_error"[^>]*>(.*?)</div>', body, re.S)
        msg = re.sub(r'<[^>]+>', '', m.group(1)).strip() if m else '(sem mensagem)'
        sys.exit(f'login falhou (HTTP {s}): {re.sub(r"\s+", " ", msg)}')
    print('login: OK (sessão de admin)')

    # 2) nonce do formulário "Carregar tema"
    s, page = get(f'{BASE}/wp-admin/theme-install.php?browse=upload')
    m = re.search(r'name="_wpnonce"[^>]*value="([^"]+)"', page) or \
        re.search(r'value="([^"]+)"[^>]*name="_wpnonce"', page)
    if not m:
        sys.exit(f'theme-install.php HTTP {s}: não encontrei o nonce '
                 '(pode ser preciso acesso FTP/SSH para instalar temas)')
    nonce = m.group(1)
    print(f'nonce: {nonce[:6]}…')

    if '--dry-run' in sys.argv:
        print('dry-run: login e nonce OK, não carreguei nada')
        return

    # 3) upload multipart
    def multipart(fields, file_field, filename, content):
        b = '----revivo' + uuid.uuid4().hex
        out = b''
        for k, v in fields.items():
            out += f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
        out += (f'--{b}\r\nContent-Disposition: form-data; name="{file_field}"; filename="{filename}"\r\n'
                f'Content-Type: application/zip\r\n\r\n').encode() + content + b'\r\n'
        out += f'--{b}--\r\n'.encode()
        return b, out

    data = ZIP.read_bytes()
    results = []
    for label, url, field in (
        ('admin-ajax', f'{BASE}/wp-admin/admin-ajax.php?action=upload-theme', 'themezip'),
        ('update.php', f'{BASE}/wp-admin/update.php?action=upload-theme', 'themezip'),
    ):
        b, payload = multipart({'_wpnonce': nonce}, field, ZIP.name, data)
        req = urllib.request.Request(url, data=payload, method='POST')
        req.add_header('Content-Type', f'multipart/form-data; boundary={b}')
        try:
            with opener.open(req, timeout=300) as r:
                status, text = r.status, r.read().decode('utf-8', 'replace')
        except urllib.error.HTTPError as e:
            status, text = e.code, e.read().decode('utf-8', 'replace')
        clean = re.sub(r'<[^>]+>', ' ', text)
        clean = re.sub(r'\s+', ' ', clean).strip()
        print(f'{label}: HTTP {status} — {clean[:300]}')
        results.append((label, status, clean))
        if re.search(r'(instalad|installed|success|atualiz|updated)', clean, re.I):
            break

    # 4) verificar por REST (application password) que ficou instalado e inativo
    token = 'Basic ' + base64.b64encode(
        f"{E['WP_LIVE_USER']}:{E['WP_LIVE_PASSWORD']}".encode()).decode()
    req = urllib.request.Request(f'{API}/wp/v2/themes?status=inactive')
    req.add_header('Authorization', token)
    try:
        with urllib.request.urlopen(req, timeout=60, context=ctx) as r:
            themes = json.loads(r.read().decode())
        found = [t for t in themes if t.get('stylesheet') == 'revivo']
        if found:
            t = found[0]
            print(f"\nverificado: tema 'revivo' instalado e INATIVO "
                  f"(versão {t.get('version')}, stylesheet {t.get('stylesheet')})")
            print('O site continua com o tema atual até o ativares em Aparência → Temas.')
        else:
            print('\nnão encontrei o revivo na lista de temas inativos — vê Aparência → Temas no wp-admin.')
    except Exception as e:
        print(f'\nverificação REST falhou ({e}); confirma manualmente em Aparência → Temas.')


if __name__ == '__main__':
    main()
