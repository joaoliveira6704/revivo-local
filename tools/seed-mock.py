#!/usr/bin/env python3
"""
Dados mock para demonstração: clientes, encomendas, avaliações e pedidos de peças.

- Clientes com emails @example.test (domínio reservado, não recebe emails).
- Encomendas pela REST do WooCommerce, com estados variados e meta _rv_mock=1.
  Os emails do WooCommerce são desligados durante a criação e repostos no fim.
- Avaliações dos clientes que compraram o produto (aparecem como compra verificada).
- Pedidos de peças pelo formulário real "Pedir peça" (Contact Form 7) e depois avançados no
  painel "Pedidos de peças" do WP-Admin (sessão de admin), sem avisar o cliente.
  Nota: o Contact Form 7 envia o email normal do formulário ao administrador por cada pedido.
- Um cliente que já exista é ignorado com tudo o que lhe pertence, por isso pode correr-se de novo.

Credenciais (.env): WP_{LOCAL,LIVE}_API / _USER / _PASSWORD (application password) e
WP_{LOCAL,LIVE}_ADMIN_PASSWORD (login do wp-admin, para os pedidos). A senha dos clientes mock fica
em WP_MOCK_PASSWORD (gerada na primeira vez).

Uso:
  python3 -I tools/seed-mock.py local --dry-run
  python3 -I tools/seed-mock.py local
  python3 -I tools/seed-mock.py live
"""
import base64
import http.cookiejar
import json
import re
import secrets
import ssl
import sys
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timedelta, timezone
from html import unescape
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FORM_ID, FORM_PAGE = 51, 53

# nome, apelido, morada, localidade, código postal, telefone
CUSTOMERS = [
    ('Ana', 'Martins', 'Rua Augusta 112, 2.º Esq.', 'Lisboa', '1100-053', '912345101'),
    ('Rui', 'Costa', 'Rua de Santa Catarina 420', 'Porto', '4000-447', '913456202'),
    ('Inês', 'Ferreira', 'Avenida da Liberdade 85', 'Braga', '4710-251', '914567303'),
    ('Tiago', 'Sousa', 'Rua Ferreira Borges 31', 'Coimbra', '3000-180', '915678404'),
    ('Marta', 'Lopes', 'Rua João Mendonça 9', 'Aveiro', '3800-200', '916789505'),
    ('Pedro', 'Almeida', 'Rua de Santo António 54', 'Faro', '8000-283', '917890606'),
]

# cliente, há quantos dias, estado, pagamento, [(sku, qtd)], nota do cliente
ORDERS = [
    (0, 41, 'completed', 'bacs', [('RV-PS-001', 1), ('RV-UT-001', 1)], ''),
    (1, 35, 'completed', 'cod', [('RV-PS-005', 1)], ''),
    (2, 28, 'completed', 'bacs', [('RV-DE-001', 1), ('RV-DE-002', 1)], 'É para oferecer, se puderem não incluir a fatura na caixa.'),
    (3, 21, 'completed', 'bacs', [('RV-AT-002', 1), ('RV-AT-001', 1)], ''),
    (4, 16, 'completed', 'cod', [('RV-PS-002', 1), ('RV-PS-003', 1)], ''),
    (5, 12, 'completed', 'bacs', [('RV-CO-001', 2)], ''),
    (4, 9, 'cancelled', 'bacs', [('RV-DE-002', 1)], ''),
    (0, 6, 'processing', 'bacs', [('RV-UT-002', 1), ('RV-PS-004', 2)], 'Se possível, enviar até sexta-feira.'),
    (1, 4, 'on-hold', 'bacs', [('RV-DE-001', 1)], ''),
    (2, 2, 'processing', 'cod', [('RV-AT-001', 1)], ''),
    (3, 1, 'pending', 'bacs', [('RV-PS-001', 2)], ''),
    (5, 0, 'processing', 'bacs', [('RV-UT-001', 1), ('RV-PS-005', 1)], ''),
]
PAYMENT = {'bacs': 'Transferência bancária', 'cod': 'Pagamento na entrega'}

