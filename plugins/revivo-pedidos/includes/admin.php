<?php
/**
 * Administração: lista de pedidos, detalhe e envio de orçamento.
 */
defined('ABSPATH') || exit;

/* ---------- menu com contador de pedidos novos ---------- */
add_action('admin_menu', function () {
	global $menu;
	$n = (new WP_Query(['post_type' => RVP_CPT, 'post_status' => 'publish', 'fields' => 'ids', 'posts_per_page' => -1,
		'meta_query' => [['key' => '_rvp_status', 'value' => 'novo']]]))->found_posts;
	if (!$n) return;
	foreach ($menu as $i => $item) {
		if (($item[2] ?? '') === 'edit.php?post_type=' . RVP_CPT) {
			$menu[$i][0] .= ' <span class="awaiting-mod"><span class="pending-count">' . (int) $n . '</span></span>';
		}
	}
}, 99);

add_action('admin_enqueue_scripts', function ($hook) {
	$screen = get_current_screen();
	if ($screen && ($screen->post_type === RVP_CPT || $screen->id === 'dashboard')) {
		wp_enqueue_style('rvp-admin', RVP_URL . 'assets/admin.css', [], RVP_VERSION);
	}
});

/* ---------- lista ---------- */
add_filter('manage_' . RVP_CPT . '_posts_columns', function () {
	return ['cb' => '<input type="checkbox">', 'title' => 'Pedido', 'rvp_cliente' => 'Cliente', 'rvp_tipo' => 'Tipo / material',
		'rvp_status' => 'Estado', 'rvp_quote' => 'Orçamento', 'date' => 'Data'];
});
add_action('manage_' . RVP_CPT . '_posts_custom_column', function ($col, $id) {
	switch ($col) {
		case 'rvp_cliente':
			echo '<b>' . esc_html(rvp_get($id, 'nome', '—')) . '</b><br><a href="mailto:' . esc_attr(rvp_get($id, 'email')) . '">' . esc_html(rvp_get($id, 'email')) . '</a>';
			if (!(int) rvp_get($id, 'user_id', 0)) echo '<br><span class="rvp-muted">sem conta</span>';
			break;
		case 'rvp_tipo':
			echo esc_html(rvp_get($id, 'tipo', '—')) . '<br><span class="rvp-muted">' . esc_html(rvp_get($id, 'material', '—')) . ' · ' . esc_html(rvp_get($id, 'medidas', '—')) . ' · ×' . esc_html(rvp_get($id, 'quantidade', '1')) . '</span>';
			break;
		case 'rvp_status':
			echo '<span class="rvp-pill rvp-pill--' . esc_attr(rvp_status($id)) . '">' . esc_html(rvp_status_label(rvp_status($id))) . '</span>';
			break;
		case 'rvp_quote':
			$p = rvp_get($id, 'quote_price');
			echo $p !== '' ? '<b>' . esc_html(rvp_money($p)) . '</b>' : '<span class="rvp-muted">' . (rvp_get($id, 'estimativa') ? 'estimativa: ' . esc_html(rvp_get($id, 'estimativa')) : '—') . '</span>';
			break;
	}
}, 10, 2);
add_filter('post_row_actions', function ($actions, $post) {
	if ($post->post_type === RVP_CPT) {
		unset($actions['inline hide-if-no-js']);
		$actions['edit'] = '<a href="' . esc_url(get_edit_post_link($post->ID)) . '">' . (rvp_status($post->ID) === 'novo' ? 'Dar orçamento' : 'Abrir') . '</a>';
	}
	return $actions;
}, 10, 2);

