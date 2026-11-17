<?php
/**
 * Produtos de demonstração — SÓ PARA O SITE LOCAL.
 * docker compose run --rm cli wp eval-file /var/www/html/.rv-tmp/seed.php
 * Idempotente: identifica os produtos pelo meta _rv_demo e não os duplica.
 */
require_once ABSPATH . 'wp-admin/includes/media.php';
require_once ABSPATH . 'wp-admin/includes/file.php';
require_once ABSPATH . 'wp-admin/includes/image.php';
$admins = get_users(['role' => 'administrator', 'number' => 1, 'fields' => 'ID']);
wp_set_current_user($admins[0]);

// atributo global "Material"
$attr_id = wc_attribute_taxonomy_id_by_name('material');
if (!$attr_id) {
  $attr_id = wc_create_attribute(['name' => 'Material', 'slug' => 'material', 'type' => 'select', 'order_by' => 'menu_order', 'has_archives' => false]);
  register_taxonomy('pa_material', ['product'], ['hierarchical' => false, 'label' => 'Material']);
}
foreach (['PLA', 'PETG', 'Resina'] as $t) { if (!term_exists($t, 'pa_material')) wp_insert_term($t, 'pa_material'); }

$cat = function ($slug) { $t = get_term_by('slug', $slug, 'product_cat'); return $t ? $t->term_id : 0; };
$img_dir = '/var/www/html/.rv-tmp/img/';

$products = [
  ['Botão de máquina de lavar universal', 'botao-maquina', 'pecas-de-substituicao', '4.90', '', ['PETG'], 'Botão rotativo compatível com os eixos de 6 mm mais comuns. Impresso em PETG, resistente à humidade e ao calor.', false],
  ['Puxador de frigorífico clássico', 'puxador-frigorifico', 'pecas-de-substituicao', '7.50', '', ['PETG'], 'Réplica do puxador de porta de modelos clássicos. Indique a marca e o modelo para confirmarmos a compatibilidade.', true],
  ['Engrenagem para batedeira', 'engrenagem-batedeira', 'pecas-de-substituicao', '5.90', '4.90', ['PETG', 'Resina'], 'Engrenagem de substituição para batedeiras e misturadoras. Dentes reforçados para maior durabilidade.', false],
  ['Dobradiça de tampa de micro-ondas', 'dobradica-microondas', 'pecas-de-substituicao', '6.50', '', ['PETG'], 'Dobradiça de substituição para a tampa interior do micro-ondas, resistente à temperatura.', false],
  ['Vaso geométrico Facetas', 'vaso-facetas', 'decoracao', '18.00', '', ['PLA'], 'Vaso decorativo com faces geométricas, ideal para plantas secas ou como peça de destaque.', true],
  ['Candeeiro de mesa Onda', 'candeeiro-onda', 'decoracao', '34.00', '', ['PLA'], 'Candeeiro com abajur ondulado que difunde uma luz quente e suave. Inclui casquilho E14.', false],
  ['Organizador de secretária modular', 'organizador-secretaria', 'utilitarios', '12.50', '', ['PLA', 'PETG'], 'Módulos encaixáveis para canetas, cartões e pequenos objetos. Combine como quiser.', false],
  ['Suporte de parede para ferramentas', 'suporte-ferramentas', 'utilitarios', '9.90', '', ['PETG'], 'Ganchos robustos para pendurar ferramentas, cabos ou utensílios de cozinha.', false],
  ['Figura colecionável Pinguim', 'dragao-articulado', 'colecionaveis', '22.00', '18.90', ['Resina'], 'Figura em resina com acabamento liso e detalhe fino. Edição limitada da coleção Revivo.', true],
  ['Miniatura de farol', 'miniatura-farol', 'colecionaveis', '15.00', '', ['Resina'], 'Miniatura de farol costeiro impressa em resina, pronta a pintar ou a expor.', false],
  ['Suporte de telemóvel ajustável', 'suporte-telemovel', 'acessorios-tecnologicos', '11.90', '', ['PLA'], 'Suporte estável com ângulo ideal para videochamadas e receitas na cozinha.', false],
  ['Organizador de cabos (pack 6)', 'organizador-cabos', 'acessorios-tecnologicos', '6.90', '', ['PETG'], 'Seis clips para manter os cabos da secretária arrumados e à mão.', false],
  ['Impressão à medida', 'impressao-medida', 'impressoes-a-medida', '10.00', '', ['PLA', 'PETG', 'Resina'], 'Envie-nos o seu modelo 3D ou a sua ideia e imprimimos na cor, material e acabamento que escolher. Preço base por peça.', false],
];

foreach ($products as $i => [$name, $img, $catslug, $price, $sale, $mats, $desc, $featured]) {
  $found = get_posts(['post_type' => 'product', 'post_status' => 'any', 'meta_key' => '_rv_demo', 'meta_value' => $img, 'fields' => 'ids']);
  $p = $found ? wc_get_product($found[0]) : new WC_Product_Simple();
  $p->set_name($name);
  $p->set_status('publish');
  $p->set_regular_price($price);
  $p->set_sale_price($sale);
  $p->set_short_description($desc);
  $p->set_description($desc . "\n\nProduzido sob encomenda pela Revivo. Prazo estimado de produção: 3 a 5 dias úteis.");
  $p->set_category_ids([$cat($catslug)]);
  $p->set_featured($featured);
  $p->set_manage_stock(false);
  $p->set_stock_status('instock');
  $p->set_menu_order($i);
  $a = new WC_Product_Attribute();
  $a->set_id($attr_id); $a->set_name('pa_material');
  $a->set_options(array_map(fn($m) => get_term_by('name', $m, 'pa_material')->term_id, $mats));
  $a->set_visible(true); $a->set_variation(false);
  $p->set_attributes([$a]);
  $id = $p->save();
  update_post_meta($id, '_rv_demo', $img);
  wp_set_object_terms($id, $mats, 'pa_material');
  if (!$p->get_image_id() && file_exists($img_dir . $img . '.png')) {
    $tmp = wp_tempnam($img . '.png'); copy($img_dir . $img . '.png', $tmp);
    $att = media_handle_sideload(['name' => 'revivo-' . $img . '.png', 'tmp_name' => $tmp], $id, $name);
    if (!is_wp_error($att)) { $p->set_image_id($att); $p->save(); }
  }
  WP_CLI::log("✔ $name (#$id)");
}

// produto existente: Roda de Prato → Peças de substituição + PETG
$rp = wc_get_product(31);
if ($rp) {
  $rp->set_category_ids([$cat('pecas-de-substituicao')]);
  $a = new WC_Product_Attribute(); $a->set_id($attr_id); $a->set_name('pa_material');
  $a->set_options([get_term_by('name', 'PETG', 'pa_material')->term_id]); $a->set_visible(true);
  $rp->set_attributes([$a]); $rp->save(); wp_set_object_terms(31, ['PETG'], 'pa_material');
  WP_CLI::log('✔ Roda de Prato atualizada');
}
wc_delete_product_transients();
WP_CLI::success('Produtos de demonstração prontos.');
