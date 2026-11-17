#!/usr/bin/env python3
"""
Aplica o design (design/*.css, design/revivo.js) ao WordPress LOCAL.

  python3 -I design/apply.py          aplica CSS + JS
  python3 -I design/apply.py css      só o CSS
  python3 -I design/apply.py js       só o JS (vai para o footer)
  python3 -I design/apply.py templates  templates de design/templates/*.html (loja, produto, carrinho…)

CSS final = design/custom.original.css (base) + design/revivo-v2.css (camada 2.0)
            → "CSS adicional" dos Global Styles (post wp_global_styles).
JS        = design/revivo.js → bloco HTML marcado no fim da template part "footer".
Depois: ./push.sh diff  e  ./push.sh css / ./push.sh part footer  para o site real.
"""
import json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / 'design'
TMP = ROOT / 'wordpress' / '.rv-tmp'
JS_START, JS_END = '<!-- wp:html {"className":"rv-js-block"} -->', '<!-- /wp:html -->'

# corre dentro do WordPress: grava conteúdo sem filtros kses (scripts) e sem perder barras invertidas
PHP = r'''<?php
list($kind, $file) = $args;
$admins = get_users(['role' => 'administrator', 'number' => 1, 'fields' => 'ID']);
wp_set_current_user($admins[0]);
kses_remove_filters();
$data = json_decode(file_get_contents($file), true);
if ($kind === 'css') {
  $p = get_posts(['post_type' => 'wp_global_styles', 'post_status' => 'publish', 'numberposts' => 1,
    'tax_query' => [['taxonomy' => 'wp_theme', 'field' => 'name', 'terms' => get_stylesheet()]]])[0];
  $cfg = json_decode($p->post_content, true);
  $cfg['styles']['css'] = $data['css'];
  $r = wp_update_post(wp_slash(['ID' => $p->ID, 'post_content' => wp_json_encode($cfg)]), true);
} elseif ($kind === 'template') {
  $type = $data['type'];
  $t = get_block_template(get_stylesheet() . '//' . $data['slug'], $type);
  if ($t && $t->wp_id) {
    $r = wp_update_post(wp_slash(['ID' => $t->wp_id, 'post_content' => $data['content']]), true);
  } else {
    $r = wp_insert_post(wp_slash(['post_type' => $type, 'post_status' => 'publish', 'post_name' => $data['slug'],
      'post_title' => $data['title'], 'post_content' => $data['content']]), true);
    if (!is_wp_error($r)) {
      wp_set_object_terms($r, get_stylesheet(), 'wp_theme');
      if ($type === 'wp_template_part') wp_set_object_terms($r, $data['area'] ?? 'uncategorized', 'wp_template_part_area');
    }
  }
} elseif ($kind === 'page') {
  $ex = get_page_by_path($data['slug'], OBJECT, 'page');
  if (!$ex && !empty($data['id'])) $ex = get_post((int)$data['id']);
  $arr = ['post_type' => 'page', 'post_status' => 'publish', 'post_name' => $data['slug'], 'post_title' => $data['title'], 'post_content' => $data['content']];
  if ($ex) $arr['ID'] = $ex->ID;
  $r = $ex ? wp_update_post(wp_slash($arr), true) : wp_insert_post(wp_slash($arr), true);
} elseif ($kind === 'option') {
  foreach ($data as $k => $v) update_option($k, $v);
  $r = 0;
} elseif ($kind === 'post') {
  $r = wp_update_post(wp_slash(['ID' => (int)$data['id'], 'post_content' => $data['content']]), true);
} else {
  $p = get_block_template(get_stylesheet() . '//footer', 'wp_template_part');
  $c = $p->content;
  $start = strpos($c, $data['start']);
  if ($start !== false) {
    $end = strpos($c, $data['end'], $start) + strlen($data['end']);
    $c = substr($c, 0, $start) . $data['block'] . substr($c, $end);
  } else {
    $c = rtrim($c) . "\n\n" . $data['block'];
  }
  $r = $p->wp_id ? wp_update_post(wp_slash(['ID' => $p->wp_id, 'post_content' => $c]), true) : new WP_Error('no-post', 'footer não está guardado na BD');
}
if (is_wp_error($r)) { WP_CLI::error($r->get_error_message()); }
wp_cache_flush();
WP_CLI::success("$kind aplicado (post $r)");
'''


def wp_eval(kind, payload):
    TMP.mkdir(exist_ok=True)
    (TMP / 'apply.php').write_text(PHP)
    (TMP / f'{kind}.json').write_text(json.dumps(payload, ensure_ascii=False))
    r = subprocess.run(['docker', 'compose', 'run', '--rm', '-T', 'cli', 'wp', 'eval-file',
                        '/var/www/html/.rv-tmp/apply.php', kind, f'/var/www/html/.rv-tmp/{kind}.json'],
                       cwd=ROOT, capture_output=True, text=True)
    out = (r.stdout + r.stderr).strip().splitlines()
    print('\n'.join(l for l in out if 'Container' not in l))
    if r.returncode:
        sys.exit(1)


def apply_css():
    css = (D / 'custom.original.css').read_text().rstrip()
    for f in ('revivo-v2.css', 'revivo-shop.css'):
        if (D / f).exists():
            css += '\n\n' + (D / f).read_text()
    wp_eval('css', {'css': css})


def apply_js():
    js = (D / 'revivo.js').read_text().strip()
    # o wptexturize do WordPress confunde "x < y" com uma tag HTML e passa a estragar o resto do script
    import re
    bad = [l.strip() for l in js.splitlines() if re.search(r"<\s*[0-9A-Za-z(_$]", re.sub(r"'[^']*'", "''", l))]
    if bad:
        sys.exit('revivo.js tem comparações com "<" (usar ">" invertido):\n  ' + '\n  '.join(bad))
    block = f'{JS_START}\n<script>\n{js}\n</script>\n{JS_END}'
    wp_eval('js', {'start': JS_START, 'end': JS_END, 'block': block})


def apply_templates():
    """design/templates/<slug>.html → templates do tema (wp_template) no site local."""
    titles = {'archive-product': 'Catálogo de produtos', 'single-product': 'Produto', 'page-cart': 'Página do carrinho',
              'page-checkout': 'Página de finalização de compra', 'product-search-results': 'Resultados de pesquisa de produtos', 'page': 'Páginas',
              'order-confirmation': 'Confirmação de encomenda', 'search': 'Resultados da pesquisa'}
    for f in sorted((D / 'templates').glob('*.html')):
        wp_eval('template', {'type': 'wp_template', 'slug': f.stem, 'title': titles.get(f.stem, f.stem),
                             'content': f.read_text()})


def upsert_page(slug, title, content, page_id=0):
    wp_eval('page', {'slug': slug, 'title': title, 'content': content, 'id': page_id})


def set_options(opts):
    wp_eval('option', opts)


def update_post(post_id, content):
    wp_eval('post', {'id': post_id, 'content': content})


if __name__ == '__main__':
    what = sys.argv[1] if len(sys.argv) > 1 else 'all'
    if what in ('all', 'css'):
        apply_css()
    if what in ('all', 'js'):
        apply_js()
    if what in ('all', 'templates'):
        apply_templates()
