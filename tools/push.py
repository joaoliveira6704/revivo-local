#!/usr/bin/env python3
"""
Revivo — envia alterações do WordPress local (Docker) para o site real, via REST API.

  ./push.sh diff                    lista o que está diferente entre local e site real
  ./push.sh diff <tipo> <slug>      mostra as diferenças de um item (linha a linha)
  ./push.sh css                     envia os Global Styles (CSS adicional, cores, tipografia)
  ./push.sh part <slug>             envia uma template part (ex.: header, footer)
  ./push.sh template <slug>         envia um template (ex.: page, single-product)
  ./push.sh page <slug>             envia o conteúdo e título de uma página (ex.: pedir-peca)
  ./push.sh all                     envia tudo o que estiver diferente

Antes de escrever, guarda a versão do site real em backups/<data-hora>/ e pede confirmação
(usa -y para não perguntar). Tipos: css, part, template, page.
"""
import difflib, json, os, ssl, subprocess, sys, base64, urllib.request, urllib.error
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
THEME = 'twentytwentyfive'


def load_env():
    env = {}
    for line in (ROOT / '.env').read_text().splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            env[k.strip()] = v.strip()
    return env


ENV = load_env()
API = ENV['WP_LIVE_API'].rstrip('/')
LIVE_URL = API.split('/index.php/wp-json')[0].split('/wp-json')[0]
LOCAL_URL = ENV.get('WP_LOCAL_URL', 'http://localhost:8080').rstrip('/')


def to_live(text):
    """Os URLs locais (http://localhost:8080) passam a ser os do site real, também na forma escapada em JSON."""
    if not text:
        return text
    for a, b in ((LOCAL_URL, LIVE_URL), (LOCAL_URL.replace('/', '\\/'), LIVE_URL.replace('/', '\\/'))):
        text = text.replace(a, b)
    return text
AUTH = 'Basic ' + base64.b64encode(f"{ENV['WP_LIVE_USER']}:{ENV['WP_LIVE_PASSWORD']}".encode()).decode()

# o servidor da escola não envia o certificado intermédio; juntamo-lo aqui em vez de desligar a verificação
CTX = ssl.create_default_context()
CTX.load_verify_locations(str(ROOT / 'config' / 'harica-geant-tls-r1.pem'))


