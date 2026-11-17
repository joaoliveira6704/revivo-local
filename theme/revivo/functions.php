<?php
/**
 * Revivo — funções do tema.
 *
 * O CSS e o JS do design vivem em ficheiros (assets/css, assets/js) em vez de
 * estarem na base de dados (Global Styles / bloco HTML no footer). Assim o
 * design edita-se como código e é versionado no git.
 *
 * @package Revivo
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

/**
 * Suportes do tema.
 */
function revivo_setup() {
	add_theme_support( 'wp-block-styles' );
	add_theme_support( 'responsive-embeds' );
	add_theme_support( 'post-thumbnails' );
	add_theme_support( 'editor-styles' );
	add_theme_support(
		'html5',
		array( 'search-form', 'comment-form', 'comment-list', 'gallery', 'caption', 'style', 'script' )
	);

	// Pré-visualização no editor com o mesmo CSS do site.
	add_editor_style(
		array(
			'assets/css/base.css',
			'assets/css/revivo.css',
			'assets/css/shop.css',
		)
	);

	// WooCommerce (a loja usa templates de bloco deste tema).
	add_theme_support( 'woocommerce' );
	add_theme_support( 'wc-product-gallery-zoom' );
	add_theme_support( 'wc-product-gallery-lightbox' );
	add_theme_support( 'wc-product-gallery-slider' );
}
add_action( 'after_setup_theme', 'revivo_setup' );

/**
 * CSS e JS do design.
 *
 * Prioridade 5 para o CSS sair antes dos estilos dos plugins (WooCommerce,
 * Contact Form 7, Complianz), tal como acontecia quando o CSS era injetado
 * nos Global Styles — que são impressos antes dos estilos dos plugins.
 */
function revivo_assets() {
	$version = wp_get_theme()->get( 'Version' );
	$uri     = get_stylesheet_directory_uri();

	wp_enqueue_style( 'revivo-base', $uri . '/assets/css/base.css', array(), $version );
	wp_enqueue_style( 'revivo', $uri . '/assets/css/revivo.css', array( 'revivo-base' ), $version );
	wp_enqueue_style( 'revivo-shop', $uri . '/assets/css/shop.css', array( 'revivo' ), $version );

	wp_enqueue_script( 'revivo', $uri . '/assets/js/revivo.js', array(), $version, true );
}
add_action( 'wp_enqueue_scripts', 'revivo_assets', 5 );
