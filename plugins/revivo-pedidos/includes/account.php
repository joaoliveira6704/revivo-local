<?php
/**
 * Área de cliente: separador "Pedidos" em A minha conta (lista, detalhe, aceitar/recusar orçamento).
 */
defined('ABSPATH') || exit;

add_action('init', function () {
	add_rewrite_endpoint('pedidos', EP_ROOT | EP_PAGES);
	// garante as regras depois de atualizar o plugin
	if (get_option('rvp_rewrite_version') !== RVP_VERSION) {
		flush_rewrite_rules(false);
		update_option('rvp_rewrite_version', RVP_VERSION);
	}
});
add_filter('woocommerce_get_query_vars', function ($vars) { $vars['pedidos'] = 'pedidos'; return $vars; });
add_filter('woocommerce_endpoint_pedidos_title', fn() => 'Pedidos de peças');

/** Item do menu logo a seguir a "Encomendas", com contador de orçamentos por responder. */
add_filter('woocommerce_account_menu_items', function ($items) {
	$new = [];
	foreach ($items as $k => $label) {
		$new[$k] = $label;
		if ($k === 'orders') $new['pedidos'] = 'Pedidos de peças';
	}
	if (!isset($new['pedidos'])) $new = ['pedidos' => 'Pedidos de peças'] + $new;
	return $new;
});
add_filter('woocommerce_account_menu_item_classes', function ($classes, $endpoint) {
	if ($endpoint === 'pedidos' && is_user_logged_in()) {
		foreach (rvp_user_requests(get_current_user_id()) as $p) {
			if (rvp_status($p->ID) === 'orcamento') { $classes[] = 'rvp-has-quote'; break; }
		}
	}
	return $classes;
}, 10, 2);

/** Aceitar / recusar orçamento. */
add_action('template_redirect', function () {
	if (empty($_POST['rvp_action']) || !is_user_logged_in()) return;
	$id = absint($_POST['rvp_id'] ?? 0);
	$uid = get_current_user_id();
	if (!wp_verify_nonce($_POST['_rvp_nonce'] ?? '', 'rvp_quote_' . $id) || !rvp_user_can_view($id, $uid)) {
		wc_add_notice('Não foi possível processar o pedido. Tente novamente.', 'error');
		return;
	}
	if (rvp_status($id) !== 'orcamento') return;

	if ($_POST['rvp_action'] === 'recusar') {
		rvp_set_status($id, 'recusado', 'Recusado pelo cliente');
		wc_add_notice('Orçamento recusado. Obrigado pela resposta.', 'notice');
		wp_safe_redirect(rvp_account_url($id));
		exit;
	}

	// aceitar → encomenda WooCommerce com o valor do orçamento
	$price = (float) rvp_get($id, 'quote_price', 0);
	$order = wc_create_order(['customer_id' => $uid]);
	$fee = new WC_Order_Item_Fee();
	$fee->set_name(sprintf('Peça à medida — Pedido #%d', $id));
	$fee->set_amount($price);
	$fee->set_total($price);
	$fee->set_tax_status('none');
	$order->add_item($fee);
	$customer = new WC_Customer($uid);
	$order->set_address($customer->get_billing(), 'billing');
	$order->set_address($customer->get_shipping(), 'shipping');
	if (!$order->get_billing_email()) $order->set_billing_email(rvp_get($id, 'email'));
	$order->update_meta_data('_rvp_request', $id);
	$order->calculate_totals(false);
	$order->update_status('pending', sprintf('Criada a partir do orçamento do pedido de peça #%d.', $id));
	$order->save();
	rvp_set($id, 'order_id', $order->get_id());
	rvp_set_status($id, 'aceite', 'Aceite pelo cliente — encomenda #' . $order->get_id());
	wp_safe_redirect($order->get_checkout_payment_url());
	exit;
});

/** Pagamento confirmado → em produção; encomenda concluída → pedido concluído. */
add_action('woocommerce_order_status_changed', function ($order_id, $from, $to, $order) {
	$id = (int) $order->get_meta('_rvp_request');
	if (!$id) return;
	if ($to === 'processing' && rvp_status($id) === 'aceite') rvp_set_status($id, 'producao', 'Pagamento recebido');
	if ($to === 'completed') rvp_set_status($id, 'concluido', 'Encomenda concluída');
	if ($to === 'cancelled') rvp_set_status($id, 'cancelado', 'Encomenda cancelada');
}, 10, 4);

