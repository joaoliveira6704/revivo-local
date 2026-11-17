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

1. Faz as alterações no site local: **design em `theme/revivo/`** (ver secção seguinte), conteúdo de
   páginas no Editor do Site. Ver `python3 -I tools/theme-status.py` se o Editor do Site esconder ficheiros.
2. Vê o que mudou em relação ao site real:
   ```bash
   ./push.sh diff                  # lista
   ./push.sh diff page pedir-peca  # linha a linha
   ```
3. Envia:
   ```bash
   python3 -I tools/build-theme.py  # tema → dist/revivo-theme.zip (WP-Admin)
   ./push.sh page pedir-peca        # páginas
   ./push.sh all                    # tudo o que estiver diferente
   ```

O script troca `http://localhost:8080` pelo endereço real, guarda a versão do site real em
`backups/<data-hora>/` antes de escrever e pede confirmação (`-y` para não perguntar).

**Não é enviado pelo script:** o tema (vai por zip no WP-Admin), produtos e encomendas WooCommerce,
media, menus `wp_navigation`, formulários Contact Form 7, definições de plugins e utilizadores.
Isso faz-se no WP-Admin do site real.

## Design (tema `theme/revivo`)

O design é um **tema de blocos autónomo** em `theme/revivo`, montado no Docker em
`wp-content/themes/revivo`. Editas ficheiros, recarregas a página — não há nada a aplicar na base de dados.

```bash
docker compose up -d          # uma vez, para montar ./theme/revivo no container
# editar theme/revivo/... e recarregar http://localhost:8080
```

| Ficheiro | O quê |
|---|---|
| `theme/revivo/style.css` | metadata do tema (nome, versão) |
| `theme/revivo/theme.json` | paleta, tipografia (Manrope + Fira Code), estilos base |
| `theme/revivo/functions.php` | carrega o CSS/JS do tema e declara suporte WooCommerce |
| `theme/revivo/templates/*.html` | front-page, página, loja, produto, carrinho, checkout, pesquisa, 404… |
| `theme/revivo/parts/header.html`, `parts/footer.html` | cabeçalho (avisos, menu, pesquisa, tema claro/escuro) e rodapé |
| `theme/revivo/assets/css/base.css` | CSS original do site (base, não mexer) |
| `theme/revivo/assets/css/revivo.css` | camada 2.0: tokens, header flutuante, hero, cartões, animações, modo escuro |
| `theme/revivo/assets/css/shop.css` | loja, filtros, produto, carrinho, checkout, "A minha conta" |
| `theme/revivo/assets/js/revivo.js` | interações: progresso, header, luz nos cartões, contadores, animações, −/+ quantidade, painel de cliente |
| `theme/revivo/assets/fonts/` | Manrope e Fira Code (self-hosted, sem dependência do Twenty Twenty-Five) |

### Editar sem que a base de dados esconda os ficheiros

O Editor do Site guarda alterações na BD e essas cópias passam a esconder os ficheiros do tema.
Como o design é gerido em ficheiros + git:

```bash
python3 -I tools/theme-status.py           # ver overrides na BD
python3 -I tools/theme-status.py --reset   # apagar e voltar aos ficheiros
```

### Instalar no site real

```bash
python3 -I tools/build-theme.py                 # dist/revivo-theme.zip
python3 -I tools/build-theme.py --bump patch     # sobe a versão e empacota
```

O zip leva os URLs do site real (substitui `http://localhost:8080`) e instala-se em
**WP-Admin → Aparência → Temas → Adicionar → Carregar tema**. Fica **inativo**: o site continua
igual até ativares. Para reverter, ativa o Twenty Twenty-Five — os templates que estão na BD
para esse tema nunca foram apagados.

`theme/revivo/screenshot.png` gera-se com `swift tools/make-screenshot.swift theme/revivo/screenshot.png`.

### Legado (fluxo anterior, na base de dados)

`design/apply.py` e `design/templates/`, `design/custom.original.css`, `design/revivo-v2.css`,
`design/revivo-shop.css`, `design/revivo.js` são o fluxo antigo (escrevia o design nos Global Styles
e em templates do Twenty Twenty-Five). Ficam como histórico e como caminho de recurso; o design
atual é `theme/revivo`. `design/parts/_legacy/` tem cópias antigas das parts.

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
2. **Tema:** carregar `dist/revivo-theme.zip` em **Aparência → Temas → Adicionar → Carregar tema**
   (fica inativo). Pré-visualizar e só depois **Ativar**. Ter o Twenty Twenty-Five instalado é o rollback.
3. `./push.sh all` — com o tema ativo, `css`, `part` e `template` deixam de ser usados; interessa o
   envio de **páginas** (`./push.sh page <slug>` ou `./push.sh all` para o que estiver diferente).
4. No WP-Admin real (não é enviado pelo script):
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
- `theme/revivo/`: o tema (design editável em ficheiros + git)
- `tools/build-theme.py`: empacota o tema em `dist/revivo-theme.zip` para o site real
- `tools/theme-status.py`: mostra/apaga overrides do Editor do Site na BD
- `push.sh`, `tools/push.py`: envio de páginas (e do fluxo antigo de templates/CSS) via REST API
- `.env`: credenciais do site real e do local (**não partilhar**, está no `.gitignore`)
- `config/harica-geant-tls-r1.pem`: certificado intermédio que o servidor da escola não envia
  (permite verificar o HTTPS em vez de o desligar)
- `import/`: exports do Duplicator · `backups/`: cópias do site real antes de cada envio
