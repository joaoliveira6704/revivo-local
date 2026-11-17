#!/usr/bin/env python3
"""
Instala ou atualiza o tema ou o plugin no site real, a partir dos zips em dist/.

Usa o mesmo caminho que o WP-Admin: carrega o zip e, se já existir, escolhe
"Substituir a atual pela carregada" (overwrite). Funciona com o tema ativo —
nesse caso a nova versão fica visível logo. O plugin é ativado pela REST API
(--no-activate para o deixar inativo).

Credenciais (no .env, ignorado pelo git):
  WP_LIVE_USER / WP_LIVE_ADMIN_PASSWORD          (login do wp-admin, para o upload)
  WP_LIVE_API / WP_LIVE_USER / WP_LIVE_PASSWORD  (application password, para verificar/ativar)

Uso:
  python3 -I tools/upload.py theme --dry-run    # testa login/nonce e mostra o estado
  python3 -I tools/upload.py theme              # instala/substitui dist/revivo-theme.zip
  python3 -I tools/upload.py plugin             # instala/substitui e ativa dist/revivo-pedidos.zip
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

KINDS = {
    'theme': {
        'zip': ROOT / 'dist' / 'revivo-theme.zip',
        'source': ROOT / 'theme' / 'revivo' / 'style.css',
        'slug': 'revivo',
        'form': '/wp-admin/theme-install.php?browse=upload',
        'action': 'upload-theme', 'field': 'themezip',
    },
    'plugin': {
        'zip': ROOT / 'dist' / 'revivo-pedidos.zip',
        'source': ROOT / 'plugins' / 'revivo-pedidos' / 'revivo-pedidos.php',
        'slug': 'revivo-pedidos/revivo-pedidos',
        'form': '/wp-admin/plugin-install.php?tab=upload',
        'action': 'upload-plugin', 'field': 'pluginzip',
    },
}


def env():
    d = {}
    for line in (ROOT / '.env').read_text().splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            d[k.strip()] = v.strip()
    return d


def local_version(path):
    m = re.search(r'^\s*\*?\s*Version:\s*(\S+)', path.read_text(), re.M)
    return m.group(1) if m else '?'


def plain(html):
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', html)).strip()


class Admin:
    def __init__(self, context):
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.jar),
            urllib.request.HTTPSHandler(context=context))
        self.opener.addheaders = [('User-Agent', 'Mozilla/5.0 revivo-deploy')]

    def get(self, url):
        with self.opener.open(url, timeout=180) as r:
            return r.status, r.read().decode('utf-8', 'replace')

    def post_form(self, url, data):
        req = urllib.request.Request(url, data=urllib.parse.urlencode(data).encode(), method='POST')
        req.add_header('Content-Type', 'application/x-www-form-urlencoded')
        with self.opener.open(req, timeout=180) as r:
            return r.status, r.read().decode('utf-8', 'replace')

    def post_multipart(self, url, fields, field, filename, content):
        b = '----revivo' + uuid.uuid4().hex
        body = b''
        for k, v in fields.items():
            body += f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
        body += (f'--{b}\r\nContent-Disposition: form-data; name="{field}"; filename="{filename}"\r\n'
                 'Content-Type: application/zip\r\n\r\n').encode() + content + b'\r\n'
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


class Rest:
    def __init__(self, api, context, user, password):
        self.api, self.context = api, context
        self.token = 'Basic ' + base64.b64encode(f'{user}:{password}'.encode()).decode()

    def call(self, path, data=None):
        req = urllib.request.Request(self.api + path, method='POST' if data else 'GET',
                                     data=json.dumps(data).encode() if data else None)
        req.add_header('Authorization', self.token)
        if data:
            req.add_header('Content-Type', 'application/json')
        try:
            with urllib.request.urlopen(req, timeout=60, context=self.context) as r:
                return r.status, json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            return e.code, None


def status(rest, kind, slug):
    """Devolve (versão instalada ou None, ativo?, descrição do que está ativo)."""
    if kind == 'theme':
        _, active = rest.call('/wp/v2/themes?status=active')
        active_slug = active[0]['stylesheet'] if active else '?'
        if active_slug == slug:
            return active[0].get('version'), True, active_slug
        _, inactive = rest.call('/wp/v2/themes?status=inactive')
        t = next((t for t in inactive or [] if t['stylesheet'] == slug), None)
        return (t.get('version') if t else None), False, active_slug
    s, p = rest.call('/wp/v2/plugins/' + slug)
    if s != 200 or not p:
        return None, False, ''
    return p.get('version'), p.get('status') == 'active', p.get('status')


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if len(args) != 1 or args[0] not in KINDS:
        sys.exit('uso: python3 -I tools/upload.py {theme|plugin} [--dry-run] [--no-activate]')
    kind = args[0]
    K = KINDS[kind]
    dry = '--dry-run' in sys.argv

    E = env()
    if not E.get('WP_LIVE_ADMIN_PASSWORD'):
        sys.exit('Falta WP_LIVE_ADMIN_PASSWORD no .env (senha de login do wp-admin).')
    if not K['zip'].exists():
        sys.exit(f"Falta {K['zip'].relative_to(ROOT)}")

    api = E['WP_LIVE_API'].rstrip('/')
    base = api.split('/index.php/wp-json')[0].split('/wp-json')[0].rstrip('/')
    ctx = ssl.create_default_context()
    ctx.load_verify_locations(str(ROOT / 'config' / 'harica-geant-tls-r1.pem'))
    rest = Rest(api, ctx, E['WP_LIVE_USER'], E['WP_LIVE_PASSWORD'])

    want = local_version(K['source'])
    have, active, state = status(rest, kind, K['slug'])
    print(f'site:       {base}')
    print(f'{kind}:     {K["slug"]} — instalado: {have or "não"}'
          f'{" (ATIVO)" if active else ""} | zip: {want}')
    if kind == 'theme' and not active:
        print(f'tema ativo: {state}')

    a = Admin(ctx)
    a.get(f'{base}/wp-login.php')
    a.post_form(f'{base}/wp-login.php', {
        'log': E['WP_LIVE_USER'], 'pwd': E['WP_LIVE_ADMIN_PASSWORD'],
        'wp-submit': 'Log In', 'redirect_to': f'{base}/wp-admin/', 'testcookie': '1'})
    if not a.logged_in():
        sys.exit('login no wp-admin falhou (verifica WP_LIVE_ADMIN_PASSWORD)')
    print('login:      OK')

    s, page = a.get(base + K['form'])
    m = re.search(r'name="_wpnonce"[^>]*value="([^"]+)"', page) or \
        re.search(r'value="([^"]+)"[^>]*name="_wpnonce"', page)
    if not m:
        sys.exit(f'sem nonce de upload (HTTP {s}) — o utilizador pode não ter permissão para instalar')
    if dry:
        print(f'dry-run:    autenticado, nonce ok, {"substituir " + have if have else "instalação nova"}; nada alterado')
        return

    s, page = a.post_multipart(f"{base}/wp-admin/update.php?action={K['action']}",
                               {'_wpnonce': m.group(1)}, K['field'], K['zip'].name, K['zip'].read_bytes())
    # já instalado: o WordPress pede confirmação com um link "overwrite=update-…"
    over = re.search(r'href="([^"]*overwrite=update-(?:theme|plugin)[^"]*)"', page)
    if over:
        url = unescape(over.group(1))
        if not url.startswith('http'):
            url = f'{base}/wp-admin/{url.lstrip("/")}'
        s, page = a.get(url)
        print(f'substituir: HTTP {s}')
    else:
        print(f'upload:     HTTP {s}')
    msg = plain(page)
    # só o relatório da instalação: o topo do wp-admin pode ter avisos que não têm a ver (ex.: atualização do WordPress)
    start = max(msg.find('A instalar'), msg.find('Installing'))
    msg = msg[start:] if start >= 0 else msg
    # a página traz traduções de JS com "falhou"/"failed": em vez de procurar erros, confirma a mensagem de sucesso
    if not re.search(r'com sucesso|successfully', msg):
        print('aviso: o WordPress não confirmou a instalação —', msg[:300])

    if kind == 'plugin' and '--no-activate' not in sys.argv:
        s, p = rest.call('/wp/v2/plugins/' + K['slug'], {'status': 'active'})
        print(f'ativar:     HTTP {s} — {p.get("status") if p else "?"}')

    have, active, state = status(rest, kind, K['slug'])
    if not have:
        sys.exit(f'{kind} não aparece instalado depois do upload — ver o WP-Admin')
    print(f'\nverificado: {K["slug"]} {have} {"ATIVO" if active else "inativo"}'
          f'{"" if have == want else " — ATENÇÃO: esperava " + want}')


if __name__ == '__main__':
    main()