/* ------------------------------------------------------------------ apresentação */

function rvp_badge(string $s): string {
	return '<span class="rv-badge rvp-badge rvp-badge--' . esc_attr($s) . '">' . esc_html(rvp_status_label($s)) . '</span>';
}

function rvp_progress(string $s): string {
	$flow = rvp_flow();
	$labels = ['novo' => 'Recebido', 'analise' => 'Análise', 'orcamento' => 'Orçamento', 'aceite' => 'Aceite', 'producao' => 'Produção', 'enviado' => 'Enviado', 'concluido' => 'Concluído'];
	$idx = array_search($s, $flow, true);
	if ($idx === false) return '<div class="rvp-progress is-stopped">' . rvp_badge($s) . '</div>';
	$out = '<ol class="rvp-progress" style="--rvp-p:' . round($idx / (count($flow) - 1) * 100) . '%">';
	foreach ($flow as $i => $k) {
		$cls = $i < $idx ? 'is-done' : ($i === $idx ? 'is-current' : '');
		$out .= '<li class="' . $cls . '"' . ($i === $idx ? ' aria-current="step"' : '') . '><span></span><em>' . esc_html($labels[$k]) . '</em></li>';
	}
	return $out . '</ol>';
}

add_action('woocommerce_account_pedidos_endpoint', function () {
	$uid = get_current_user_id();
	$id = absint($_GET['pedido'] ?? 0);
	if ($id) {
		if (!rvp_user_can_view($id, $uid)) {
			echo '<div class="woocommerce-error">Este pedido não existe ou não pertence à sua conta.</div>';
			return;
		}
		rvp_render_detail($id);
		return;
	}
	rvp_render_list($uid);
});

function rvp_render_list(int $uid): void {
	$reqs = rvp_user_requests($uid);
	$new_url = get_permalink(get_page_by_path('pedir-peca')) ?: home_url('/');
	echo '<div class="rvp">';
	echo '<div class="rvp-head"><div><p class="rv-dash-k">Peças à medida</p><h2>Os seus pedidos</h2></div>'
		. '<a class="rv-dash-btn" href="' . esc_url($new_url) . '">Novo pedido</a></div>';
	if (!$reqs) {
		echo '<div class="rvp-empty"><span class="rvp-empty-ico" aria-hidden="true">✦</span><b>Ainda não fez nenhum pedido de peça.</b>'
			. '<p>Diga-nos que peça partiu — nós modelamos, imprimimos e enviamos um orçamento sem compromisso.</p>'
			. '<a class="rv-dash-btn" href="' . esc_url($new_url) . '">Pedir uma peça</a></div></div>';
		return;
	}
	echo '<ul class="rvp-list">';
	foreach ($reqs as $p) {
		$s = rvp_status($p->ID);
		$price = rvp_get($p->ID, 'quote_price');
		echo '<li class="rvp-card' . ($s === 'orcamento' ? ' has-quote' : '') . '"><a href="' . esc_url(rvp_account_url($p->ID)) . '">';
		echo '<div class="rvp-card-top"><span class="rvp-num">#' . (int) $p->ID . '</span>' . rvp_badge($s) . '</div>';
		echo '<b class="rvp-title">' . esc_html(get_the_title($p)) . '</b>';
		echo '<span class="rvp-meta">' . esc_html(get_the_date('j M Y', $p)) . ' · ' . esc_html(rvp_get($p->ID, 'tipo', 'Pedido')) . ' · ' . esc_html(rvp_get($p->ID, 'material', '—')) . '</span>';
		echo rvp_progress($s);
		echo '<div class="rvp-card-foot">' . ($price !== '' ? '<span class="rvp-price"><small>Orçamento</small>' . esc_html(rvp_money($price)) . '</span>' : '<span class="rvp-price is-pending"><small>Orçamento</small>a aguardar</span>')
			. '<span class="rvp-open">' . ($s === 'orcamento' ? 'Responder ao orçamento' : 'Ver pedido') . ' →</span></div>';
		echo '</a></li>';
	}
	echo '</ul></div>';
}