# cliente (ou nome/email de visitante), sku, estrelas, texto, há quantos dias
REVIEWS = [
    (0, 'RV-PS-001', 5, 'Encaixou à primeira na gaveta do frigorífico. Ficou melhor do que o original!', 38),
    (0, 'RV-UT-001', 4, 'Práticos e discretos. A cola podia ser um pouco mais forte, mas cumprem.', 37),
    (1, 'RV-PS-005', 5, 'A batedeira voltou a funcionar. Poupei uma máquina nova por menos de 10 €.', 31),
    (2, 'RV-DE-001', 5, 'O padrão é lindíssimo e o acabamento muito cuidado. Recebi elogios logo no primeiro dia.', 24),
    (2, 'RV-DE-002', 4, 'Luz muito agradável à noite. Demorou um pouco mais do que esperava a chegar.', 24),
    (3, 'RV-AT-002', 5, 'Robusto e com bom peso, não tomba. Os auscultadores ficam perfeitos.', 18),
    (3, 'RV-AT-001', 4, 'Faz o que promete. Gostava que tivesse mais uma posição de inclinação.', 17),
    (4, 'RV-PS-002', 5, 'Os botões do fogão estavam rachados há meses. Estes servem na perfeição.', 12),
    (4, 'RV-PS-003', 3, 'Dois suportes ficaram perfeitos; os outros dois precisaram de um pouco de lixa para entrar.', 12),
    (5, 'RV-CO-001', 5, 'Detalhe impressionante para o tamanho. Comprei dois, um para oferecer.', 8),
    (('Sofia R.', 'sofia.r@example.test'), 'RV-PS-004', 4, 'Funciona bem no estore da sala. Simples de montar.', 20),
    (('Carlos M.', 'carlos.m@example.test'), 'RV-UT-002', 5, 'A oficina ficou finalmente arrumada. Muito sólido.', 15),
]

# cliente, campos do formulário, estado final, orçamento (valor, dias, mensagem)
REQUESTS = [
    (0, {'tipo': 'Peça de substituição', 'marca': 'Bosch', 'modelo': 'KGN36', 'descricao': 'A prateleira da porta do frigorífico partiu num dos cantos e já não segura as garrafas.',
         'medidas': '320 × 60 × 45 mm', 'quantidade': '1', 'material': 'PETG', 'cor': 'Branco', 'acabamento': 'Standard'},
     'orcamento', ('12.50', 4, 'Vamos imprimir em PETG branco, resistente ao frio. O prazo inclui uma prova de encaixe.')),
    (1, {'tipo': 'Peça de substituição', 'marca': 'Philips', 'modelo': 'HR1628', 'descricao': 'A patilha do engate do copo da varinha mágica partiu e o copo já não prende.',
         'medidas': '35 × 22 × 10 mm', 'quantidade': '1', 'material': 'PETG', 'cor': 'Preto', 'acabamento': 'Standard'},
     'concluido', ('7.90', 3, 'Patilha reforçada em PETG preto.')),
    (2, {'tipo': 'Impressão à medida', 'marca': '', 'modelo': '', 'descricao': 'Suporte de parede para três vasos pequenos, estilo minimalista, para a varanda.',
         'medidas': '40 × 12 × 10 cm', 'quantidade': '1', 'material': 'PLA', 'cor': 'Verde', 'acabamento': 'Com pós-processamento'},
     'analise', None),
    (3, {'tipo': 'Peça de substituição', 'marca': "De'Longhi", 'modelo': 'ECAM 22.110', 'descricao': 'A bandeja de recolha de pingos da máquina de café rachou e verte água.',
         'medidas': '180 × 110 × 15 mm', 'quantidade': '1', 'material': 'PETG', 'cor': 'Preto', 'acabamento': 'Standard'},
     'novo', None),
    (4, {'tipo': 'Impressão à medida', 'marca': '', 'modelo': '', 'descricao': 'Peças de xadrez personalizadas com as iniciais da família no rei e na rainha.',
         'medidas': 'Rei com 8 cm de altura', 'quantidade': '32', 'material': 'Resina', 'cor': 'Branco e preto', 'acabamento': 'Personalizado'},
     'orcamento', ('64.00', 10, 'Conjunto completo em resina, com as iniciais gravadas em relevo. Pintura incluída.')),
    (5, {'tipo': 'Peça de substituição', 'marca': 'IKEA', 'modelo': 'MALM', 'descricao': 'Faltam duas tampas dos puxadores da cómoda.',
         'medidas': '30 × 30 × 8 mm', 'quantidade': '2', 'material': 'PLA', 'cor': 'Branco', 'acabamento': 'Standard'},
     'recusado', ('6.50', 3, 'Duas tampas em PLA branco mate.')),
]


def env():
    d = {}
    for line in (ROOT / '.env').read_text().splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            d[k.strip()] = v.strip()
    return d