# ---------------------------------------------------------------- site real (REST)
def live(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(API + path, data=data, method=method,
                                 headers={'Authorization': AUTH, 'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, context=CTX, timeout=60) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        sys.exit(f'Erro {e.code} em {method} {path}: {e.read().decode()[:400]}')


def live_items():
    items = {}
    gs = live('GET', '/wp/v2/global-styles/' + str(live_global_styles_id()) + '?context=edit')
    items[('css', 'global-styles')] = {'id': gs['id'], 'content': norm_gs(gs.get('styles'), gs.get('settings'))}
    for kind, route in (('part', 'template-parts'), ('template', 'templates')):
        for t in live('GET', f'/wp/v2/{route}?context=edit&per_page=100'):
            if t.get('theme') == THEME:
                items[(kind, t['slug'])] = {'id': t['id'], 'content': t['content']['raw'], 'source': t.get('source')}
    page = 1
    while True:
        batch = live('GET', f'/wp/v2/pages?context=edit&per_page=100&page={page}&status=publish,draft,private')
        for p in batch:
            items[('page', p['slug'])] = {'id': p['id'], 'content': p['content']['raw'], 'title': p['title']['raw'], 'status': p['status'], 'excerpt': p['excerpt']['raw']}
        if len(batch) < 100:
            break
        page += 1
    return items


_gs_id = None
def live_global_styles_id():
    global _gs_id
    if _gs_id is None:
        theme = live('GET', '/wp/v2/themes?status=active')[0]
        _gs_id = int(theme['_links']['wp:user-global-styles'][0]['href'].rstrip('/').split('/')[-1])
    return _gs_id


# ---------------------------------------------------------------- site local (wp-cli no Docker)
PHP_DUMP = r'''
$out = [];
$q = new WP_Query(['post_type' => ['wp_template_part','wp_template','wp_global_styles','page'],
  'post_status' => ['publish','draft','private'], 'posts_per_page' => -1, 'no_found_rows' => true,
  'update_post_term_cache' => true]);
foreach ($q->posts as $p) {
  $theme = wp_get_post_terms($p->ID, 'wp_theme', ['fields' => 'names']);
  $out[] = ['type' => $p->post_type, 'slug' => $p->post_name, 'title' => $p->post_title, 'excerpt' => $p->post_excerpt,
            'status' => $p->post_status, 'content' => $p->post_content,
            'theme' => is_array($theme) && $theme ? $theme[0] : null];
}
echo json_encode($out);
'''


def local_items():
    r = subprocess.run(['docker', 'compose', 'run', '--rm', '-T', 'cli', 'wp', 'eval', PHP_DUMP],
                       cwd=ROOT, capture_output=True, text=True)
    out = r.stdout[r.stdout.find('['):]
    if r.returncode != 0 or not out:
        sys.exit('Não consegui ler o WordPress local (o Docker está a correr?)\n' + r.stderr[-800:])
    items = {}
    for p in json.loads(out):
        p['content'] = to_live(p['content'])
        if p['type'] == 'wp_global_styles':
            if p['theme'] == THEME:
                d = json.loads(p['content'] or '{}')
                items[('css', 'global-styles')] = {'content': norm_gs(d.get('styles'), d.get('settings'))}
        elif p['type'] in ('wp_template_part', 'wp_template'):
            if p['theme'] == THEME:
                kind = 'part' if p['type'] == 'wp_template_part' else 'template'
                items[(kind, p['slug'])] = {'content': p['content']}
        else:
            items[('page', p['slug'])] = {'content': p['content'], 'title': p['title'], 'status': p['status'], 'excerpt': p['excerpt']}
    return items


# ---------------------------------------------------------------- comparação
def norm_gs(styles, settings):
    return json.dumps({'styles': styles or {}, 'settings': settings or {}}, ensure_ascii=False, indent=1, sort_keys=True)


def same(a, b):
    return (a or '').replace('\r\n', '\n').strip() == (b or '').replace('\r\n', '\n').strip()


def changed(loc, liv):
    out = []
    for key, it in sorted(loc.items()):
        other = liv.get(key)
        if other is None:
            out.append((key, 'novo (não existe no site real)'))
        elif not same(it['content'], other['content']) or (key[0] == 'page' and (it.get('title') != other.get('title') or it.get('status') != other.get('status') or (it.get('excerpt') or '') != (other.get('excerpt') or ''))):
            out.append((key, 'alterado'))
    return out


def show_diff(key, loc, liv):
    a = (liv.get(key) or {}).get('content', '')
    b = loc[key]['content']
    if key[0] == 'css':  # o CSS adicional vem numa só linha JSON; mostrar como texto
        a = json.loads(a or '{}').get('styles', {}).get('css', '') + '\n' + a
        b = json.loads(b).get('styles', {}).get('css', '') + '\n' + b
    lines = difflib.unified_diff(a.splitlines(), b.splitlines(), 'site real', 'local', lineterm='', n=2)
    print('\n'.join(lines) or '(sem diferenças)')


# ---------------------------------------------------------------- envio
def backup(key, data):
    d = ROOT / 'backups' / datetime.now().strftime('%Y-%m-%d_%H%M%S')
    d.mkdir(parents=True, exist_ok=True)
    f = d / f'{key[0]}-{key[1]}.json'
    f.write_text(json.dumps(data, ensure_ascii=False, indent=1))
    return f.relative_to(ROOT)


def push(key, loc, liv):
    kind, slug = key
    it = loc[key]
    if kind == 'css':
        gs_id = live_global_styles_id()
        cur = live('GET', f'/wp/v2/global-styles/{gs_id}?context=edit')
        print('  backup:', backup(key, cur))
        d = json.loads(it['content'])
        res = live('POST', f'/wp/v2/global-styles/{gs_id}', {'styles': d['styles'], 'settings': d['settings']})
        ok = norm_gs(res.get('styles'), res.get('settings')) == it['content']
    elif kind in ('part', 'template'):
        route = 'template-parts' if kind == 'part' else 'templates'
        tid = f'{THEME}//{slug}'
        if key in liv:
            print('  backup:', backup(key, live('GET', f'/wp/v2/{route}/{tid}?context=edit')))
        res = live('POST', f'/wp/v2/{route}/{tid}', {'content': it['content']})
        ok = same(res['content']['raw'], it['content'])
    elif kind == 'page':
        body = {'content': it['content'], 'title': it['title'], 'status': it.get('status', 'publish'), 'excerpt': it.get('excerpt', '')}
        if key in liv:
            pid = liv[key]['id']
            print('  backup:', backup(key, live('GET', f'/wp/v2/pages/{pid}?context=edit')))
            res = live('POST', f'/wp/v2/pages/{pid}', body)
        else:
            res = live('POST', '/wp/v2/pages', dict(body, slug=slug))
        ok = same(res['content']['raw'], it['content'])
    print(f'  {"✔ enviado" if ok else "⚠ enviado, mas o site real devolveu conteúdo diferente — verifica"}: {kind} {slug}')


def confirm(msg, yes):
    if yes:
        return True
    return input(f'{msg} [s/N] ').strip().lower() in ('s', 'sim', 'y', 'yes')


def main(argv):
    yes = '-y' in argv
    args = [a for a in argv if a != '-y']
    if not args or args[0] in ('-h', '--help', 'help'):
        print(__doc__)
        return
    cmd = args[0]
    print('A ler site local e site real…')
    loc, liv = local_items(), live_items()

    if cmd == 'diff':
        if len(args) >= 2:
            key = ('css', 'global-styles') if args[1] == 'css' else (args[1], args[2] if len(args) > 2 else '')
            if key not in loc:
                sys.exit(f'Não existe localmente: {key[0]} {key[1]}')
            show_diff(key, loc, liv)
            return
        ch = changed(loc, liv)
        if not ch:
            print('Tudo igual — nada para enviar.')
        for (kind, slug), why in ch:
            print(f'  {kind:9} {slug:30} {why}')
        return

    if cmd == 'all':
        keys = [k for k, _ in changed(loc, liv)]
    elif cmd == 'css':
        keys = [('css', 'global-styles')]
    elif cmd in ('part', 'template', 'page') and len(args) > 1:
        keys = [(cmd, s) for s in args[1:]]
    else:
        sys.exit(__doc__)

    keys = [k for k in keys if k in loc]
    todo = [k for k in keys if k not in liv or not same(loc[k]['content'], liv[k]['content'])
            or (k[0] == 'page' and (loc[k].get('title') != liv[k].get('title') or loc[k].get('status') != liv[k].get('status') or (loc[k].get('excerpt') or '') != (liv[k].get('excerpt') or '')))]
    if not todo:
        print('Nada para enviar — local e site real já são iguais.')
        return
    print('Vai enviar para o site real:')
    for k in todo:
        print(f'  {k[0]:9} {k[1]}')
    if not confirm('Continuar?', yes):
        print('Cancelado.')
        return
    for k in todo:
        push(k, loc, liv)


if __name__ == '__main__':
    main(sys.argv[1:])
