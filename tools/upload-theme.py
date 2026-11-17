#!/usr/bin/env python3
"""
Carrega dist/revivo-theme.zip no site real com sessão de admin do WordPress.

O WordPress não substitui um tema já instalado na pasta (overwrite_package=false),
por isso, se o tema existir, apaga-o primeiro (só é possível se estiver inativo)
e volta a instalar. NÃO ativa o tema.

Credenciais (no .env, ignorado pelo git):
  WP_LIVE_USER / WP_LIVE_ADMIN_PASSWORD      (login do wp-admin)
  WP_LIVE_API / WP_LIVE_USER / WP_LIVE_PASSWORD  (application password, para verificar)

Uso:
  python3 -I tools/upload-theme.py --dry-run   # testa login/nonce e o estado do tema
  python3 -I tools/upload-theme.py             # instala/atualiza (fica inativo)
  python3 -I tools/upload-theme.py --no-replace  # aborta se o tema já existir
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
from html import unescape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ZIP = ROOT / 'dist' / 'revivo-theme.zip'
SLUG = 'revivo'


def env():
    d = {}
    for line in (ROOT / '.env').read_text().splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            d[k.strip()] = v.strip()
    return d


def local_version():
    m = re.search(r'^Version:\s*(\S+)', (ROOT / 'theme' / SLUG / 'style.css').read_text(), re.M)
    return m.group(1) if m else '?'


class Admin:
    def __init__(self, base, context):
        self.base = base
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.jar),
            urllib.request.HTTPSHandler(context=context))
        self.opener.addheaders = [('User-Agent', 'Mozilla/5.0 (Macintosh) revivo-deploy')]

    def get(self, url):
        with self.opener.open(url, timeout=120) as r:
            return r.status, r.read().decode('utf-8', 'replace'), r.geturl()

    def post_form(self, url, data):
        req = urllib.request.Request(url, data=urllib.parse.urlencode(data).encode(), method='POST')
        req.add_header('Content-Type', 'application/x-www-form-urlencoded')
        with self.opener.open(req, timeout=180) as r:
            return r.status, r.read().decode('utf-8', 'replace')

    def post_multipart(self, url, fields, field, filename, content, ctype='application/zip'):
        b = '----revivo' + uuid.uuid4().hex
        body = b''
        for k, v in fields.items():
            body += f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
        body += (f'--{b}\r\nContent-Disposition: form-data; name="{field}"; filename="{filename}"\r\n'
                 f'Content-Type: {ctype}\r\n\r\n').encode() + content + b'\r\n'
        body += f'--{b}--\r\n'.encode()
        req = urllib.request.Request(url, data=body, method='POST')
        req.add_header('Content-Type', f'multipart/form-data; boundary={b}')
        try:
            with self.opener.open(req, timeout=600) as r:
                return r.status, r.read().decode('utf-8', 'replace')
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode('utf-8', 'replace')

    def logged_in(self):
        return any(c.name.startswith('wordpress_logged_in') for c in self.jar)


def rest_get(api, context, token, path):
    req = urllib.request.Request(api + path)
    req.add_header('Authorization', token)
    try:
        with urllib.request.urlopen(req, timeout=60, context=context) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, None


def theme_status(api, context, token):
    """Devolve (existe, está_ativo, versão, todas_as_inativas)."""
    s, active = rest_get(api, context, token, '/wp/v2/themes?status=active')
    active_slug = active[0]['stylesheet'] if s == 200 and active else None
    s, inactive = rest_get(api, context, token, '/wp/v2/themes?status=inactive')
    found = None
    for t in (inactive or []):
        if t['stylesheet'] == SLUG:
            found = t
    return found, (active_slug == SLUG), (active_slug or '')


def main():
    E = env()
    if not E.get('WP_LIVE_ADMIN_PASSWORD'):
        sys.exit('Falta WP_LIVE_ADMIN_PASSWORD no .env.')
    if not ZIP.exists():
        sys.exit(f'Falta o zip ({ZIP.relative_to(ROOT)}) — corre python3 -I tools/build-theme.py')

    API = E['WP_LIVE_API'].rstrip('/')
    BASE = API.split('/index.php/wp-json')[0].split('/wp-json')[0].rstrip('/')
    ctx = ssl.create_default_context()
    ctx.load_verify_locations(str(ROOT / 'config' / 'harica-geant-tls-r1.pem'))
    token = 'Basic ' + base64.b64encode(
        f"{E['WP_LIVE_USER']}:{E['WP_LIVE_PASSWORD']}".encode()).decode()

    want = local_version()
    dry = '--dry-run' in sys.argv
    replace = '--no-replace' not in sys.argv

    print(f'site: {BASE}')
    found, is_active, active_slug = theme_status(API, ctx, token)
    print(f'tema ativo: {active_slug}')
    if is_active:
        sys.exit('O tema revivo está ATIVO. Não apago um tema ativo; desativa-o primeiro.')
    print(f'revivo instalado: {"sim, versão " + found.get("version", "?") if found else "não"} | queremos: {want}')

    a = Admin(BASE, ctx)
    a.get(f'{BASE}/wp-login.php')
    s, body = a.post_form(f'{BASE}/wp-login.php', {
        'log': E['WP_LIVE_USER'], 'pwd': E['WP_LIVE_ADMIN_PASSWORD'],
        'wp-submit': 'Log In', 'redirect_to': f'{BASE}/wp-admin/', 'testcookie': '1'})
    if not a.logged_in():
        m = re.search(r'id="login_error"[^>]*>(.*?)</div>', body, re.S)
        msg = re.sub(r'<[^>]+>', '', m.group(1)) if m else '(sem mensagem)'
        sys.exit(f'login falhou: {re.sub(r"\s+", " ", msg).strip()}')
    print('login: OK')

    # nãoce do formulário de upload
    s, page, _ = a.get(f'{BASE}/wp-admin/theme-install.php?browse=upload')
    m = re.search(r'name="_wpnonce"[^>]*value="([^"]+)"', page) or \
        re.search(r'value="([^"]+)"[^>]*name="_wpnonce"', page)
    if not m:
        sys.exit(f'sem nonce de upload (HTTP {s}) — pode faltar acesso de escrita a ficheiros')
    nonce = m.group(1)

    if dry:
        print(f'dry-run: autenticado, nonce ok, tema {"a substituir" if found else "novo"}; nada alterado')
        return

    # apagar versão antiga (não há overwrite na instalação de temas)
    if found:
        if not replace:
            sys.exit(f'revivo {found.get("version")} já existe e --no-replace foi pedido.')
        s, page, _ = a.get(f'{BASE}/wp-admin/themes.php')
        # O link de apagar não está em href="...": só existe no JSON embutido da lista de temas
        # (ex.: "delete":"https://.../themes.php?action=delete&amp;stylesheet=revivo&amp;_wpnonce=...").
        hits = re.findall(r'"delete":"([^"]*action=delete[^"]*)"', page)
        target = next((h for h in hits if 'stylesheet=' + SLUG + '&' in unescape(h)), None)
        if not target:
            sys.exit('não encontrei o URL de apagar o tema em themes.php (não apaguei nada)')
        url = unescape(target).replace('&#038;', '&')
        if not url.startswith('http'):
            url = f'{BASE}/wp-admin/{url.lstrip("/")}'
        s, page, final = a.get(url)
        gone, still_active, act = theme_status(API, ctx, token)
        if gone:
            sys.exit('depois de apagar, o tema ainda aparece instalado — parar')
        print(f'tema antigo apagado (HTTP {s})')
        # nonce muda depois de mexer em temas? obter de novo por segurança
        s, page, _ = a.get(f'{BASE}/wp-admin/theme-install.php?browse=upload')
        m = re.search(r'name="_wpnonce"[^>]*value="([^"]+)"', page) or \
            re.search(r'value="([^"]+)"[^>]*name="_wpnonce"', page)
        nonce = m.group(1) if m else nonce

    # upload
    s, text = a.post_multipart(
        f'{BASE}/wp-admin/update.php?action=upload-theme', {'_wpnonce': nonce},
        'themezip', ZIP.name, ZIP.read_bytes())
    plain = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', text)).strip()
    print(f'upload: HTTP {s} — {plain[:180]}')

    # verificação independente (REST)
    found, is_active, active_slug = theme_status(API, ctx, token)
    if not found:
        sys.exit('o tema não aparece instalado depois do upload — ver wp-admin → Aparência → Temas')
    ok = found.get('version') == want
    print(f"\nverificado: revivo {found.get('version')} instalado, INATIVO"
          f"{' — atualizado' if ok else ' — ATENÇÃO: versão não é a esperada ' + want}")
    print(f'site continua com: {active_slug}')


if __name__ == '__main__':
    main()
