/* Revivo 2.0 — interações. NOTA: não usar o sinal "menor que" em comparações (o WordPress confunde-o com HTML); usar ">" invertido. */
/* Revivo 2.0 — interações (fonte: design/revivo.js · aplicar com: python3 -I design/apply.py js) */
(function () {
  var d = document, r = d.documentElement;
  if (r.classList.contains('rv-js')) return;
  r.classList.add('rv-js');
  var reduce = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
  var hdr = d.querySelector('header.wp-block-template-part'), tb = d.querySelector('.rv-topbar');

  /* altura da barra superior: o header fica colado logo abaixo dela quando se faz scroll */
  function topbar() { if (tb) r.style.setProperty('--rv-topbar-h', tb.offsetHeight + 'px'); }
  topbar(); addEventListener('resize', topbar);

  /* fundo da navbar quando está colada ao topo (muda com a barra de admin e com sessão iniciada):
     o submenu das páginas (.rv-subnav) fica a seguir a ela em vez de a uma altura fixa */
  function navBottom() {
    if (!hdr) return;
    var nav = hdr.querySelector('.rv-navwrap') || hdr;
    var stuck = parseFloat(getComputedStyle(hdr).top) || 0;
    r.style.setProperty('--rv-nav-bottom', Math.round(stuck + nav.getBoundingClientRect().bottom - hdr.getBoundingClientRect().top) + 'px');
  }
  navBottom(); addEventListener('resize', navBottom); addEventListener('load', navBottom);

  /* barra de progresso, header com sombra e linha do "como funciona" */
  var bar = d.createElement('div'); bar.className = 'rv-progress'; bar.setAttribute('aria-hidden', 'true'); d.body.appendChild(bar);
  var steps = d.querySelectorAll('.rv-steps'), ticking = false;
  function onScroll() {
    ticking = false;
    var y = scrollY, max = r.scrollHeight - innerHeight;
    bar.style.setProperty('--p', max > 0 ? (y / max).toFixed(4) : 0);
    if (hdr) hdr.classList.toggle('rv-scrolled', y > (tb ? tb.offsetHeight : 0) + 10);
    steps.forEach(function (s) {
      var b = s.getBoundingClientRect();
      var p = Math.min(1, Math.max(0, (innerHeight * .85 - b.top) / (b.height + innerHeight * .25)));
      s.style.setProperty('--p', (p * 100).toFixed(1) + '%');
      /* cada passo acende quando a linha chega ao centro do quadrado
         (sem linha, em ecrãs pequenos: quando o quadrado entra no ecrã) */
      var lc = getComputedStyle(s, '::before'), line = lc.display !== 'none';
      var l0 = parseFloat(lc.left) || 0, len = b.width - l0 - (parseFloat(lc.right) || 0);
      s.querySelectorAll('.rv-step').forEach(function (st) {
        var ic = (st.querySelector('.rv-icon') || st).getBoundingClientRect();
        var on = reduce || (line ? l0 + p * len + 1 >= ic.left + ic.width / 2 - b.left : innerHeight * .8 > ic.top);
        st.classList.toggle('is-on', on);
      });
    });
  }
  addEventListener('scroll', function () { if (!ticking) { ticking = true; requestAnimationFrame(onScroll); } }, { passive: true });
  onScroll();

  /* luz que segue o rato nos cartões */
  d.addEventListener('pointermove', function (e) {
    var c = e.target.closest && e.target.closest('.rv-card,.rv-stat,.rv-cats a');
    if (!c) return;
    var b = c.getBoundingClientRect();
    c.style.setProperty('--mx', (e.clientX - b.left) + 'px');
    c.style.setProperty('--my', (e.clientY - b.top) + 'px');
  }, { passive: true });

  /* botões − / + nos campos de quantidade (produto e carrinho clássico) */
  function steppers(root) {
    (root || d).querySelectorAll('.quantity:not(.rv-q)').forEach(function (q) {
      var inp = q.querySelector('input.qty'); if (!inp || inp.type === 'hidden') return;
      q.classList.add('rv-q');
      function mk(t, dlt) {
        var b = d.createElement('button'); b.type = 'button'; b.className = 'rv-qbtn'; b.textContent = t;
        b.setAttribute('aria-label', dlt > 0 ? 'Aumentar quantidade' : 'Diminuir quantidade');
        b.addEventListener('click', function () {
          var min = parseFloat(inp.min) || 1, max = parseFloat(inp.max) || Infinity, v = (parseFloat(inp.value) || min) + dlt;
          inp.value = Math.min(max, Math.max(min, v)); inp.dispatchEvent(new Event('change', { bubbles: true }));
        });
        return b;
      }
      q.insertBefore(mk('−', -1), inp); q.appendChild(mk('+', 1));
    });
  }
  steppers();

  /* painel de cliente: saudação, última encomenda e atalhos */
  function rvDashboard() {
    var content = d.querySelector('.woocommerce-MyAccount-content');
    if (!content || !d.querySelector('.woocommerce-MyAccount-navigation-link--dashboard.is-active')) return;
    var links = {};
    d.querySelectorAll('.woocommerce-MyAccount-navigation-link').forEach(function (li) {
      var k = (li.className.match(/navigation-link--([\w-]+)/) || [])[1], a = li.querySelector('a');
      if (k && a) links[k] = a.href;
    });
    // primeiro nome do perfil (functions.php); sem ele, a saudação fica "Olá!" e as iniciais vêm do nome público
    var user = window.rvUser || {}, first = user.first || '';
    var strong = content.querySelector('p strong'), name = first ? first + ' ' + (user.last || '') : (strong ? strong.textContent.trim() : '');
    var ini = name.split(/\s+/).filter(Boolean).slice(0, 2).map(function (s) { return s[0]; }).join('').toUpperCase();
    function el(tag, cls, text) { var e = d.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; }

    var box = el('div', 'rv-dash');
    var hello = el('div', 'rv-dash-hello');
    hello.appendChild(el('span', 'rv-dash-avatar', ini || '☺'));
    var ht = el('div'); ht.appendChild(el('p', 'rv-dash-k', 'Área de cliente'));
    ht.appendChild(el('h2', '', first ? 'Olá, ' + first : 'Olá!'));
    ht.appendChild(el('p', 'rv-dash-sub', 'Acompanhe as suas encomendas e gira os seus dados num só sítio.'));
    hello.appendChild(ht); box.appendChild(hello);

    var last = el('div', 'rv-dash-last'); last.setAttribute('aria-live', 'polite');
    last.appendChild(el('p', 'rv-dash-k', 'Última encomenda'));
    var body = el('div', 'rv-dash-last-body', 'A carregar…'); last.appendChild(body); box.appendChild(last);

    // ícones com os mesmos traços do menu lateral (base.css / shop.css)
    var icons = {
      box: '<path d="M12 2.8 20 7.2v9.6L12 21.2 4 16.8V7.2z"/><path d="M4 7.2l8 4.4 8-4.4M12 11.6v9.6"/>',
      wrench: '<path d="M14.7 6.3a4 4 0 0 0-5.4 5.4L3 18l3 3 6.3-6.3a4 4 0 0 0 5.4-5.4l-2.6 2.6-2.4-.6-.6-2.4z"/>',
      pin: '<path d="M12 21s-6.5-5.6-6.5-11a6.5 6.5 0 0 1 13 0c0 5.4-6.5 11-6.5 11z"/><circle cx="12" cy="10" r="2.3"/>',
      user: '<circle cx="12" cy="8" r="4"/><path d="M4 20.5c1.5-4 4.5-6 8-6s6.5 2 8 6"/>'
    };
    // com o plugin Revivo Pedidos ativo, o atalho leva aos pedidos (que têm o botão "Novo pedido")
    var peca = links.pedidos ? ['pedidos', 'Pedidos de peças', 'Orçamentos e estado', 'wrench'] : ['pedir', 'Pedir uma peça', 'Orçamento à medida', 'wrench'];
    var tiles = [['orders', 'Encomendas', 'Histórico e estado', 'box'], peca,
      ['edit-address', 'Moradas', 'Faturação e envio', 'pin'], ['edit-account', 'Detalhes da conta', 'Nome, email e senha', 'user']];
    var pedir = d.querySelector('.rv-hbtn'); if (pedir) links.pedir = pedir.href;
    var grid = el('div', 'rv-dash-grid');
    tiles.forEach(function (t) {
      if (!links[t[0]]) return;
      var a = el('a', 'rv-dash-tile'); a.href = links[t[0]];
      var ico = el('span', 'rv-dash-ico'); ico.setAttribute('aria-hidden', 'true');
      ico.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' + icons[t[3]] + '</svg>';
      a.appendChild(ico); a.appendChild(el('b', '', t[1])); a.appendChild(el('span', 'rv-dash-desc', t[2]));
      grid.appendChild(a);
    });
    box.appendChild(grid);
    content.querySelectorAll(':scope > p').forEach(function (p) { p.classList.add('rv-dash-default'); });
    content.insertBefore(box, content.firstChild);

    if (!links.orders) { body.textContent = ''; return; }
    fetch(links.orders, { credentials: 'same-origin' }).then(function (r) { return r.text(); }).then(function (html) {
      var doc = new DOMParser().parseFromString(html, 'text/html');
      var rows = doc.querySelectorAll('.woocommerce-orders-table__row');
      body.textContent = '';
      if (!rows.length) {
        body.appendChild(el('p', 'rv-dash-empty', 'Ainda não fez nenhuma encomenda.'));
        var go = el('a', 'rv-dash-btn', 'Explorar a loja'); go.href = (d.querySelector('.rv-header a[href*="shop"]') || {}).href || '/'; body.appendChild(go);
        return;
      }
      var r = rows[0], cell = function (k) { var c = r.querySelector('.woocommerce-orders-table__cell-order-' + k); return c ? c.textContent.replace(/\s+/g, ' ').trim() : ''; };
      var status = (r.className.match(/status-([\w-]+)/) || [])[1] || '';
      var top = el('div', 'rv-dash-order');
      top.appendChild(el('b', 'rv-dash-num', cell('number')));
      top.appendChild(el('span', 'rv-badge rv-badge--' + status, cell('status')));
      body.appendChild(top);
      body.appendChild(el('p', 'rv-dash-meta', cell('date') + ' · ' + cell('total')));
      var view = r.querySelector('.woocommerce-orders-table__cell-order-actions a, .woocommerce-orders-table__cell-order-number a');
      var act = el('div', 'rv-dash-actions');
      if (view) { var v = el('a', 'rv-dash-btn', 'Ver encomenda'); v.href = view.href; act.appendChild(v); }
      var all = el('a', 'rv-dash-link', rows.length > 1 ? 'Ver todas (' + rows.length + ')' : 'Ver histórico'); all.href = links.orders; act.appendChild(all);
      body.appendChild(act);
    }).catch(function () { body.textContent = ''; });
  }
  rvDashboard();

  /* páginas legais: índice lateral com secção ativa */
  (function toc() {
    var art = d.querySelector('.rv-legal'), aside = d.querySelector('.rv-legal-aside');
    if (!art || !aside) return;
    var hs = art.querySelectorAll('h2'); if (!hs.length) return;
    var nav = d.createElement('nav'); nav.className = 'rv-toc'; nav.setAttribute('aria-label', 'Nesta página');
    var k = d.createElement('span'); k.className = 'rv-toc-k'; k.textContent = 'Nesta página'; nav.appendChild(k);
    var map = [];
    hs.forEach(function (h, i) {
      if (!h.id) h.id = 's' + (i + 1);
      var n = String(i + 1).padStart(2, '0'); h.setAttribute('data-n', n);
      var a = d.createElement('a'); a.href = '#' + h.id;
      var s = d.createElement('span'); s.textContent = n; a.appendChild(s); a.appendChild(d.createTextNode(h.textContent));
      nav.appendChild(a); map.push([h, a]);
    });
    aside.appendChild(nav);
    function spy() {
      var cur = map[0];
      map.forEach(function (m) { if (160 > m[0].getBoundingClientRect().top) cur = m; });
      map.forEach(function (m) { m[1].classList.toggle('is-active', m === cur); });
    }
    addEventListener('scroll', spy, { passive: true }); spy();
  })();

  /* pesquisa: painel com resultados ao vivo (produtos + páginas) */
  (function search() {
    var btn = d.querySelector('.rv-search-btn'); if (!btn) return;
    var home = (d.querySelector('.rv-logo') || {}).href || location.origin + '/';
    var api = function (route, q) { return home + (home.indexOf('?') > -1 ? '&' : '?') + 'rest_route=' + route + '&' + q; };
    var dec = function (s) { var t = d.createElement('textarea'); t.innerHTML = s || ''; return t.value; };
    var money = function (p) { if (!p) return ''; var v = (parseInt(p.price, 10) || 0) / Math.pow(10, p.currency_minor_unit || 2);
      return v.toLocaleString('pt-PT', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' ' + (p.currency_symbol || '€'); };
    var ov = d.createElement('div'); ov.className = 'rv-search'; ov.hidden = true;
    ov.innerHTML = '<div class="rv-search-backdrop" data-close></div><div class="rv-search-panel" role="dialog" aria-modal="true" aria-label="Pesquisar">' +
      '<form class="rv-search-bar" role="search"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>' +
      '<input type="search" name="s" placeholder="Pesquisar produtos, peças, páginas…" autocomplete="off" aria-label="Pesquisar" aria-controls="rv-search-results">' +
      '<button type="button" class="rv-search-x" data-close aria-label="Fechar">Esc</button></form>' +
      '<div class="rv-search-body" id="rv-search-results" aria-live="polite"></div>' +
      '<div class="rv-search-foot"><span><span class="rv-kbd">↑</span><span class="rv-kbd">↓</span> navegar</span><span><span class="rv-kbd">↵</span> abrir</span><span><span class="rv-kbd">Esc</span> fechar</span></div></div>';
    d.body.appendChild(ov);
    var inp = ov.querySelector('input'), body = ov.querySelector('.rv-search-body'), form = ov.querySelector('form');
    var ctrl, timer, items = [], act = -1, lastFocus;
    var sugg = ['engrenagem', 'puxador', 'botão', 'vaso', 'suporte', 'resina'];
    function el(tag, cls, txt) { var e = d.createElement(tag); if (cls) e.className = cls; if (txt != null) e.textContent = txt; return e; }
    function idle() {
      body.textContent = '';
      body.appendChild(el('p', 'rv-search-k', 'Sugestões'));
      var row = el('div', 'rv-search-chips');
      sugg.forEach(function (s) { var b = el('button', 'rv-search-chip', s); b.type = 'button'; b.onclick = function () { inp.value = s; run(); inp.focus(); }; row.appendChild(b); });
      body.appendChild(row);
      body.appendChild(el('p', 'rv-search-k', 'Atalhos'));
      var list = el('div', 'rv-search-list');
      [['Loja', home + '?post_type=product'], ['Pedir uma peça à medida', (d.querySelector('.rv-hbtn') || {}).href], ['A minha conta', (d.querySelector('.wc-block-customer-account a') || {}).href]]
        .forEach(function (l) { if (!l[1]) return; var a = el('a', 'rv-search-item rv-search-item--link'); a.href = l[1]; a.appendChild(el('span', 'rv-search-ico', '↗')); a.appendChild(el('b', '', l[0])); list.appendChild(a); });
      body.appendChild(list); collect();
    }
    function collect() { items = [].slice.call(body.querySelectorAll('a.rv-search-item')); act = -1; }
    function mark(i) { items.forEach(function (a, j) { a.classList.toggle('is-active', j === i); }); act = i; if (items[i]) items[i].scrollIntoView({ block: 'nearest' }); }
    function open() { lastFocus = d.activeElement; ov.hidden = false; r.classList.add('rv-search-open'); requestAnimationFrame(function () { ov.classList.add('is-open'); inp.focus(); inp.select(); }); if (!inp.value) idle(); }
    function close() { ov.classList.remove('is-open'); r.classList.remove('rv-search-open'); setTimeout(function () { ov.hidden = true; }, 200); if (lastFocus) lastFocus.focus(); }
    function run() {
      var q = inp.value.trim(); clearTimeout(timer);
      if (2 > q.length) { idle(); return; }
      timer = setTimeout(function () {
        if (ctrl) ctrl.abort(); ctrl = new AbortController();
        body.classList.add('is-loading');
        var eq = encodeURIComponent(q);
        Promise.all([
          fetch(api('/wc/store/v1/products', 'search=' + eq + '&per_page=6'), { signal: ctrl.signal }).then(function (r) { return r.ok ? r.json() : []; }).catch(function () { return []; }),
          fetch(api('/wp/v2/search', 'search=' + eq + '&type=post&subtype=page&per_page=4'), { signal: ctrl.signal }).then(function (r) { return r.ok ? r.json() : []; }).catch(function () { return []; })
        ]).then(function (res) {
          body.classList.remove('is-loading'); body.textContent = '';
          var prods = res[0] || [], pages = res[1] || [];
          if (!prods.length && !pages.length) {
            var e = el('div', 'rv-search-empty'); e.appendChild(el('b', '', 'Sem resultados para “' + q + '”'));
            e.appendChild(el('p', '', 'Não encontra a peça? Nós modelamos e imprimimos à medida.'));
            var a = el('a', 'rv-search-item rv-search-cta', 'Pedir uma peça à medida →'); a.href = (d.querySelector('.rv-hbtn') || {}).href || home; e.appendChild(a);
            body.appendChild(e); collect(); return;
          }
          if (prods.length) {
            body.appendChild(el('p', 'rv-search-k', 'Produtos'));
            var list = el('div', 'rv-search-list');
            prods.forEach(function (p) {
              var a = el('a', 'rv-search-item'); a.href = p.permalink;
              var im = el('span', 'rv-search-thumb'); var src = p.images && p.images[0] && (p.images[0].thumbnail || p.images[0].src);
              if (src) { var img = d.createElement('img'); img.src = src; img.alt = ''; img.loading = 'lazy'; im.appendChild(img); }
              a.appendChild(im);
              var t = el('span', 'rv-search-txt'); t.appendChild(el('b', '', dec(p.name)));
              if (p.categories && p.categories[0]) t.appendChild(el('small', '', dec(p.categories[0].name)));
              a.appendChild(t);
              var pr = el('span', 'rv-search-price', money(p.prices)); if (p.on_sale) pr.classList.add('is-sale'); a.appendChild(pr);
              list.appendChild(a);
            });
            body.appendChild(list);
          }
          if (pages.length) {
            body.appendChild(el('p', 'rv-search-k', 'Páginas'));
            var pl = el('div', 'rv-search-list');
            pages.forEach(function (pg) { var a = el('a', 'rv-search-item rv-search-item--link'); a.href = pg.url; a.appendChild(el('span', 'rv-search-ico', '§')); a.appendChild(el('b', '', dec(pg.title))); pl.appendChild(a); });
            body.appendChild(pl);
          }
          var all = el('a', 'rv-search-item rv-search-all', 'Ver todos os resultados na loja →'); all.href = home + '?s=' + eq + '&post_type=product'; body.appendChild(all);
          collect(); if (items.length) mark(0);
        });
      }, 180);
    }
    btn.addEventListener('click', open);
    ov.addEventListener('click', function (e) { if (e.target.closest('[data-close]')) close(); });
    inp.addEventListener('input', run);
    form.addEventListener('submit', function (e) { e.preventDefault(); if (items[act]) location.href = items[act].href; else if (inp.value.trim()) location.href = home + '?s=' + encodeURIComponent(inp.value.trim()) + '&post_type=product'; });
    ov.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') { e.preventDefault(); close(); }
      else if (e.key === 'ArrowDown' && items.length) { e.preventDefault(); mark((act + 1) % items.length); }
      else if (e.key === 'ArrowUp' && items.length) { e.preventDefault(); mark((act - 1 + items.length) % items.length); }
      else if (e.key === 'Tab') { e.preventDefault(); inp.focus(); }
    });
    d.addEventListener('keydown', function (e) {
      var typing = /input|textarea|select/i.test((e.target || {}).tagName || '') || (e.target && e.target.isContentEditable);
      if ((e.key === 'k' && (e.metaKey || e.ctrlKey)) || (e.key === '/' && !typing)) { e.preventDefault(); ov.hidden ? open() : close(); }
    });
  })();

  /* A minha conta: trocar de separador sem recarregar a página */
  (function accountNav() {
    var nav = d.querySelector('.woocommerce-MyAccount-navigation'), content = d.querySelector('.woocommerce-MyAccount-content');
    if (!nav || !content || !window.fetch || !history.pushState) return;
    var base = (nav.querySelector('a') || {}).href || '';
    var root = base.replace(/\/?(\?.*)?$/, '').replace(/\/[^\/]+$/, '');
    function ajaxable(a) {
      if (!a || a.target || a.hasAttribute('download') || a.origin !== location.origin) return false;
      var h = a.href;
      if (h.indexOf(root) !== 0 || /customer-logout|edit-address\/(billing|shipping)|order-pay|add-payment-method/.test(h)) return false;
      if (a.closest('.woocommerce-MyAccount-navigation-link--customer-logout')) return false;
      return true;
    }
    var busy = null;
    function load(url, push) {
      if (busy) busy.abort();
      busy = new AbortController();
      content.classList.add('is-loading'); content.setAttribute('aria-busy', 'true');
      fetch(url, { credentials: 'same-origin', signal: busy.signal }).then(function (r) {
        if (!r.ok || r.redirected && r.url.indexOf(root) !== 0) throw 0;
        return r.text();
      }).then(function (html) {
        var doc = new DOMParser().parseFromString(html, 'text/html');
        var nc = doc.querySelector('.woocommerce-MyAccount-content'), nn = doc.querySelector('.woocommerce-MyAccount-navigation');
        if (!nc || !nn) throw 0;
        content.innerHTML = nc.innerHTML;
        nav.innerHTML = nn.innerHTML;
        d.title = doc.title;
        if (push) history.pushState({ rvAccount: 1 }, '', url);
        content.classList.remove('is-loading'); content.removeAttribute('aria-busy');
        content.classList.remove('rv-swap'); void content.offsetWidth; content.classList.add('rv-swap');
        rvDashboard(); steppers(content);
        var top = content.getBoundingClientRect().top;
        if (0 > top - 110 || top > innerHeight * .6) scrollTo({ top: scrollY + top - 120, behavior: reduce ? 'auto' : 'smooth' });
        var h = content.querySelector('h2, h3'); if (h) { h.setAttribute('tabindex', '-1'); h.focus({ preventScroll: true }); }
      }).catch(function (e) { if (e && e.name === 'AbortError') return; location.href = url; });
    }
    d.addEventListener('click', function (e) {
      if (e.defaultPrevented || e.button || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
      var a = e.target.closest && e.target.closest('.woocommerce-MyAccount-navigation a, .woocommerce-MyAccount-content a');
      if (!ajaxable(a)) return;
      e.preventDefault();
      if (a.href !== location.href) load(a.href, true);
    });
    history.replaceState({ rvAccount: 1 }, '', location.href);
    addEventListener('popstate', function (e) { if (e.state && e.state.rvAccount) load(location.href, false); });
  })();

  /* avaliações: resumo com média e distribuição, avatares com iniciais */
  (function reviews() {
    var box = d.querySelector('#reviews'); if (!box) return;
    var items = [].slice.call(box.querySelectorAll('li.review'));
    items.forEach(function (li) {
      var img = li.querySelector('img.avatar'), name = (li.querySelector('.woocommerce-review__author') || {}).textContent || '';
      if (img) {
        var s = d.createElement('span'); s.className = 'rv-rv-avatar';
        s.textContent = name.trim().split(/\s+/).slice(0, 2).map(function (w) { return w[0]; }).join('').toUpperCase();
        img.replaceWith(s);
      }
    });
    box.querySelectorAll('.woocommerce-review__verified').forEach(function (v) { v.textContent = 'Compra verificada'; });
    var ratings = items.map(function (li) { return parseInt((li.querySelector('.star-rating .rating') || {}).textContent, 10) || 0; }).filter(Boolean);
    var form = box.querySelector('#review_form_wrapper');
    var sum = d.createElement('div'); sum.className = 'rv-rv-summary';
    var left = d.createElement('div'); left.className = 'rv-rv-score';
    var avg = ratings.length ? ratings.reduce(function (a, b) { return a + b; }, 0) / ratings.length : 0;
    var big = d.createElement('b'); big.textContent = ratings.length ? avg.toFixed(1).replace('.', ',') : '—'; left.appendChild(big);
    var stars = d.createElement('span'); stars.className = 'rv-rv-stars'; stars.style.setProperty('--r', (avg / 5 * 100).toFixed(0) + '%');
    stars.setAttribute('aria-label', 'Média ' + avg.toFixed(1) + ' de 5'); left.appendChild(stars);
    var cnt = d.createElement('small'); cnt.textContent = ratings.length === 1 ? '1 avaliação' : ratings.length + ' avaliações'; left.appendChild(cnt);
    sum.appendChild(left);
    var bars = d.createElement('div'); bars.className = 'rv-rv-bars';
    [5, 4, 3, 2, 1].forEach(function (n) {
      var c = ratings.filter(function (r) { return r === n; }).length, row = d.createElement('div'); row.className = 'rv-rv-bar';
      var l = d.createElement('span'); l.textContent = n + '★'; row.appendChild(l);
      var t = d.createElement('i'); t.style.setProperty('--w', (ratings.length ? c / ratings.length * 100 : 0) + '%'); row.appendChild(t);
      var k = d.createElement('span'); k.textContent = c; row.appendChild(k);
      bars.appendChild(row);
    });
    sum.appendChild(bars);
    if (form) {
      var cta = d.createElement('a'); cta.className = 'rv-dash-btn rv-rv-write'; cta.href = '#review_form_wrapper'; cta.textContent = 'Escrever uma avaliação';
      cta.addEventListener('click', function (e) { e.preventDefault(); form.scrollIntoView({ behavior: reduce ? 'auto' : 'smooth', block: 'center' }); var t = form.querySelector('textarea'); if (t) setTimeout(function () { t.focus({ preventScroll: true }); }, 400); });
      sum.appendChild(cta);
    }
    box.insertBefore(sum, box.firstChild);
    d.querySelectorAll('.rv-product-rating a, .woocommerce-review-link').forEach(function (a) {
      a.textContent = a.textContent.replace(/\((\d+) customer reviews?\)/i, function (m, n) { return n === '1' ? '(1 avaliação)' : '(' + n + ' avaliações)'; });
    });
    // ligação da avaliação por baixo do título → abre o separador
    d.querySelectorAll('.rv-product-rating a, .woocommerce-review-link').forEach(function (a) {
      a.addEventListener('click', function () { var t = d.querySelector('.reviews_tab a'); if (t) t.click(); });
    });
  })();

  /* mini-carrinho (painel lateral): textos em PT e barra de portes grátis */
  (function miniCart() {
    var FREE = 40, busy = false;
    function txt(root) {
      root.querySelectorAll('.wp-block-woocommerce-mini-cart-title-items-counter-block, .wc-block-mini-cart__footer-subtotal .wc-block-components-totals-item__description, .wc-block-components-totals-item__description').forEach(function (e) {
        var t = e.textContent;
        var n = t.replace(/\(items?:\s*(\d+)\)/i, '$1').replace(/Shipping and discounts calculated at checkout\.?/i, 'Portes e descontos calculados no checkout.');
        if (n !== t) e.textContent = n;
      });
    }
    function bar(dr) {
      var sub = dr.querySelector('.wc-block-mini-cart__footer-subtotal .wc-block-components-totals-item__value, .wc-block-mini-cart__footer .wc-block-components-totals-item__value');
      var host = dr.querySelector('.wc-block-mini-cart__title');
      if (!sub || !host) return;
      var v = parseFloat(sub.textContent.replace(/[^\d,.-]/g, '').replace(/\.(?=\d{3})/g, '').replace(',', '.')) || 0;
      var el = dr.querySelector('.rv-mc-ship');
      if (!el) { el = d.createElement('div'); el.className = 'rv-mc-ship'; el.innerHTML = '<p></p><i><b></b></i>'; host.insertAdjacentElement('afterend', el); }
      var left = Math.max(0, FREE - v);
      el.querySelector('p').textContent = left ? 'Faltam ' + left.toLocaleString('pt-PT', { style: 'currency', currency: 'EUR' }) + ' para portes grátis' : '✓ Tem portes grátis nesta encomenda';
      el.classList.toggle('is-free', !left);
      el.querySelector('b').style.width = Math.min(100, v / FREE * 100) + '%';
    }
    var mo = new MutationObserver(function () {
      if (busy) return; busy = true;
      requestAnimationFrame(function () {
        var dr = d.querySelector('.wc-block-mini-cart__drawer');
        if (dr) { txt(dr); bar(dr); }
        busy = false;
      });
    });
    mo.observe(d.body, { childList: true, subtree: true, characterData: true });
  })();

  /* modal reutilizável (terminar sessão, cookies, …) */
  function rvModal(o) {
    var m = d.createElement('div'); m.className = 'rv-modal' + (o.cls ? ' ' + o.cls : ''); m.hidden = true;
    var bg = d.createElement('div'); bg.className = 'rv-modal-bg'; m.appendChild(bg);
    var box = d.createElement('div'); box.className = 'rv-modal-box'; box.setAttribute('role', o.alert ? 'alertdialog' : 'dialog');
    box.setAttribute('aria-modal', 'true'); box.setAttribute('aria-labelledby', o.id + '-t'); box.setAttribute('aria-describedby', o.id + '-d');
    if (o.icon) { var ic = d.createElement('div'); ic.className = 'rv-modal-ico'; ic.textContent = o.icon; ic.setAttribute('aria-hidden', 'true'); box.appendChild(ic); }
    var h = d.createElement('h2'); h.id = o.id + '-t'; h.textContent = o.title; box.appendChild(h);
    var desc = d.createElement('div'); desc.id = o.id + '-d'; desc.innerHTML = o.html; box.appendChild(desc);
    if (o.extra) box.appendChild(o.extra);
    var act = d.createElement('div'); act.className = 'rv-modal-actions';
    o.buttons.forEach(function (b) {
      var x = d.createElement('button'); x.type = 'button'; x.className = 'rv-btn rv-btn--' + (b.kind || 'ghost'); x.textContent = b.label;
      x.addEventListener('click', function () { b.onClick(api, x); }); act.appendChild(x);
    });
    box.appendChild(act); m.appendChild(box); d.body.appendChild(m);
    var last;
    var api = {
      el: m, box: box,
      open: function () { last = d.activeElement; m.hidden = false; if (!o.noLock) r.classList.add('rv-modal-open');
        requestAnimationFrame(function () { m.classList.add('is-open'); (box.querySelector('.rv-btn--' + (o.focus || 'ghost')) || box.querySelector('button')).focus(); }); },
      close: function () { m.classList.remove('is-open'); r.classList.remove('rv-modal-open'); setTimeout(function () { m.hidden = true; }, 250); if (last && last.focus) last.focus(); }
    };
    if (o.dismiss !== false) bg.addEventListener('click', api.close);
    m.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && o.dismiss !== false) { e.preventDefault(); api.close(); }
      if (e.key === 'Tab') { var f = [].slice.call(box.querySelectorAll('button, a[href], input:not([disabled])')); if (!f.length) return;
        var i = f.indexOf(d.activeElement); if (e.shiftKey && 1 > i) { e.preventDefault(); f[f.length - 1].focus(); } else if (!e.shiftKey && i === f.length - 1) { e.preventDefault(); f[0].focus(); } }
    });
    return api;
  }

  /* terminar sessão: pedir confirmação */
  (function logoutConfirm() {
    var href = null, modal = null;
    d.addEventListener('click', function (e) {
      var a = e.target.closest && e.target.closest('a[href*="customer-logout"], a[href*="action=logout"]');
      if (!a || e.metaKey || e.ctrlKey) return;
      e.preventDefault(); href = a.href;
      if (!modal) modal = rvModal({ id: 'rv-logout', icon: '👋', alert: true, title: 'Terminar sessão?',
        html: '<p>Vai sair da sua conta Revivo. Os artigos no carrinho ficam guardados neste dispositivo.</p>',
        buttons: [{ label: 'Cancelar', kind: 'ghost', onClick: function (m) { m.close(); } },
          { label: 'Terminar sessão', kind: 'danger', onClick: function (m, b) { b.disabled = true; b.textContent = 'A sair…'; location.href = href; } }] });
      modal.open();
    }, true);
  })();

  /* consentimento de cookies */
  (function cookies() {
    var KEY = 'rv-consent', saved = null;
    try { saved = JSON.parse(localStorage.getItem(KEY) || 'null'); } catch (e) {}
    window.rvConsent = saved || { preferences: false, statistics: false };
    var home = (d.querySelector('.rv-logo') || {}).href || '/';
    var policy = home.replace(/\/$/, '') + '/index.php/politica-de-cookies/';
    var opts = d.createElement('div'); opts.className = 'rv-ck-opts'; opts.hidden = true;
    [['necessary', 'Essenciais', 'Sessão, carrinho e segurança. Sempre ativos.', true],
     ['preferences', 'Preferências', 'Lembrar escolhas como o modo claro/escuro.'],
     ['statistics', 'Estatísticas', 'Medir visitas de forma anónima para melhorar o site.']].forEach(function (c) {
      var row = d.createElement('label'); row.className = 'rv-ck-opt';
      var t = d.createElement('div'); var b = d.createElement('b'); b.textContent = c[1]; var s = d.createElement('span'); s.textContent = c[2];
      t.appendChild(b); t.appendChild(s); row.appendChild(t);
      var sw = d.createElement('input'); sw.type = 'checkbox'; sw.className = 'rv-switch'; sw.name = c[0];
      sw.checked = c[3] ? true : !!window.rvConsent[c[0]]; if (c[3]) sw.disabled = true; row.appendChild(sw);
      opts.appendChild(row);
    });
    function save(pref, stats, m) {
      window.rvConsent = { preferences: pref, statistics: stats, date: new Date().toISOString() };
      try { localStorage.setItem(KEY, JSON.stringify(window.rvConsent)); } catch (e) {}
      if (!pref) { try { localStorage.removeItem('rv-theme'); } catch (e) {} }
      d.dispatchEvent(new CustomEvent('rv:consent', { detail: window.rvConsent }));
      m.close();
    }
    var modal = rvModal({ id: 'rv-cookies', cls: 'rv-modal--cookies', icon: '🍪', title: 'Cookies no site da Revivo', dismiss: false, noLock: true, focus: 'primary',
      html: '<p>Usamos cookies essenciais para o carrinho e a sessão. Com a sua autorização, usamos também cookies de preferências e estatísticas. Pode mudar a escolha a qualquer momento. <a href="' + policy + '">Política de cookies</a></p>',
      extra: opts,
      buttons: [
        { label: 'Rejeitar opcionais', kind: 'ghost', onClick: function (m) { save(false, false, m); } },
        { label: 'Personalizar', kind: 'ghost', onClick: function (m, b) {
          if (opts.hidden) { opts.hidden = false; b.textContent = 'Guardar escolhas'; return; }
          save(opts.querySelector('[name=preferences]').checked, opts.querySelector('[name=statistics]').checked, m);
        } },
        { label: 'Aceitar todos', kind: 'primary', onClick: function (m) { save(true, true, m); } }] });
    if (!saved) setTimeout(modal.open, 900);
    // link no rodapé para voltar a abrir
    var foot = d.querySelector('.rv-fcompliance');
    if (foot) { var l = d.createElement('button'); l.type = 'button'; l.className = 'rv-ck-link'; l.textContent = 'Preferências de cookies';
      l.addEventListener('click', function () { opts.hidden = false; var b = modal.box.querySelectorAll('.rv-btn')[1]; if (b) b.textContent = 'Guardar escolhas'; modal.open(); }); foot.insertBefore(l, foot.lastChild); }
  })();

  /* barra de avisos: os links duplicados não recebem foco */
  d.querySelectorAll('.rv-ann-track a').forEach(function (a) { a.tabIndex = -1; });

  /* barra de secções (página Sobre): secção ativa */
  (function subnav() {
    var links = [].slice.call(d.querySelectorAll('.rv-subnav a[href^="#"]')); if (!links.length) return;
    var secs = links.map(function (a) { return d.getElementById(a.getAttribute('href').slice(1)); });
    function spy() {
      var cur = 0;
      secs.forEach(function (s, i) { if (s && 200 > s.getBoundingClientRect().top) cur = i; });
      links.forEach(function (a, i) { a.classList.toggle('is-active', i === cur); if (i === cur) a.setAttribute('aria-current', 'true'); else a.removeAttribute('aria-current'); });
    }
    addEventListener('scroll', spy, { passive: true }); spy();
  })();

  /* páginas de resultados de pesquisa: título, contagem, migalhas e termo destacado */
  (function searchPage() {
    if (!d.querySelector('.rv-search-page')) return;
    var term = new URLSearchParams(location.search).get('s') || '';
    var h = d.querySelector('.rv-search-title');
    if (h && term) {
      h.textContent = '';
      var k = d.createElement('span'); k.className = 'rv-st-k'; k.textContent = 'Resultados para'; h.appendChild(k);
      var t = d.createElement('span'); t.className = 'rv-st-term'; t.textContent = '“' + term + '”'; h.appendChild(t);
      var n = d.querySelectorAll('.rv-sr-list > li, .rv-products .wc-block-product-template > li').length;
      var cnt = (d.querySelector('.woocommerce-result-count') || {}).textContent || '';
      var m = cnt.match(/(\d+)\s+resultado/); if (m) n = parseInt(m[1], 10);
      var cc = d.createElement('span'); cc.className = 'rv-st-count'; cc.textContent = n === 1 ? '1 resultado' : n + ' resultados'; h.appendChild(cc);
    }
    // migalhas: "Resultados da pesquisa por “x”" → "Pesquisa"
    d.querySelectorAll('.rv-hero-crumbs .woocommerce-breadcrumb').forEach(function (bc) {
      var last = bc.lastChild; while (last && last.nodeType === 1 && !last.textContent.trim()) last = last.previousSibling;
      if (last && last.nodeType === 3 && /pesquisa|search/i.test(last.textContent)) last.textContent = last.textContent.replace(/[^\/]*$/, ' Pesquisa');
    });
    // destacar o termo nos excertos e títulos
    if (term.length > 1) {
      var re = new RegExp('(' + term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + ')', 'gi');
      d.querySelectorAll('.rv-sr-excerpt p, .rv-sr-title a, .rv-pcard-title a').forEach(function (el) {
        [].slice.call(el.childNodes).forEach(function (nd) {
          if (nd.nodeType !== 3 || !re.test(nd.textContent)) return; re.lastIndex = 0;
          var span = d.createElement('span'); span.innerHTML = nd.textContent.replace(/[&"]/g, function (ch) { return ch === '&' ? '&amp;' : '&quot;'; }).replace(/[<]/g, '&lt;').replace(re, '<mark>$1</mark>');
          nd.replaceWith.apply(nd, [].slice.call(span.childNodes));
        });
      });
    }
  })();

  if (reduce || !('IntersectionObserver' in window)) return;

  /* números que contam (62 Mt, 22,3%…) */
  var nums = [].slice.call(d.querySelectorAll('.rv-stat .rv-big')).map(function (el) {
    var m = el.textContent.trim().match(/^(\d+(?:[.,]\d+)?)(.*)$/);
    if (!m) return null;
    var dec = (m[1].split(/[.,]/)[1] || '').length, sep = m[1].indexOf(',') > -1 ? ',' : '.';
    return { el: el, to: parseFloat(m[1].replace(',', '.')), dec: dec, sep: sep, suf: m[2] };
  }).filter(Boolean);
  function count(n) {
    var t0 = performance.now(), dur = 1600;
    (function frame(t) {
      var k = Math.min(1, (t - t0) / dur), e = 1 - Math.pow(2, -10 * k);
      n.el.textContent = (n.to * e).toFixed(n.dec).replace('.', n.sep) + n.suf;
      if (1 > k) requestAnimationFrame(frame);
    })(t0);
  }
  var ioN = new IntersectionObserver(function (en) {
    en.forEach(function (e) {
      if (!e.isIntersecting) return;
      ioN.unobserve(e.target);
      nums.forEach(function (n) { if (n.el === e.target) count(n); });
    });
  }, { threshold: .6 });
  nums.forEach(function (n) { n.el.textContent = '0' + (n.dec ? n.sep + '0'.repeat(n.dec) : '') + n.suf; ioN.observe(n.el); });

  /* entrada suave dos elementos ao fazer scroll */
  /* nos passos só o texto entra a desvanecer: o quadrado fica opaco para a linha de progresso não se ver através dele */
  var sel = '.rv-head,.rv-hero-text>*,.rv-art,.rv-split>:not(.rv-stats),.rv-card,.rv-stat,.rv-step>:not(.rv-icon),.rv-cats a,.rv-mats,' +
    '.rv-feature>*,.rv-cta,.rv-bmc>*,.rv-quote,.rv-formcard,.rv-aside,.rv-facts,.rv-warn,.rv-fgrid>*,.rv-pagehero .rv-wrap>*,' +
    '.wp-block-buttons.rv-center';
  var els = [];
  d.querySelectorAll(sel).forEach(function (el) {  /* ordem do documento: os pais vêm primeiro */
    if (el.closest('.rv-header') || (el.parentElement && el.parentElement.closest('.rv-reveal'))) return;
    var i = [].indexOf.call(el.parentNode.children, el);
    el.style.setProperty('--d', Math.min(i, 6) * 70 + 'ms');
    el.classList.add('rv-reveal');
    els.push(el);
  });
  var io = new IntersectionObserver(function (en) {
    en.forEach(function (e) {
      if (!e.isIntersecting) return;
      var el = e.target; io.unobserve(el);
      el.classList.add('is-in');
      /* depois de entrar, devolve as transições normais (hover dos cartões, etc.) */
      setTimeout(function () { el.classList.remove('rv-reveal', 'is-in'); el.style.removeProperty('--d'); }, 1500);
    });
  }, { rootMargin: '0px 0px -6% 0px', threshold: .06 });
  els.forEach(function (el) { io.observe(el); });
})();
