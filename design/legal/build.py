#!/usr/bin/env python3
"""
Páginas legais da Revivo (pt-PT) → site local.
  python3 -I design/legal/build.py
Cada página: hero do template "page" + layout .rv-legal (índice lateral gerado pelo JS).
Texto adaptado a uma loja online portuguesa, assinalando que é um projeto académico.
"""
import html, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import apply  # noqa: E402

URL = 'http://localhost:8080/index.php'
UPDATED = '17 de novembro de 2026'
ENTIDADE = ('Revivo — projeto académico do Grupo 6 da licenciatura em Tecnologias e Desenvolvimento Web '
            '(ESMAD / Politécnico do Porto). Loja fictícia: não existe uma empresa registada, NIF ou morada comercial reais.')
CONTACTO = 'revivo.grupo6@exemplo.pt'

PAGES = {
    'privacy-policy': ('Política de Privacidade', 3, 'Como tratamos os seus dados pessoais, ao abrigo do RGPD.', [
        ('Quem somos', [ENTIDADE, f'Para qualquer questão sobre privacidade, contacte-nos através de <a href="mailto:{CONTACTO}">{CONTACTO}</a>.']),
        ('Que dados recolhemos', [
            '- <b>Dados de conta e encomenda:</b> nome, email, telefone, morada de faturação e de envio.',
            '- <b>Pedidos de peças:</b> descrição, medidas, material, fotografias ou ficheiros 3D que nos envia.',
            '- <b>Dados técnicos:</b> endereço IP, tipo de navegador e páginas visitadas, de forma agregada.',
            '- <b>Preferências:</b> por exemplo o modo claro/escuro, guardado apenas no seu navegador.']),
        ('Para que usamos os dados', [
            '- Processar encomendas, orçamentos e entregas (execução de contrato).',
            '- Responder a pedidos de contacto e de peças à medida (diligências pré-contratuais).',
            '- Cumprir obrigações legais, como a faturação (obrigação legal).',
            '- Melhorar o site com estatísticas anónimas (interesse legítimo ou consentimento, conforme aplicável).',
            'Não vendemos nem partilhamos os seus dados para fins de marketing de terceiros.']),
        ('Durante quanto tempo', [
            'Guardamos os dados de encomendas durante o prazo exigido por lei para efeitos fiscais (até 10 anos). '
            'Os pedidos de orçamento sem encomenda são apagados ao fim de 12 meses. A conta de cliente mantém-se até pedir a sua eliminação.']),
        ('Com quem partilhamos', [
            'Apenas com prestadores necessários ao funcionamento da loja — alojamento do site, processamento de pagamentos e transportadoras — '
            'que tratam os dados por nossa conta e sob contrato. Neste projeto académico não existem pagamentos nem envios reais.']),
        ('Os seus direitos', [
            'Pode, a qualquer momento, pedir o acesso, retificação, apagamento, limitação, portabilidade ou opor-se ao tratamento dos seus dados, '
            f'e retirar o consentimento que tenha dado. Basta escrever para <a href="mailto:{CONTACTO}">{CONTACTO}</a>.',
            'Tem também o direito de apresentar reclamação à Comissão Nacional de Proteção de Dados (<a href="https://www.cnpd.pt" target="_blank" rel="noopener">www.cnpd.pt</a>).']),
        ('Segurança', ['O site usa ligação cifrada (HTTPS) e o acesso aos dados está limitado à equipa. Nenhum sistema é totalmente seguro, mas aplicamos medidas técnicas e organizativas adequadas.']),
        ('Cookies', [f'Usamos cookies essenciais para o carrinho e a sessão, e cookies opcionais apenas com o seu consentimento. Saiba mais na <a href="{URL}/politica-de-cookies/">Política de Cookies</a>.']),
    ]),
    'termos-e-condicoes': ('Termos e Condições', 0, 'As regras que se aplicam à utilização do site e às compras na Revivo.', [
        ('Identificação', [ENTIDADE, f'Contacto: <a href="mailto:{CONTACTO}">{CONTACTO}</a>.']),
        ('Âmbito', [
            'Estes termos aplicam-se a todas as compras feitas na loja online e aos pedidos de peças à medida. '
            'Ao concluir uma encomenda, declara que leu e aceita estes termos, a <a href="' + URL + '/privacy-policy/">Política de Privacidade</a> '
            'e a <a href="' + URL + '/refund_returns/">Política de Devoluções</a>.',
            '<b>Projeto académico:</b> a Revivo é uma loja fictícia criada para avaliação. Nenhuma encomenda é processada, cobrada ou enviada.']),
        ('Produtos e preços', [
            'Os produtos são fabricados por impressão 3D sob encomenda. As imagens são ilustrativas e podem existir pequenas variações de cor e textura próprias do processo de fabrico.',
            'Os preços são apresentados em euros e incluem IVA à taxa legal em vigor. Os portes de envio, quando existam, são indicados antes da confirmação da encomenda.']),
        ('Encomendas e pedidos à medida', [
            '- <b>Catálogo:</b> a encomenda fica confirmada após o pagamento; recebe um email com o resumo.',
            '- <b>Peças à medida:</b> o pedido é analisado pela equipa, que envia um orçamento sem compromisso. A produção só começa depois de o aceitar e pagar.',
            '- Reservamo-nos o direito de recusar pedidos que violem direitos de terceiros ou sejam tecnicamente inviáveis, devolvendo qualquer valor pago.']),
        ('Pagamento', ['Aceitamos os métodos indicados no checkout (transferência bancária, cheque ou pagamento na entrega). A encomenda é processada após a confirmação do pagamento.']),
        ('Prazos e entrega', [
            f'O prazo estimado de produção é de 3 a 5 dias úteis, a que acresce o prazo da transportadora. Veja os detalhes em <a href="{URL}/envios-e-pagamentos/">Envios e Pagamentos</a>. '
            'Se não conseguirmos cumprir o prazo, informamos e pode cancelar a encomenda com reembolso integral.']),
        ('Direito de livre resolução', [
            f'Tem 14 dias para devolver produtos do catálogo sem indicar motivo, nos termos do Decreto-Lei n.º 24/2014. '
            f'Esse direito não se aplica a peças fabricadas segundo as suas especificações ou claramente personalizadas (art. 17.º). Consulte a <a href="{URL}/refund_returns/">Política de Devoluções</a>.']),
        ('Garantia', ['Os produtos têm a garantia legal de conformidade de 3 anos (Decreto-Lei n.º 84/2021). Em caso de defeito, contacte-nos para reparação, substituição ou reembolso.']),
        ('Propriedade intelectual', ['Os conteúdos do site (textos, imagens, logótipo e modelos 3D) pertencem à Revivo. Ao enviar-nos ficheiros, garante que tem direito a utilizá-los; usamo-los apenas para produzir a sua encomenda.']),
        ('Resolução de litígios', [
            'Em caso de litígio de consumo, pode recorrer a uma entidade de Resolução Alternativa de Litígios, por exemplo o '
            '<a href="https://www.cniacc.pt" target="_blank" rel="noopener">CNIACC — Centro Nacional de Informação e Arbitragem de Conflitos de Consumo</a>. '
            'Mais informações no <a href="https://www.consumidor.gov.pt" target="_blank" rel="noopener">Portal do Consumidor</a>.',
            'Dispõe ainda do <a href="https://www.livroreclamacoes.pt" target="_blank" rel="noopener">Livro de Reclamações Eletrónico</a>.']),
        ('Lei aplicável', ['Estes termos regem-se pela lei portuguesa. Podemos atualizá-los; a versão aplicável é a que estava publicada na data da encomenda.']),
    ]),
    'refund_returns': ('Devoluções e Reembolsos', 22, 'Como devolver um produto e receber o seu dinheiro.', [
        ('Prazo de 14 dias', ['Pode devolver produtos do catálogo no prazo de 14 dias a contar da receção, sem indicar motivo (direito de livre resolução).']),
        ('O que não pode ser devolvido', [
            '- Peças fabricadas segundo as suas medidas ou especificações (pedidos à medida).',
            '- Produtos personalizados com cores, textos ou ficheiros fornecidos por si.',
            'Estas exceções não afetam a garantia: se uma peça à medida tiver defeito ou não corresponder ao orçamento aceite, resolvemos o problema.']),
        ('Como devolver', [
            f'1. Envie-nos um email para <a href="mailto:{CONTACTO}">{CONTACTO}</a> com o número da encomenda.',
            '2. Embale o produto de forma segura, no estado em que o recebeu.',
            '3. Envie-o para a morada que lhe indicarmos. Os portes de devolução ficam a seu cargo, salvo defeito.']),
        ('Reembolso', ['Reembolsamos o valor pago, incluindo os portes de envio iniciais, no prazo de 14 dias após recebermos a devolução, pelo mesmo meio de pagamento usado na compra.']),
        ('Produtos com defeito', ['Se o produto chegar danificado ou com defeito, contacte-nos com fotografias. Substituímos ou reembolsamos sem custos para si, ao abrigo da garantia legal de 3 anos.']),
    ]),
    'politica-de-cookies': ('Política de Cookies', 0, 'Que cookies usamos e como os pode gerir.', [
        ('O que são cookies', ['Cookies são pequenos ficheiros guardados no seu navegador que permitem ao site lembrar-se de informação entre páginas e visitas.']),
        ('Cookies que usamos', [
            '- <b>Essenciais:</b> sessão, carrinho de compras e segurança (WordPress e WooCommerce). Não podem ser desativados.',
            '- <b>Preferências:</b> modo claro/escuro (guardado no armazenamento local do navegador).',
            '- <b>Estatísticas (opcionais):</b> só são ativados com o seu consentimento, através do aviso de cookies.']),
        ('Gerir o consentimento', ['Pode alterar as suas escolhas a qualquer momento no aviso de cookies ou apagar os cookies nas definições do navegador. Desativar os cookies essenciais pode impedir o funcionamento do carrinho.']),
        ('Mais informação', [f'Veja também a <a href="{URL}/privacy-policy/">Política de Privacidade</a>.']),
    ]),
    'envios-e-pagamentos': ('Envios e Pagamentos', 0, 'Prazos, custos de envio e métodos de pagamento.', [
        ('Prazos', [
            '- <b>Produção:</b> 3 a 5 dias úteis (peças à medida: indicado no orçamento).',
            '- <b>Entrega em Portugal continental:</b> 1 a 3 dias úteis após a expedição.',
            '- <b>Ilhas:</b> 3 a 7 dias úteis.']),
        ('Custos de envio', ['O custo é calculado no checkout em função do peso e do destino. Encomendas acima de 40 € têm envio gratuito em Portugal continental.']),
        ('Métodos de pagamento', [
            '- Transferência bancária (a encomenda segue após a confirmação).',
            '- Cheque.',
            '- Pagamento na entrega.',
            '<b>Projeto académico:</b> nenhum pagamento é realmente cobrado.']),
        ('Acompanhar a encomenda', [f'Pode acompanhar o estado de cada encomenda em <a href="{URL}/my-account/orders/">A minha conta → Encomendas</a>.']),
    ]),
}