/* filtros por estado (separadores por cima da lista) */
add_filter('views_edit-' . RVP_CPT, function ($views) {
	$cur = sanitize_key($_GET['rvp_status'] ?? '');
	$base = admin_url('edit.php?post_type=' . RVP_CPT);
	$out = ['all' => '<a href="' . esc_url($base) . '"' . (!$cur ? ' class="current"' : '') . '>Todos</a>'];
	foreach (rvp_statuses() as $k => [$label]) {
		$n = (new WP_Query(['post_type' => RVP_CPT, 'post_status' => 'publish', 'fields' => 'ids', 'posts_per_page' => -1, 'meta_query' => [['key' => '_rvp_status', 'value' => $k]]]))->found_posts;
		if (!$n) continue;
		$out[$k] = '<a href="' . esc_url(add_query_arg('rvp_status', $k, $base)) . '"' . ($cur === $k ? ' class="current"' : '') . '>' . esc_html($label) . ' <span class="count">(' . $n . ')</span></a>';
	}
	return $out;
});
add_action('pre_get_posts', function ($q) {
	if (!is_admin() || !$q->is_main_query() || $q->get('post_type') !== RVP_CPT) return;
	if (!empty($_GET['rvp_status'])) $q->set('meta_query', [['key' => '_rvp_status', 'value' => sanitize_key($_GET['rvp_status'])]]);
	// pesquisar também por nome/email/descrição
	if ($s = $q->get('s')) {
		$q->set('s', '');
		$q->set('meta_query', [['relation' => 'OR',
			['key' => '_rvp_nome', 'value' => $s, 'compare' => 'LIKE'], ['key' => '_rvp_email', 'value' => $s, 'compare' => 'LIKE'],
			['key' => '_rvp_descricao', 'value' => $s, 'compare' => 'LIKE'], ['key' => '_rvp_marca', 'value' => $s, 'compare' => 'LIKE']]]);
	}
});

/* ---------- ecrã do pedido ---------- */
add_action('add_meta_boxes_' . RVP_CPT, function () {
	remove_meta_box('submitdiv', RVP_CPT, 'side');
	add_meta_box('rvp_details', 'Detalhes do pedido', 'rvp_box_details', RVP_CPT, 'normal', 'high');
	add_meta_box('rvp_quote', 'Orçamento e estado', 'rvp_box_quote', RVP_CPT, 'side', 'high');
	add_meta_box('rvp_log', 'Histórico', 'rvp_box_log', RVP_CPT, 'normal', 'low');
});

function rvp_box_details($post): void {
	$id = $post->ID;
	echo '<div class="rvp-admin-head"><span class="rvp-pill rvp-pill--' . esc_attr(rvp_status($id)) . '">' . esc_html(rvp_status_label(rvp_status($id))) . '</span>'
		. '<span>Pedido <b>#' . (int) $id . '</b> · recebido a ' . esc_html(get_the_date('j M Y, H:i', $post)) . '</span></div>';
	echo '<table class="rvp-table">';
	foreach (rvp_fields() as $k => $label) {
		$v = rvp_get($id, $k);
		if ($v === '') continue;
		if ($k === 'email') $v = '<a href="mailto:' . esc_attr($v) . '">' . esc_html($v) . '</a>';
		else $v = nl2br(esc_html($v));
		echo '<tr><th>' . esc_html($label) . '</th><td>' . $v . '</td></tr>';
	}
	$uid = (int) rvp_get($id, 'user_id', 0);
	echo '<tr><th>Conta</th><td>' . ($uid ? '<a href="' . esc_url(get_edit_user_link($uid)) . '">' . esc_html(get_userdata($uid)->display_name ?? '#' . $uid) . '</a>' : 'Sem conta (o cliente não pode aceitar online até criar conta com este email)') . '</td></tr>';
	$files = (array) rvp_get($id, 'files', []);
	if ($files) {
		echo '<tr><th>Ficheiros</th><td>';
		foreach ($files as $f) echo '<a class="button" href="' . esc_url($f['url']) . '" target="_blank" rel="noopener">📎 ' . esc_html($f['name']) . '</a> ';
		echo '</td></tr>';
	}
	if ($oid = (int) rvp_get($id, 'order_id', 0)) {
		$o = wc_get_order($oid);
		echo '<tr><th>Encomenda</th><td><a href="' . esc_url($o ? $o->get_edit_order_url() : '#') . '">#' . $oid . '</a>' . ($o ? ' · ' . esc_html(wc_get_order_status_name($o->get_status())) : '') . '</td></tr>';
	}
	echo '</table>';
}

