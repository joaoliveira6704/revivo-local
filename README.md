# Revivo — cópia local do site WordPress

Cópia do site [Revivo](https://trabalhos.esmad.ipp.pt/~tdw/26-27/nec/wp-group06/) em Docker, para fazer
alterações sem risco e depois enviá-las para o site real.

| | |
|---|---|
| Site local | http://localhost:8080 |
| WP-Admin local | http://localhost:8080/wp-admin (mesmo utilizador do site real) |
| phpMyAdmin | http://localhost:8081 |

## Arrancar / parar

```bash
docker compose up -d      # arrancar (o Docker Desktop tem de estar aberto)
docker compose stop       # parar
```

WP-CLI: `docker compose run --rm cli wp <comando>` (ex.: `wp plugin list`).

## Fluxo de trabalho

1. Faz as alterações no site local (Editor do Site, páginas, CSS adicional…).
2. Vê o que mudou em relação ao site real:
   ```bash
   ./push.sh diff                  # lista
   ./push.sh diff page pedir-peca  # linha a linha
   ```
3. Envia:
   ```bash
   ./push.sh css                   # Global Styles / CSS adicional
   ./push.sh part header           # template parts (header, footer…)
   ./push.sh template page         # templates
   ./push.sh page pedir-peca       # páginas
   ./push.sh all                   # tudo o que estiver diferente
   ```

O script troca `http://localhost:8080` pelo endereço real, guarda a versão do site real em
`backups/<data-hora>/` antes de escrever e pede confirmação (`-y` para não perguntar).

**Não é enviado pelo script:** produtos e encomendas WooCommerce, media, menus `wp_navigation`,
formulários Contact Form 7, definições de plugins e utilizadores. Isso faz-se no WP-Admin do site real.

## Design (Revivo 2.0)

O design vive em ficheiros em `design/` e aplica-se ao site local com um comando:

```bash
python3 -I design/apply.py              # tudo
python3 -I design/apply.py css          # só CSS
python3 -I design/apply.py js           # só JS (vai para o footer)
python3 -I design/apply.py templates    # loja, produto, carrinho, checkout
```

| Ficheiro | O quê |
|---|---|
| `design/custom.original.css` | CSS original do site (base, não mexer) |
| `design/revivo-v2.css` | camada 2.0: tokens, header flutuante, hero, cartões, animações, modo escuro |
| `design/revivo-shop.css` | loja, filtros, produto, carrinho, checkout, "A minha conta" |
| `design/revivo.js` | interações: progresso, header, luz nos cartões, contadores, animações, −/+ quantidade, painel de cliente |
| `design/templates/*.html` | templates WooCommerce (catálogo com filtros, produto, carrinho, checkout) |
| `design/demo/` | produtos de demonstração **só para o local** (`seed.php`, imagens) |

Depois de aplicar: `./push.sh diff` e `./push.sh all` (ou um a um) para enviar para o site real.

**Só no site local:** os 13 produtos de demonstração, o atributo "Material", o cliente de teste
(`cliente.demo`, senha no `.env`) com 2 encomendas, e o modo "Brevemente" da loja desligado.

## Plugin "Revivo Pedidos" (pedidos de peças + orçamentos)

Código em `plugins/revivo-pedidos/` (montado no Docker). Guarda cada pedido do formulário "Pedir peça",
mostra-o ao cliente em **A minha conta → Pedidos de peças** (estado, progresso, orçamento, aceitar/recusar) e
dá à equipa o menu **Pedidos de peças** no WP-Admin (lista, filtros por estado, detalhe, caixa de orçamento
com email ao cliente). Ao aceitar, é criada uma encomenda WooCommerce para pagamento.

Para o site real: `dist/revivo-pedidos.zip` → WP-Admin → Plugins → Adicionar → Carregar plugin → Ativar.
Refazer o zip: `cd plugins && zip -r ../dist/revivo-pedidos.zip revivo-pedidos`

## Publicar no site real (ordem recomendada)

1. Carregar e ativar `dist/revivo-pedidos.zip` (a área de pedidos depende dele).
2. `./push.sh all` — CSS, header/footer (logótipo, pesquisa, JS), páginas (inclui as legais) e templates da loja.
3. No WP-Admin real (não é enviado pelo script):
   - **Definições → Privacidade:** escolher "Política de Privacidade".
   - **WooCommerce → Definições → Avançado:** página de Termos = "Termos e Condições".
   - **WooCommerce → Pagamentos:** títulos em português (Transferência bancária, Cheque, Pagamento na entrega).
   - **Aparência → Editor → Identidade do site:** novo ícone (`design/brand/mark-512.png`).
   - **WooCommerce → Definições → Visibilidade do site:** desligar "Brevemente" se a loja deve ficar visível.

## Identidade visual

`design/brand/`: símbolo (`mark.svg`, `mark-512.png`), logótipos horizontal/negativo/monocromático e o guia
`brand.html` (cores, tipografia, regras de utilização).

## Só no site local

- `wordpress/wp-content/mu-plugins/local-mail-log.php`: em vez de enviar emails, guarda-os em
  `wordpress/wp-content/rv-mail/` (para ver os emails do plugin). **Não copiar para o site real.**
- Produtos, avaliações, cliente e encomendas de demonstração; pedido de peça #176 de teste.

## Atualizar a cópia local

Se o site real mudar, faz um novo export no Duplicator (WP-Admin real → Duplicator → Backups), coloca o
`*_installer.php` e o `*_archive.daf` em `wordpress/` e abre `http://localhost:8080/<nome>_installer.php`
(base de dados: host `db`, nome/utilizador/password `wordpress`). Depois apaga os ficheiros do installer.

## Ficheiros

- `docker-compose.yml`: WordPress + MariaDB + phpMyAdmin + WP-CLI
- `push.sh`, `tools/push.py`: envio para o site real (REST API)
- `.env`: credenciais do site real e do local (**não partilhar**, está no `.gitignore`)
- `config/harica-geant-tls-r1.pem`: certificado intermédio que o servidor da escola não envia
  (permite verificar o HTTPS em vez de o desligar)
- `import/`: exports do Duplicator · `backups/`: cópias do site real antes de cada envio