def email_of(first, last):
    plain = unicodedata.normalize('NFKD', f'{first}.{last}').encode('ascii', 'ignore').decode().lower()
    return f'{plain}@example.test'


def iso(days_ago, hour=10):
    t = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return t.replace(hour=hour, minute=17 + days_ago % 40, second=0, microsecond=0).strftime('%Y-%m-%dT%H:%M:%S')


class Api:
    def __init__(self, base, user, password, context):
        self.base, self.context = base.rstrip('/'), context
        self.auth = 'Basic ' + base64.b64encode(f'{user}:{password}'.encode()).decode()

    def call(self, method, path, data=None):
        req = urllib.request.Request(self.base + path, method=method,
                                     data=json.dumps(data).encode() if data is not None else None)
        req.add_header('Authorization', self.auth)
        if data is not None:
            req.add_header('Content-Type', 'application/json')
        try:
            with urllib.request.urlopen(req, timeout=120, context=self.context) as r:
                return json.loads(r.read().decode() or 'null')
        except urllib.error.HTTPError as e:
            raise SystemExit(f'{method} {path} → HTTP {e.code}: {e.read().decode("utf-8", "replace")[:300]}')


class Form(HTMLParser):
    """Lê os campos de um formulário do WP-Admin (inputs, textareas e selects), como o browser os enviaria."""

    def __init__(self, attr, value):
        super().__init__()
        self.want = (attr, value)
        self.fields, self.inside, self.textarea, self.select, self.action = {}, False, None, None, None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'form' and a.get(self.want[0]) == self.want[1]:
            self.inside, self.action = True, unescape(a.get('action') or '')
        if not self.inside:
            return
        if tag == 'input' and a.get('name') and a.get('type') not in ('submit', 'button', 'image'):
            if a.get('type') in ('checkbox', 'radio') and 'checked' not in a:
                return
            self.fields[a['name']] = a.get('value', '')
        elif tag == 'textarea' and a.get('name'):
            self.textarea = a['name']
            self.fields[self.textarea] = ''
        elif tag == 'select' and a.get('name'):
            self.select = a['name']
        elif tag == 'option' and self.select and 'selected' in a:
            self.fields[self.select] = a.get('value', '')

    def handle_endtag(self, tag):
        if tag == 'form' and self.inside:
            self.inside = False
        elif tag == 'textarea':
            self.textarea = None
        elif tag == 'select':
            self.select = None

    def handle_data(self, data):
        if self.textarea:
            self.fields[self.textarea] += data


class Admin:
    def __init__(self, base, context):
        self.base = base
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar),
                                                  urllib.request.HTTPSHandler(context=context))
        self.opener.addheaders = [('User-Agent', 'Mozilla/5.0 revivo-mock')]

    def open(self, url, data=None):
        body = urllib.parse.urlencode(data).encode() if data is not None else None
        with self.opener.open(urllib.request.Request(url, data=body), timeout=120) as r:
            return r.read().decode('utf-8', 'replace')

    def login(self, user, password):
        self.open(f'{self.base}/wp-login.php')
        self.open(f'{self.base}/wp-login.php', {'log': user, 'pwd': password, 'wp-submit': 'Log In',
                                                'redirect_to': f'{self.base}/wp-admin/', 'testcookie': '1'})
        return any(c.name.startswith('wordpress_logged_in') for c in self.jar)

    def save_request(self, pid, changes):
        """Grava o pedido pelo formulário do ecrã de edição (mesmo caminho que o botão Guardar)."""
        f = Form('id', 'post')
        f.feed(self.open(f'{self.base}/wp-admin/post.php?post={pid}&action=edit'))
        fields = f.fields
        if '_rvp_admin_nonce' not in fields:
            raise SystemExit(f'pedido #{pid}: não encontrei o formulário do orçamento no WP-Admin')
        fields.pop('rvp_notify', None)  # não avisar o cliente (mock)
        fields.update(changes)
        self.open(f'{self.base}/wp-admin/post.php', fields)

    def set_order_date(self, oid, when):
        """A REST não aceita date_created nas encomendas: muda-a no ecrã da encomenda (campo "Data de criação")."""
        f = Form('name', 'order')
        f.feed(self.open(f'{self.base}/wp-admin/admin.php?page=wc-orders&action=edit&id={oid}'))
        if 'order_date' not in f.fields or not f.action:
            raise SystemExit(f'encomenda #{oid}: não encontrei o formulário da encomenda no WP-Admin')
        f.fields.update({'order_date': when[:10], 'order_date_hour': when[11:13], 'order_date_minute': when[14:16],
                         'order_date_second': '00', 'save': 'Atualizar'})
        self.open(f.action, f.fields)