function rvp_render_detail(int $id): void {
	$s = rvp_status($id);
	$st = rvp_statuses();
	$price = rvp_get($id, 'quote_price');
	echo '<div class="rvp rvp-detail">';
	echo '<a class="rvp-back" href="' . esc_url(rvp_account_url()) . '">← Todos os pedidos</a>';
	echo '<div class="rvp-head"><div><p class="rv-dash-k">Pedido #' . (int) $id . ' · ' . esc_html(get_the_date('j \d\e F \d\e Y', $id)) . '</p><h2>' . esc_html(get_the_title($id)) . '</h2></div>' . rvp_badge($s) . '</div>';
	echo rvp_progress($s);
	echo '<p class="rvp-status-text">' . esc_html($st[$s][1] ?? '') . '</p>';

	// orçamento
	if ($price !== '') {
		$days = rvp_get($id, 'quote_days');
		$msg = rvp_get($id, 'quote_message');
		echo '<section class="rvp-quote"><div class="rvp-quote-main"><p class="rv-dash-k">Orçamento</p><div class="rvp-quote-price">' . esc_html(rvp_money($price)) . '</div>'
			. '<p class="rvp-quote-sub">' . ($days ? 'Prazo de produção: ' . (int) $days . ' dias úteis' : '') . (rvp_get($id, 'quote_date') ? ' · enviado a ' . esc_html(wp_date('j M Y', (int) rvp_get($id, 'quote_date'))) : '') . '</p></div>';
		if ($msg) echo '<blockquote class="rvp-quote-msg">' . wpautop(esc_html($msg)) . '</blockquote>';
		if ($s === 'orcamento') {
			echo '<form method="post" class="rvp-quote-actions">' . wp_nonce_field('rvp_quote_' . $id, '_rvp_nonce', true, false)
				. '<input type="hidden" name="rvp_id" value="' . (int) $id . '">'
				. '<button class="rvp-accept" name="rvp_action" value="aceitar">Aceitar e pagar ' . esc_html(rvp_money($price)) . '</button>'
				. '<button class="rvp-decline" name="rvp_action" value="recusar" onclick="return confirm(\'Recusar este orçamento?\')">Recusar</button></form>';
		}
		$oid = (int) rvp_get($id, 'order_id', 0);
		if ($oid && ($order = wc_get_order($oid))) {
			if ($order->needs_payment()) echo '<div class="rvp-quote-actions"><a class="rvp-accept" href="' . esc_url($order->get_checkout_payment_url()) . '">Pagar encomenda #' . $oid . '</a></div>';
			else echo '<p class="rvp-quote-sub">Encomenda <a href="' . esc_url($order->get_view_order_url()) . '">#' . $oid . '</a> · ' . esc_html(wc_get_order_status_name($order->get_status())) . '</p>';
		}
		echo '</section>';
	} elseif (!in_array($s, ['cancelado', 'recusado'], true)) {
		echo '<section class="rvp-quote is-waiting"><p class="rv-dash-k">Orçamento</p><b>Em preparação</b><p class="rvp-quote-sub">' . (rvp_get($id, 'estimativa') ? 'Estimativa do site: ' . esc_html(rvp_get($id, 'estimativa')) . '. ' : '') . 'Avisamos por email quando estiver pronto.</p></section>';
	}

	// detalhes
	echo '<section class="rvp-section"><h3>Detalhes do pedido</h3><dl class="rvp-dl">';
	foreach (rvp_fields() as $k => $label) {
		if (in_array($k, ['nome', 'email'], true)) continue;
		$v = rvp_get($id, $k);
		if ($v === '') continue;
		echo '<div' . ($k === 'descricao' ? ' class="is-wide"' : '') . '><dt>' . esc_html($label) . '</dt><dd>' . nl2br(esc_html($v)) . '</dd></div>';
	}
	echo '</dl>';
	$files = (array) rvp_get($id, 'files', []);
	if ($files) {
		echo '<div class="rvp-files">';
		foreach ($files as $f) echo '<a href="' . esc_url($f['url']) . '" target="_blank" rel="noopener">📎 ' . esc_html($f['name']) . '</a>';
		echo '</div>';
	}
	echo '</section>';

	// histórico
	$log = array_reverse((array) rvp_get($id, 'log', []));
	if ($log) {
		echo '<section class="rvp-section"><h3>Histórico</h3><ol class="rvp-timeline">';
		foreach ($log as $e) {
			echo '<li><b>' . esc_html(rvp_status_label($e['to'] ?? '')) . '</b><span>' . esc_html(wp_date('j M Y, H:i', (int) ($e['t'] ?? 0))) . '</span>'
				. (!empty($e['note']) ? '<p>' . esc_html($e['note']) . '</p>' : '') . '</li>';
		}
		echo '</ol></section>';
	}
	echo '</div>';
}
