<?php
/**
 * Captura dos pedidos enviados pelo formulário "Pedir peça" (Contact Form 7).
 * O formulário é reconhecido por ter os campos "descricao" e "medidas".
 */
defined('ABSPATH') || exit;

function rvp_is_request_form($contact_form): bool {
	if (!is_object($contact_form) || !method_exists($contact_form, 'scan_form_tags')) return false;
	$names = wp_list_pluck($contact_form->scan_form_tags(), 'name');
	return in_array('descricao', $names, true) && in_array('medidas', $names, true);
}

/** Guarda o pedido antes de o CF7 enviar o email (os ficheiros ainda existem nesta fase). */
add_action('wpcf7_before_send_mail', function ($contact_form, &$abort, $submission) {
	if (!rvp_is_request_form($contact_form) || !$submission) return;
	$data = $submission->get_posted_data();
	$val = function ($k) use ($data) {
		$v = $data[$k] ?? '';
		if (is_array($v)) $v = implode(', ', array_filter($v));
		return $k === 'descricao' ? sanitize_textarea_field($v) : sanitize_text_field($v);
	};

	$user_id = get_current_user_id();
	$email = sanitize_email($val('email'));
	if (!$user_id && $email && ($u = get_user_by('email', $email))) $user_id = $u->ID; // associa à conta com o mesmo email

	$title = trim(($val('marca') ? $val('marca') . ' ' : '') . ($val('modelo') ?: '')) ?: wp_trim_words($val('descricao'), 8, '…');
	$id = wp_insert_post([
		'post_type' => RVP_CPT, 'post_status' => 'publish',
		'post_title' => $title ?: 'Pedido de peça', 'post_author' => $user_id ?: 0,
	], true);
	if (is_wp_error($id)) return;

	foreach (array_keys(rvp_fields()) as $k) {
		if ($k === 'estimativa') continue;
		rvp_set($id, $k, $k === 'email' ? $email : $val($k));
	}
	// estimativa calculada no site (campo escondido acrescentado por este plugin)
	if (!empty($_POST['estimativa'])) rvp_set($id, 'estimativa', sanitize_text_field(wp_unslash($_POST['estimativa'])));
	rvp_set($id, 'user_id', $user_id);
	rvp_set($id, 'status', 'novo');
	rvp_set($id, 'log', [['t' => time(), 'from' => '', 'to' => 'novo', 'note' => 'Pedido recebido pelo site', 'by' => $user_id]]);

	// ficheiros: copiar para uploads/revivo-pedidos/<pasta aleatória>/
	$files = [];
	foreach ((array) $submission->uploaded_files() as $paths) {
		foreach ((array) $paths as $path) {
			if (!is_file($path)) continue;
			$up = wp_upload_dir();
			$dir = trailingslashit($up['basedir']) . 'revivo-pedidos/' . $id . '-' . wp_generate_password(10, false);
			wp_mkdir_p($dir);
			$name = sanitize_file_name(basename($path));
			if (@copy($path, "$dir/$name")) {
				$files[] = ['name' => $name, 'url' => str_replace($up['basedir'], $up['baseurl'], "$dir/$name")];
			}
		}
	}
	rvp_set($id, 'files', $files);

	$GLOBALS['rvp_last_request'] = $id;
	do_action('rvp_request_created', $id);
}, 10, 3);

/** Mensagem de sucesso com o número do pedido. */
add_filter('wpcf7_display_message', function ($message, $status) {
	if ($status === 'mail_sent_ok' && !empty($GLOBALS['rvp_last_request'])) {
		$id = (int) $GLOBALS['rvp_last_request'];
		$message = sprintf('Pedido #%d recebido! Vamos analisá-lo e enviar-lhe um orçamento.', $id)
			. (is_user_logged_in() ? ' Pode acompanhá-lo em A minha conta → Pedidos.' : '');
	}
	return $message;
}, 10, 2);

/** Email de confirmação ao cliente. */
add_action('rvp_request_created', function ($id) {
	$email = rvp_get($id, 'email');
	if (!$email) return;
	$body = '<p>Olá ' . esc_html(rvp_get($id, 'nome')) . ',</p><p>Recebemos o seu pedido <b>#' . (int) $id . '</b>. A equipa vai analisar a peça e enviar-lhe um orçamento, normalmente em 1 a 2 dias úteis.</p>'
		. (rvp_get($id, 'estimativa') ? '<p>Estimativa indicada no site: <b>' . esc_html(rvp_get($id, 'estimativa')) . '</b></p>' : '');
	$has_account = (int) rvp_get($id, 'user_id', 0) > 0;
	rvp_mail($email, 'Recebemos o seu pedido #' . $id . ' — Revivo', 'Pedido recebido', $body,
		$has_account ? 'Acompanhar o pedido' : '', $has_account ? rvp_account_url($id) : '');
});

/** Campo escondido "estimativa" (preenchido pelo script da página) e aviso sobre o acompanhamento. */
add_filter('wpcf7_form_hidden_fields', function ($fields) {
	$cf = function_exists('wpcf7_get_current_contact_form') ? wpcf7_get_current_contact_form() : null;
	if ($cf && rvp_is_request_form($cf)) $fields['estimativa'] = '';
	return $fields;
});
add_filter('wpcf7_form_elements', function ($html) {
	$cf = function_exists('wpcf7_get_current_contact_form') ? wpcf7_get_current_contact_form() : null;
	if (!$cf || !rvp_is_request_form($cf)) return $html;
	if (is_user_logged_in()) {
		$note = '<div class="rv-ped-note is-in"><b>Sessão iniciada.</b> Vai poder acompanhar este pedido e o orçamento em <a href="' . esc_url(rvp_account_url()) . '">A minha conta → Pedidos</a>.</div>';
	} else {
		$login = function_exists('wc_get_page_permalink') ? wc_get_page_permalink('myaccount') : wp_login_url();
		$note = '<div class="rv-ped-note"><b>Dica:</b> <a href="' . esc_url($login) . '">inicie sessão ou crie conta</a> para acompanhar o pedido e aceitar o orçamento online.</div>';
	}
	return $note . $html;
});

/** Nome completo de quem tem sessão iniciada: perfil → faturação WooCommerce → nome público. */
function rvp_user_full_name(WP_User $u): string {
	$name = trim($u->first_name . ' ' . $u->last_name);
	if ($name === '') $name = trim(get_user_meta($u->ID, 'billing_first_name', true) . ' ' . get_user_meta($u->ID, 'billing_last_name', true));
	return $name !== '' ? $name : $u->display_name;
}

/** Pré-preenche nome e email de quem tem sessão iniciada (o nome chega ao campo como atributo do shortcode). */
add_filter('shortcode_atts_wpcf7', function ($out) {
	if (is_user_logged_in()) $out['nome'] = rvp_user_full_name(wp_get_current_user());
	return $out;
});
add_filter('wpcf7_form_tag', function ($tag) {
	if (!is_user_logged_in() || empty($tag['name'])) return $tag;
	if ($tag['name'] === 'nome') $tag['options'][] = 'default:shortcode_attr';
	if ($tag['name'] === 'email') $tag['options'][] = 'default:user_email';
	return $tag;
});
