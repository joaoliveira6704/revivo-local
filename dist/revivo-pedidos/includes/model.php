<?php
/**
 * Modelo: tipo de conteúdo "rv_pedido", estados e funções de acesso.
 */
defined('ABSPATH') || exit;

const RVP_CPT = 'rv_pedido';

/** Estados do pedido (chave => [rótulo, descrição para o cliente]). */
function rvp_statuses(): array {
	return [
		'novo'      => ['Recebido', 'Recebemos o seu pedido. A equipa vai analisá-lo em breve.'],
		'analise'   => ['Em análise', 'Estamos a estudar a peça e a escolher o material mais adequado.'],
		'orcamento' => ['Orçamento enviado', 'O orçamento está pronto. Aceite-o para avançarmos com a produção.'],
		'aceite'    => ['Orçamento aceite', 'Obrigado! Assim que o pagamento estiver confirmado começamos a produção.'],
		'producao'  => ['Em produção', 'A sua peça está a ser modelada e impressa.'],
		'enviado'   => ['Enviado', 'A encomenda foi expedida.'],
		'concluido' => ['Concluído', 'Pedido concluído. Obrigado por reparar em vez de substituir!'],
		'recusado'  => ['Orçamento recusado', 'Recusou o orçamento. Se quiser, envie-nos um novo pedido.'],
		'cancelado' => ['Cancelado', 'Este pedido foi cancelado.'],
	];
}

/** Ordem do progresso mostrado ao cliente. */
function rvp_flow(): array {
	return ['novo', 'analise', 'orcamento', 'aceite', 'producao', 'enviado', 'concluido'];
}

/** Campos guardados a partir do formulário (meta => rótulo). */
function rvp_fields(): array {
	return [
		'tipo' => 'Tipo de pedido', 'nome' => 'Nome', 'email' => 'Email', 'marca' => 'Marca do aparelho',
		'modelo' => 'Modelo', 'descricao' => 'Descrição', 'medidas' => 'Medidas', 'quantidade' => 'Quantidade',
		'material' => 'Material', 'cor' => 'Cor', 'acabamento' => 'Acabamento', 'estimativa' => 'Estimativa do site',
	];
}

add_action('init', 'rvp_register_cpt');
function rvp_register_cpt(): void {
	register_post_type(RVP_CPT, [
		'labels' => [
			'name' => 'Pedidos de peças', 'singular_name' => 'Pedido de peça', 'menu_name' => 'Pedidos de peças',
			'all_items' => 'Todos os pedidos', 'edit_item' => 'Pedido de peça', 'search_items' => 'Pesquisar pedidos',
			'not_found' => 'Ainda não há pedidos.', 'not_found_in_trash' => 'Não há pedidos no lixo.',
		],
		'public' => false, 'show_ui' => true, 'show_in_menu' => true, 'show_in_rest' => false,
		'menu_position' => 56, 'menu_icon' => 'dashicons-hammer', 'supports' => ['title'],
		'capability_type' => 'post', 'map_meta_cap' => true,
		'capabilities' => ['create_posts' => 'do_not_allow'], // os pedidos só chegam pelo formulário
	]);
}

function rvp_get(int $id, string $key, $default = '') {
	$v = get_post_meta($id, '_rvp_' . $key, true);
	return $v === '' || $v === null ? $default : $v;
}
function rvp_set(int $id, string $key, $value): void {
	update_post_meta($id, '_rvp_' . $key, $value);
}
function rvp_status(int $id): string {
	return rvp_get($id, 'status', 'novo');
}
function rvp_status_label(string $s): string {
	return rvp_statuses()[$s][0] ?? $s;
}
function rvp_money($v): string {
	return function_exists('wc_price') ? wp_strip_all_tags(wc_price((float) $v)) : number_format((float) $v, 2, ',', ' ') . ' €';
}

/** Muda o estado e guarda o histórico. */
function rvp_set_status(int $id, string $status, string $note = ''): void {
	$old = rvp_status($id);
	if ($old === $status) return;
	rvp_set($id, 'status', $status);
	$log = (array) rvp_get($id, 'log', []);
	$log[] = ['t' => time(), 'from' => $old, 'to' => $status, 'note' => $note, 'by' => get_current_user_id()];
	rvp_set($id, 'log', $log);
	do_action('rvp_status_changed', $id, $status, $old);
}

/** Pedidos de um utilizador (pela conta ou pelo email usado no formulário). */
function rvp_user_requests(int $user_id): array {
	$user = get_userdata($user_id);
	if (!$user) return [];
	$q = new WP_Query([
		'post_type' => RVP_CPT, 'post_status' => 'publish', 'posts_per_page' => 100, 'orderby' => 'date', 'order' => 'DESC',
		'meta_query' => ['relation' => 'OR',
			['key' => '_rvp_user_id', 'value' => $user_id],
			['key' => '_rvp_email', 'value' => $user->user_email],
		],
	]);
	return $q->posts;
}

/** O utilizador atual pode ver este pedido? */
function rvp_user_can_view(int $id, int $user_id): bool {
	if (get_post_type($id) !== RVP_CPT || !$user_id) return false;
	$user = get_userdata($user_id);
	return (int) rvp_get($id, 'user_id', 0) === $user_id || ($user && strcasecmp((string) rvp_get($id, 'email'), $user->user_email) === 0);
}

/** URL do pedido na área de cliente. */
function rvp_account_url(int $id = 0): string {
	$base = function_exists('wc_get_account_endpoint_url') ? wc_get_account_endpoint_url('pedidos') : home_url('/');
	return $id ? add_query_arg('pedido', $id, $base) : $base;
}

/** Email simples com o estilo da marca. */
function rvp_mail(string $to, string $subject, string $heading, string $body_html, string $cta_text = '', string $cta_url = ''): bool {
	$btn = $cta_url ? '<p style="margin:28px 0 0"><a href="' . esc_url($cta_url) . '" style="display:inline-block;background:#F2611D;color:#fff;text-decoration:none;font-weight:700;padding:12px 22px;border-radius:999px">' . esc_html($cta_text) . '</a></p>' : '';
	$html = '<div style="background:#FAF8F5;padding:32px 16px;font-family:Manrope,Helvetica,Arial,sans-serif;color:#15181C">'
		. '<div style="max-width:560px;margin:auto;background:#fff;border-radius:20px;padding:32px;border:1px solid #eee">'
		. '<p style="margin:0 0 20px;font-weight:800;font-size:22px;letter-spacing:-1px">revivo<span style="color:#F2611D">.</span></p>'
		. '<h1 style="font-size:24px;letter-spacing:-.5px;margin:0 0 12px">' . esc_html($heading) . '</h1>'
		. '<div style="font-size:15px;line-height:1.6;color:#4a5058">' . $body_html . '</div>' . $btn
		. '<p style="margin:32px 0 0;font-size:12px;color:#9aa1aa">Revivo — projeto académico (loja fictícia, sem transações reais).</p></div></div>';
	return wp_mail($to, $subject, $html, ['Content-Type: text/html; charset=UTF-8']);
}
