<?php
/**
 * Plugin Name:       Revivo Pedidos
 * Description:       Pedidos de peças à medida: guarda os pedidos do formulário "Pedir peça", mostra-os ao cliente em "A minha conta → Pedidos" e permite à equipa enviar orçamentos. Ao aceitar, é criada uma encomenda WooCommerce para pagamento.
 * Version:           1.0.1
 * Author:            Revivo — Grupo 6 (TDW · ESMAD)
 * Requires at least: 6.5
 * Requires PHP:      8.0
 * Text Domain:       revivo-pedidos
 */

defined('ABSPATH') || exit;

define('RVP_VERSION', '1.0.1');
define('RVP_FILE', __FILE__);
define('RVP_DIR', plugin_dir_path(__FILE__));
define('RVP_URL', plugin_dir_url(__FILE__));

require_once RVP_DIR . 'includes/model.php';
require_once RVP_DIR . 'includes/capture.php';
require_once RVP_DIR . 'includes/account.php';
require_once RVP_DIR . 'includes/admin.php';

register_activation_hook(__FILE__, function () {
	rvp_register_cpt();
	add_rewrite_endpoint('pedidos', EP_ROOT | EP_PAGES);
	flush_rewrite_rules();
});
register_deactivation_hook(__FILE__, 'flush_rewrite_rules');
