#!/usr/bin/env python3
"""
Cria os produtos de demonstração (design/products/catalog.json) pela REST API do WooCommerce.

- Usa a mesma API no site local e no real; os produtos que já existem (mesmo SKU) são ignorados,
  por isso pode correr-se mais de uma vez.
- Cria o atributo global "Material" (PLA, PETG, Resina) se faltar.
- Carrega a imagem de cada produto (design/products/<imagem>.jpg; gerar com tools/product-images.py).
- Nos textos, {site} é trocado pelo endereço do site.

Credenciais (no .env, ignorado pelo git): application passwords
  local: WP_LOCAL_API / WP_LOCAL_USER / WP_LOCAL_PASSWORD
  real:  WP_LIVE_API  / WP_LIVE_USER  / WP_LIVE_PASSWORD

Uso:
  python3 -I tools/seed-products.py local --dry-run
  python3 -I tools/seed-products.py local
  python3 -I tools/seed-products.py live
"""
import base64
import json
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIR = ROOT / 'design' / 'products'
MATERIALS = ['PLA', 'PETG', 'Resina']


def env():
    d = {}
    for line in (ROOT / '.env').read_text().splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            d[k.strip()] = v.strip()
    return d


class Api:
    def __init__(self, base, user, password, context):
        self.base, self.context = base.rstrip('/'), context
        self.auth = 'Basic ' + base64.b64encode(f'{user}:{password}'.encode()).decode()

    def call(self, method, path, data=None, raw=None, headers=None):
        body = raw if raw is not None else (json.dumps(data).encode() if data is not None else None)
        req = urllib.request.Request(self.base + path, data=body, method=method)
        req.add_header('Authorization', self.auth)
        if raw is None and data is not None:
            req.add_header('Content-Type', 'application/json')
        for k, v in (headers or {}).items():
            req.add_header(k, v)
        try:
            with urllib.request.urlopen(req, timeout=120, context=self.context) as r:
                return json.loads(r.read().decode() or 'null')
        except urllib.error.HTTPError as e:
            msg = e.read().decode('utf-8', 'replace')[:300]
            sys.exit(f'{method} {path} → HTTP {e.code}: {msg}')

    def get(self, path):
        return self.call('GET', path)

    def post(self, path, data):
        return self.call('POST', path, data)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if len(args) != 1 or args[0] not in ('local', 'live'):
        sys.exit('uso: python3 -I tools/seed-products.py {local|live} [--dry-run]')
    target, dry = args[0], '--dry-run' in sys.argv
    E = env()
    P = 'WP_LOCAL_' if target == 'local' else 'WP_LIVE_'
    if not E.get(P + 'API') or not E.get(P + 'PASSWORD'):
        sys.exit(f'Faltam {P}API / {P}USER / {P}PASSWORD no .env')

    ctx = ssl.create_default_context()
    ctx.load_verify_locations(str(ROOT / 'config' / 'harica-geant-tls-r1.pem'))
    api = Api(E[P + 'API'], E[P + 'USER'], E[P + 'PASSWORD'], ctx)
    site = E[P + 'API'].split('/index.php/wp-json')[0].split('/wp-json')[0].rstrip('/')
    catalog = json.loads((DIR / 'catalog.json').read_text())

    print(f'site: {site}  ({"dry-run, nada é alterado" if dry else "a escrever"})')

    cats = {c['name']: c['id'] for c in api.get('/wc/v3/products/categories?per_page=100')}
    missing = sorted({p['category'] for p in catalog} - cats.keys())
    if missing:
        sys.exit(f'categorias em falta no site: {", ".join(missing)}')

    # atributo global "Material" e os seus termos
    attr = next((a for a in api.get('/wc/v3/products/attributes') if a['slug'] in ('pa_material', 'material')), None)
    if not attr:
        print('atributo Material: a criar' + (' (dry-run)' if dry else ''))
        attr = {'id': 0} if dry else api.post('/wc/v3/products/attributes', {'name': 'Material', 'slug': 'material', 'has_archives': True})
    if attr['id']:
        have = {t['name'] for t in api.get(f"/wc/v3/products/attributes/{attr['id']}/terms?per_page=100")}
        for m in MATERIALS:
            if m not in have and not dry:
                api.post(f"/wc/v3/products/attributes/{attr['id']}/terms", {'name': m})

    made = skipped = 0
    for p in catalog:
        if api.get('/wc/v3/products?status=any&sku=' + urllib.parse.quote(p['sku'])):
            print(f"  = {p['sku']}  {p['name']}  (já existe)")
            skipped += 1
            continue
        img = DIR / f"{p['image']}.jpg"
        if not img.exists():
            sys.exit(f'falta {img.relative_to(ROOT)} — corre python3 -I tools/product-images.py')
        price = p['price'] + (f" → {p['sale']}" if p.get('sale') else '')
        if dry:
            print(f"  + {p['sku']}  {p['name']}  [{p['category']} · {p['material']} · {price} €]")
            made += 1
            continue
        media = api.call('POST', '/wp/v2/media', raw=img.read_bytes(), headers={
            'Content-Type': 'image/jpeg',
            'Content-Disposition': f'attachment; filename="revivo-{p["image"]}.jpg"'})
        api.post(f"/wp/v2/media/{media['id']}", {'alt_text': p['name'], 'title': p['name']})
        prod = api.post('/wc/v3/products', {
            'name': p['name'], 'type': 'simple', 'status': 'publish', 'sku': p['sku'],
            'regular_price': p['price'], 'sale_price': p.get('sale', ''),
            'short_description': p['short'].replace('{site}', site),
            'description': p['description'].replace('{site}', site),
            'categories': [{'id': cats[p['category']]}],
            'images': [{'id': media['id']}],
            'attributes': [{'id': attr['id'], 'visible': True, 'variation': False, 'options': [p['material']]}],
            'stock_status': 'instock',
        })
        print(f"  + {p['sku']}  {p['name']}  → #{prod['id']}  [{price} €]")
        made += 1
    print(f"\n{'a criar' if dry else 'criados'}: {made} · já existiam: {skipped}")


if __name__ == '__main__':
    main()
