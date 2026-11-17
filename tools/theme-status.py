#!/usr/bin/env python3
"""
Estado do tema Revivo: há overrides do design guardados na base de dados?

O tema é editado em ficheiros (theme/revivo) e versionado no git. Mas o Editor
do Site guarda alterações na BD (wp_template, wp_template_part, wp_global_styles)
e essas cópias passam a esconder os ficheiros do tema. Este comando mostra-as e,
com --reset, apaga-as.

  python3 -I tools/theme-status.py           # ver
  python3 -I tools/theme-status.py --reset   # apagar (pede confirmação)
"""
import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TMP = ROOT / 'wordpress' / '.rv-tmp'

PHP = r'''<?php
list($action, $theme) = $args;
$ids = [];

$q = new WP_Query([
  'post_type' => ['wp_template', 'wp_template_part'],
  'post_status' => 'any', 'posts_per_page' => -1,
  'tax_query' => [['taxonomy' => 'wp_theme', 'field' => 'name', 'terms' => $theme]],
]);
echo "Templates/parts na BD (tema $theme):\n";
if (!$q->posts) {
  echo "  nenhum — o design vem dos ficheiros do tema\n";
}
foreach ($q->posts as $p) {
  echo "  - {$p->post_type} {$p->post_name} (ID {$p->ID})\n";
  $ids[] = $p->ID;
}

$gs = get_posts(['post_type' => 'wp_global_styles', 'post_status' => 'any', 'numberposts' => -1,
  'tax_query' => [['taxonomy' => 'wp_theme', 'field' => 'name', 'terms' => $theme]]]);
echo "\nGlobal Styles na BD:\n";
if (!$gs) {
  echo "  nenhum\n";
}
foreach ($gs as $g) {
  $c = json_decode($g->post_content, true);
  $len = strlen($c['styles']['css'] ?? '');
  echo "  - ID {$g->ID} (CSS personalizado: {$len} bytes)\n";
  if ($len > 0) { $ids[] = $g->ID; }
}

if ($action === 'reset') {
  foreach ($ids as $id) { wp_delete_post($id, true); }
  echo "\nApagados " . count($ids) . " posts. O tema volta a usar só os ficheiros.\n";
}
'''

def main():
    ap = argparse.ArgumentParser(description='Overrides do tema Revivo guardados na BD.')
    ap.add_argument('--reset', action='store_true', help='apagar os overrides (volta aos ficheiros)')
    ap.add_argument('--theme', default='revivo')
    ap.add_argument('-y', '--yes', action='store_true', help='não pedir confirmação')
    args = ap.parse_args()

    if args.reset and not args.yes:
        print('Isto apaga as alterações feitas no Editor do Site para este tema.')
        if input('Continuar? [s/N] ').strip().lower() not in ('s', 'sim', 'y', 'yes'):
            sys.exit('cancelado')

    TMP.mkdir(parents=True, exist_ok=True)
    (TMP / 'theme-status.php').write_text(PHP)
    cmd = ['docker', 'compose', 'run', '--rm', '-T', 'cli', 'wp', 'eval-file',
           '/var/www/html/.rv-tmp/theme-status.php',
           'reset' if args.reset else 'status', args.theme]
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    out = r.stdout + r.stderr
    print('\n'.join(l for l in out.strip().splitlines() if 'Container' not in l))
    if r.returncode:
        sys.exit(1)


if __name__ == '__main__':
    main()