function rvp_box_quote($post): void {
	$id = $post->ID;
	$s = rvp_status($id);
	wp_nonce_field('rvp_save_' . $id, '_rvp_admin_nonce');
	$price = rvp_get($id, 'quote_price');
	echo '<div class="rvp-quote-box">';
	echo '<p><label for="rvp_quote_price"><b>Valor do orçamento (€)</b></label><input type="number" step="0.01" min="0" id="rvp_quote_price" name="rvp_quote_price" value="' . esc_attr($price) . '" placeholder="0,00">' . (rvp_get($id, 'estimativa') ? '<span class="rvp-muted">Estimativa do site: ' . esc_html(rvp_get($id, 'estimativa')) . '</span>' : '') . '</p>';
	echo '<p><label for="rvp_quote_days"><b>Prazo de produção (dias úteis)</b></label><input type="number" min="1" id="rvp_quote_days" name="rvp_quote_days" value="' . esc_attr(rvp_get($id, 'quote_days', '5')) . '"></p>';
	echo '<p><label for="rvp_quote_message"><b>Mensagem para o cliente</b></label><textarea id="rvp_quote_message" name="rvp_quote_message" rows="5" placeholder="Ex.: material escolhido, observações técnicas…">' . esc_textarea(rvp_get($id, 'quote_message')) . '</textarea></p>';
	echo '<p><label for="rvp_status"><b>Estado</b></label><select id="rvp_status" name="rvp_status">';
	foreach (rvp_statuses() as $k => [$label]) echo '<option value="' . esc_attr($k) . '"' . selected($s, $k, false) . '>' . esc_html($label) . '</option>';
	echo '</select></p>';
	echo '<p><label><input type="checkbox" name="rvp_notify" value="1" checked> Avisar o cliente por email</label></p>';
	echo '<div class="rvp-quote-buttons">';
	if (in_array($s, ['novo', 'analise'], true)) echo '<button class="button button-primary button-large" name="rvp_send_quote" value="1">Enviar orçamento</button>';
	echo '<button class="button button-large" name="rvp_save" value="1">Guardar</button></div>';
	echo '<p class="rvp-muted">"Enviar orçamento" guarda o valor, muda o estado para <i>Orçamento enviado</i> e o cliente pode aceitá-lo em A minha conta → Pedidos.</p>';
	echo '</div>';
}

function rvp_box_log($post): void {
	$log = array_reverse((array) rvp_get($post->ID, 'log', []));
	if (!$log) { echo '<p class="rvp-muted">Sem histórico.</p>'; return; }
	echo '<ol class="rvp-log">';
	foreach ($log as $e) {
		$by = !empty($e['by']) ? get_userdata((int) $e['by']) : null;
		echo '<li><b>' . esc_html(rvp_status_label($e['to'] ?? '')) . '</b> <span class="rvp-muted">' . esc_html(wp_date('j M Y, H:i', (int) ($e['t'] ?? 0))) . ($by ? ' · ' . esc_html($by->display_name) : '') . '</span>'
			. (!empty($e['note']) ? '<br>' . esc_html($e['note']) : '') . '</li>';
	}
	echo '</ol>';
}