def p(txt):
    return f'<!-- wp:paragraph -->\n<p>{txt}</p>\n<!-- /wp:paragraph -->'


def block_list(items, ordered=False):
    tag = 'ol' if ordered else 'ul'
    attrs = '{"ordered":true} ' if ordered else ''
    lis = ''.join(f'<!-- wp:list-item -->\n<li>{i}</li>\n<!-- /wp:list-item -->' for i in items)
    return f'<!-- wp:list {attrs}-->\n<{tag} class="wp-block-list">{lis}</{tag}>\n<!-- /wp:list -->'


def section_html(items):
    out, bullets, nums = [], [], []
    def flush():
        nonlocal bullets, nums
        if bullets: out.append(block_list(bullets)); bullets = []
        if nums: out.append(block_list(nums, True)); nums = []
    for it in items:
        if it.startswith('- '):
            if nums: flush()
            bullets.append(it[2:])
        elif len(it) > 2 and it[0].isdigit() and it[1:3] == '. ':
            if bullets: flush()
            nums.append(it[3:])
        else:
            flush(); out.append(p(it))
    flush()
    return '\n'.join(out)


def page_content(title, lead, sections):
    body = []
    for i, (h, items) in enumerate(sections, 1):
        anchor = f's{i}'
        body.append(f'<!-- wp:heading {{"anchor":"{anchor}"}} -->\n<h2 class="wp-block-heading" id="{anchor}">{h}</h2>\n<!-- /wp:heading -->')
        body.append(section_html(items))
    return f'''<!-- wp:group {{"align":"full","className":"rv-section rv-legal-section","layout":{{"type":"constrained"}}}} -->
<div class="wp-block-group alignfull rv-section rv-legal-section">
<!-- wp:group {{"align":"wide","className":"rv-wrap rv-legal-grid","layout":{{"type":"default"}}}} -->
<div class="wp-block-group alignwide rv-wrap rv-legal-grid">
<!-- wp:group {{"tagName":"aside","className":"rv-legal-aside","layout":{{"type":"default"}}}} -->
<aside class="wp-block-group rv-legal-aside">
<!-- wp:paragraph {{"className":"rv-legal-updated"}} -->
<p class="rv-legal-updated">Atualizado a {UPDATED}</p>
<!-- /wp:paragraph -->
</aside>
<!-- /wp:group -->
<!-- wp:group {{"tagName":"article","className":"rv-legal","layout":{{"type":"default"}}}} -->
<article class="wp-block-group rv-legal">
<!-- wp:paragraph {{"className":"rv-lead rv-legal-lead"}} -->
<p class="rv-lead rv-legal-lead">{lead}</p>
<!-- /wp:paragraph -->
<!-- wp:paragraph {{"className":"rv-legal-note"}} -->
<p class="rv-legal-note"><b>Projeto académico.</b> A Revivo é uma loja fictícia: este texto serve de exemplo e não constitui aconselhamento jurídico.</p>
<!-- /wp:paragraph -->
{chr(10).join(body)}
</article>
<!-- /wp:group -->
</div>
<!-- /wp:group -->
</div>
<!-- /wp:group -->'''


if __name__ == '__main__':
    out = Path(__file__).parent / 'pages'
    out.mkdir(exist_ok=True)
    for slug, (title, pid, lead, sections) in PAGES.items():
        content = page_content(title, lead, sections)
        (out / f'{slug}.html').write_text(content)
        apply.upsert_page(slug, title, content, pid)