def submit_request(site, ctx, customer, fields):
    """Envia o formulário "Pedir peça" pela API do Contact Form 7; devolve o número do pedido."""
    first, last = customer[0], customer[1]
    data = {'_wpcf7': str(FORM_ID), '_wpcf7_version': '6', '_wpcf7_locale': 'pt_PT',
            '_wpcf7_unit_tag': f'wpcf7-f{FORM_ID}-p{FORM_PAGE}-o1', '_wpcf7_container_post': str(FORM_PAGE),
            'nome': f'{first} {last}', 'email': email_of(first, last), 'rgpd': '1', **fields}
    b = '----revivo' + uuid.uuid4().hex
    body = b''.join(f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode() for k, v in data.items())
    body += f'--{b}--\r\n'.encode()
    url = f"{site}/index.php/wp-json/contact-form-7/v1/contact-forms/{FORM_ID}/feedback"
    req = urllib.request.Request(url, data=body, method='POST')
    req.add_header('Content-Type', f'multipart/form-data; boundary={b}')
    with urllib.request.urlopen(req, timeout=120, context=ctx) as r:
        res = json.loads(r.read().decode())
    m = re.search(r'#(\d+)', res.get('message', ''))
    if not m:
        raise SystemExit(f'o formulário não criou o pedido: {res.get("status")} — {res.get("message")}')
    return int(m.group(1)), res.get('status')


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if len(args) != 1 or args[0] not in ('local', 'live'):
        sys.exit('uso: python3 -I tools/seed-mock.py {local|live} [--dry-run]')
    target, dry = args[0], '--dry-run' in sys.argv
    E = env()
    P = 'WP_LOCAL_' if target == 'local' else 'WP_LIVE_'
    ctx = ssl.create_default_context()
    ctx.load_verify_locations(str(ROOT / 'config' / 'harica-geant-tls-r1.pem'))
    api = Api(E[P + 'API'], E[P + 'USER'], E[P + 'PASSWORD'], ctx)
    site = E[P + 'API'].split('/index.php/wp-json')[0].split('/wp-json')[0].rstrip('/')
    print(f'site: {site}  ({"dry-run, nada é alterado" if dry else "a escrever"})')

    products = {}
    for sku in sorted({s for o in ORDERS for s, _ in o[4]} | {r[1] for r in REVIEWS}):
        found = api.call('GET', '/wc/v3/products?status=any&sku=' + urllib.parse.quote(sku))
        if not found:
            sys.exit(f'falta o produto {sku} — corre primeiro tools/seed-products.py {target}')
        products[sku] = found[0]

    existing = {i for i, c in enumerate(CUSTOMERS) if api.call('GET', '/wc/v3/customers?email=' + urllib.parse.quote(email_of(c[0], c[1])))}
    new = [i for i in range(len(CUSTOMERS)) if i not in existing]
    print(f'clientes mock: {len(new)} novos, {len(existing)} já existem (ignorados com os seus dados)')

    admin = None
    if new:
        if not E.get(P + 'ADMIN_PASSWORD'):
            sys.exit(f'Falta {P}ADMIN_PASSWORD no .env (login do wp-admin, para as datas das encomendas e os pedidos)')
        admin = Admin(site, ctx)
        if not admin.login(E[P + 'USER'], E[P + 'ADMIN_PASSWORD']):
            sys.exit(f'login no wp-admin falhou (verifica {P}ADMIN_PASSWORD)')
        print('wp-admin: login OK')

    if dry:
        for i in new:
            print(f'  + cliente {CUSTOMERS[i][0]} {CUSTOMERS[i][1]} <{email_of(*CUSTOMERS[i][:2])}>')
        print(f"  + {sum(o[0] in new for o in ORDERS)} encomendas · {sum(isinstance(r[0], tuple) or r[0] in new for r in REVIEWS)} avaliações"
              f" · {sum(r[0] in new for r in REQUESTS)} pedidos de peças")
        return
    if not new:
        print('nada a fazer')
        return

    if not E.get('WP_MOCK_PASSWORD'):
        E['WP_MOCK_PASSWORD'] = secrets.token_urlsafe(12)
        with (ROOT / '.env').open('a') as f:
            f.write(f"WP_MOCK_PASSWORD={E['WP_MOCK_PASSWORD']}\n")

    # emails do WooCommerce desligados durante a criação
    groups = [g['id'] for g in api.call('GET', '/wc/v3/settings') if g['id'].startswith('email_')]
    was_on = [g for g in groups if any(o['id'] == 'enabled' and o['value'] == 'yes' for o in api.call('GET', f'/wc/v3/settings/{g}'))]
    for g in was_on:
        api.call('POST', f'/wc/v3/settings/{g}/enabled', {'value': 'no'})
    print(f'emails WooCommerce: {len(was_on)} desligados temporariamente')
    try:
        ids = {}
        for i in new:
            first, last, addr, city, pc, phone = CUSTOMERS[i]
            address = {'first_name': first, 'last_name': last, 'address_1': addr, 'city': city,
                       'postcode': pc, 'country': 'PT'}
            c = api.call('POST', '/wc/v3/customers', {
                'email': email_of(first, last), 'first_name': first, 'last_name': last,
                'username': email_of(first, last).split('@')[0], 'password': E['WP_MOCK_PASSWORD'],
                'billing': {**address, 'email': email_of(first, last), 'phone': phone}, 'shipping': address,
                'meta_data': [{'key': '_rv_mock', 'value': '1'}]})
            ids[i] = c
            print(f'  + cliente #{c["id"]} {first} {last}')

        for ci, days, status, pay, items, note in ORDERS:
            if ci not in ids:
                continue
            c = ids[ci]
            subtotal = sum(float(products[s]['price']) * q for s, q in items)
            ship = [{'method_id': 'free_shipping', 'method_title': 'Portes grátis', 'total': '0.00'}] if subtotal >= 40 else \
                   [{'method_id': 'flat_rate', 'method_title': 'Envio CTT', 'total': '3.90'}]
            o = api.call('POST', '/wc/v3/orders', {
                'customer_id': c['id'], 'status': status, 'payment_method': pay, 'payment_method_title': PAYMENT[pay],
                'set_paid': status in ('processing', 'completed'), 'billing': c['billing'], 'shipping': c['shipping'],
                'line_items': [{'product_id': products[s]['id'], 'quantity': q} for s, q in items],
                'shipping_lines': ship, 'customer_note': note,
                'meta_data': [{'key': '_rv_mock', 'value': '1'}]})
            admin.set_order_date(o['id'], iso(days))
            o = api.call('GET', f"/wc/v3/orders/{o['id']}")
            print(f'  + encomenda #{o["id"]} {c["first_name"]:6} {status:10} {o["total"]:>6} €  ({o["date_created"][:10]})')

        for who, sku, stars, text, days in REVIEWS:
            if isinstance(who, tuple):
                name, mail = who
                if any(r['reviewer_email'] == mail for r in api.call('GET', f"/wc/v3/products/reviews?product={products[sku]['id']}&per_page=100")):
                    continue
            elif who in ids:
                name, mail = f"{ids[who]['first_name']} {ids[who]['last_name'][0]}.", ids[who]['email']
            else:
                continue
            r = api.call('POST', '/wc/v3/products/reviews', {
                'product_id': products[sku]['id'], 'review': text, 'reviewer': name, 'reviewer_email': mail,
                'rating': stars, 'status': 'approved', 'date_created': iso(days, 19)})
            print(f'  + avaliação {"★" * stars:5} {sku} — {name}{" (compra verificada)" if r.get("verified") else ""}')
    finally:
        for g in was_on:
            api.call('POST', f'/wc/v3/settings/{g}/enabled', {'value': 'yes'})
        print(f'emails WooCommerce: {len(was_on)} repostos')

    for ci, fields, final, quote in REQUESTS:
        if ci not in ids:
            continue
        pid, st = submit_request(site, ctx, CUSTOMERS[ci], fields)
        if quote:
            admin.save_request(pid, {'rvp_quote_price': quote[0], 'rvp_quote_days': str(quote[1]),
                                     'rvp_quote_message': quote[2], 'rvp_send_quote': '1'})
        if final not in ('novo', 'orcamento'):
            admin.save_request(pid, {'rvp_status': final, 'rvp_save': '1'})
        print(f'  + pedido de peça #{pid} {CUSTOMERS[ci][0]:6} → {final}{" (" + quote[0] + " €)" if quote else ""}'
              f'{"" if st == "mail_sent" else "  [formulário: " + st + "]"}')

    print(f"\nclientes mock: senha em WP_MOCK_PASSWORD no .env (ex.: login {email_of(*CUSTOMERS[new[0]][:2])})")


if __name__ == '__main__':
    main()