add_action('save_post_' . RVP_CPT, function ($id) {
	if (defined('DOING_AUTOSAVE') && DOING_AUTOSAVE) return;
	if (!isset($_POST['_rvp_admin_nonce']) || !wp_verify_nonce($_POST['_rvp_admin_nonce'], 'rvp_save_' . $id) || !current_user_can('edit_post', $id)) return;

	$price = isset($_POST['rvp_quote_price']) && $_POST['rvp_quote_price'] !== '' ? round((float) str_replace(',', '.', wp_unslash($_POST['rvp_quote_price'])), 2) : '';
	rvp_set($id, 'quote_price', $price);
	rvp_set($id, 'quote_days', absint($_POST['rvp_quote_days'] ?? 0) ?: '');
	rvp_set($id, 'quote_message', sanitize_textarea_field(wp_unslash($_POST['rvp_quote_message'] ?? '')));

	$old = rvp_status($id);
	$new = sanitize_key($_POST['rvp_status'] ?? $old);
	if (!empty($_POST['rvp_send_quote'])) {
		if ($price === '' || $price <= 0) {
			set_transient('rvp_notice_' . get_current_user_id(), 'Indique o valor do orçamento antes de o enviar.', 30);
			return;
		}
		$new = 'orcamento';
		rvp_set($id, 'quote_date', time());
	}
	if (array_key_exists($new, rvp_statuses()) && $new !== $old) {
		rvp_set_status($id, $new, $new === 'orcamento' ? 'Orçamento de ' . rvp_money($price) : 'Alterado pela equipa');
		if (!empty($_POST['rvp_notify'])) rvp_notify_customer($id, $new);
	}
});

add_action('admin_notices', function () {
	$k = 'rvp_notice_' . get_current_user_id();
	if ($msg = get_transient($k)) { delete_transient($k); echo '<div class="notice notice-error"><p>' . esc_html($msg) . '</p></div>'; }
});
add_filter('post_updated_messages', function ($m) {
	$m[RVP_CPT] = array_fill(0, 11, 'Pedido atualizado.');
	return $m;
});

function rvp_notify_customer(int $id, string $status): void {
	$email = rvp_get($id, 'email');
	if (!$email) return;
	$url = rvp_account_url($id);
	$nome = esc_html(rvp_get($id, 'nome'));
	if ($status === 'orcamento') {
		$body = "<p>Olá $nome,</p><p>O orçamento para o seu pedido <b>#$id</b> está pronto:</p>"
			. '<p style="font-size:28px;font-weight:800;color:#F2611D;margin:8px 0">' . esc_html(rvp_money(rvp_get($id, 'quote_price'))) . '</p>'
			. (rvp_get($id, 'quote_days') ? '<p>Prazo de produção: ' . (int) rvp_get($id, 'quote_days') . ' dias úteis.</p>' : '')
			. (rvp_get($id, 'quote_message') ? '<p>' . nl2br(esc_html(rvp_get($id, 'quote_message'))) . '</p>' : '');
		rvp_mail($email, "Orçamento do pedido #$id — Revivo", 'O seu orçamento está pronto', $body, 'Ver e aceitar orçamento', $url);
	} else {
		$body = "<p>Olá $nome,</p><p>O estado do seu pedido <b>#$id</b> mudou para <b>" . esc_html(rvp_status_label($status)) . '</b>.</p><p>' . esc_html(rvp_statuses()[$status][1] ?? '') . '</p>';
		rvp_mail($email, "Pedido #$id: " . rvp_status_label($status) . ' — Revivo', 'Atualização do pedido', $body, 'Ver pedido', $url);
	}
}

/* ---------- resumo no painel do WordPress ---------- */
add_action('wp_dashboard_setup', function () {
	wp_add_dashboard_widget('rvp_dashboard', 'Pedidos de peças', function () {
		echo '<div class="rvp-dash-widget">';
		foreach (['novo', 'analise', 'orcamento', 'aceite', 'producao'] as $k) {
			$n = (new WP_Query(['post_type' => RVP_CPT, 'post_status' => 'publish', 'fields' => 'ids', 'posts_per_page' => -1, 'meta_query' => [['key' => '_rvp_status', 'value' => $k]]]))->found_posts;
			echo '<a href="' . esc_url(admin_url('edit.php?post_type=' . RVP_CPT . '&rvp_status=' . $k)) . '"><b>' . (int) $n . '</b><span>' . esc_html(rvp_status_label($k)) . '</span></a>';
		}
		echo '</div>';
	});
});
