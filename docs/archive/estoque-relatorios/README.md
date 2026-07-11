Owner: Documentacao (Legado)
Status: Deprecated
Last Updated: 2026-07-10
Scope: Refatoração da atualização de estoque (fluxos com/sem lote) e sistema de relatório de estoque (PDF/Excel/Email/WhatsApp)

# Estoque: refatoração de movimentações e sistema de relatórios

Registro histórico consolidado, mesclado a partir de 9 arquivos originais:
- `CONCLUSAO_VALIDACAO_ESTOQUE.md`
- `RESUMO_CORRECCOES_ESTOQUE.md`
- `SUMARIO_FINAL.md`
- `RESUMO_FINAL_TRABALHO.md`
- `RELATORIO_ESTOQUE_CHECKLIST.md`
- `RELATORIO_ESTOQUE_README.md`
- `RELATORIO_ESTOQUE_RESUMO.md`
- `RELATORIO_ESTOQUE_STATUS.md`
- `QUICK_START_ESTOQUE.md`

Estes arquivos cobrem dois trabalhos distintos no módulo `estoque/`, feitos em datas diferentes, mais um arquivo que na verdade não é sobre estoque:

## A. Refatoração da atualização de estoque — fluxos com/sem lote (02/02/2026)

Fontes: `CONCLUSAO_VALIDACAO_ESTOQUE.md`, `RESUMO_CORRECCOES_ESTOQUE.md`, `SUMARIO_FINAL.md`, `QUICK_START_ESTOQUE.md`.

### Problema identificado
`estoque/models.py` (`MovimentacaoEstoque`) tinha métodos `executar()` e `_atualizar_estoque()` com definições duplicadas/aninhadas, gerando conflito sobre quem era responsável por atualizar o estoque. Além disso, movimentações de ENTRADA/SAIDA **sem lote** (entrada rápida, sem rastreabilidade PEPS/FIFO) simplesmente não atualizavam `Produto.estoque_atual`, e o template `movimentacao_detail.html` quebrava ao tentar acessar `movimentacao.lote.produto` quando não havia lote.

### Correções implementadas
- **`estoque/models.py`** (~linhas 980-1021): removidas as duplicações; `MovimentacaoEstoque.save()` passou a apenas gerar o número do documento (não atualiza estoque); `executar()` (decorado com `@transaction.atomic`) passou a ser o único ponto que valida status, chama `_atualizar_estoque()` e marca `EXECUTADO`.
- **`estoque/forms.py`** (~linhas 404-441): `save()` do formulário de movimentação passou a detectar quando não há lote e, nesse caso, chamar um novo método `_atualizar_estoque_produto_direto()`, que recalcula `Produto.estoque_atual = SUM(ENTRADA) - SUM(SAIDA)` a partir de todas as movimentações do produto (incluindo as ligadas via lote).
- **`estoque/templates/estoque/movimentacao_detail.html`** (~linhas 55-98): passou a testar `{% if movimentacao.lote %} ... {% elif movimentacao.produto %} ... {% else %}Nao informado{% endif %}` em vez de acessar `movimentacao.lote.produto` diretamente.

### Os dois fluxos resultantes
| Aspecto | COM Lote (histórico) | SEM Lote (novo) |
|---|---|---|
| Uso | Rastreabilidade PEPS/FIFO, recebimento de compra | Entrada/saída rápida, sem rastreio |
| Disparo | `.executar(usuario)` | `form.save()` |
| Atualização | `_atualizar_estoque()` → `Lote.save()` → `Produto.save()`, atômica | `_atualizar_estoque_produto_direto()` → `Produto.save()`, direta |
| Origem típica | `ItemRecebimento.registrar_movimento_estoque()` | Formulário de entrada/saída manual |

### Testes e validação (à época)
3 cenários de teste manuais confirmados: entrada única sem lote (100 KG), múltiplas entradas + saída sem lote ((100+150)-50 = 200 KG, batendo com o valor calculado), e fluxo completo com lote (dois recebimentos somando 250 KG, lotes e produto batendo). Sem regressões identificadas no fluxo de compra (Solicitação → Pedido → Recebimento).

### Como testar/depurar (preservado)
```bash
# Se o estoque não bater, recalcular a partir do zero:
python manage.py recalcular_estoque
```
Acessar `/estoque/entrada/`, preencher produto + quantidade e deixar "Lote" vazio para o fluxo rápido; usar o fluxo de Pedido de Compra/Recebimento para o fluxo rastreável com lote.

### Status final
Documentado como pronto para produção em 02/02/2026. Próximos passos deixados em aberto: testes em produção, teste do fluxo completo de compra, e otimizações futuras opcionais (cache de lotes, relatório de movimentações por período, alertas de estoque mínimo).

## B. Sistema de relatório de estoque — PDF/Excel/Email/WhatsApp (2024)

Fontes: `RELATORIO_ESTOQUE_CHECKLIST.md`, `RELATORIO_ESTOQUE_README.md`, `RELATORIO_ESTOQUE_RESUMO.md`, `RELATORIO_ESTOQUE_STATUS.md`.

> Nota de data: estes 4 documentos trazem "2024" como data de conclusão e citam Django 5.2.7/Python 3.13.6 — parecem ser de um momento anterior ao dos documentos do item A (02/02/2026) apesar de tratarem do mesmo módulo `estoque/`; preservado como está nas fontes.

### O que foi implementado
Tela de geração de relatório de estoque (`/estoque/relatorio/`) com filtros, dois formatos de saída e três canais de entrega.

**Arquivos criados:**
- `estoque/forms_relatorio.py` — formulário com 9 campos: múltiplos armazéns, múltiplas categorias, status do lote (ATIVO/BAIXO_ESTOQUE/VENCIDO/MANUTENÇÃO/DESCARTE), toggle "apenas baixo estoque", toggle "apenas vencidos", formato (PDF/Excel) e modo de envio (baixar/email/WhatsApp/ambos), com validação de e-mail e telefone.
- `estoque/relatorio_utils.py` — `RelatorioEstoquePDF` (ReportLab) e `RelatorioEstoqueExcel` (OpenPyXL), cada um com cabeçalho (empresa, data, filtros aplicados) e tabela (Produto, Lote, Armazém, Qtd. Atual + unidade, Validade, Status).
- `estoque/enviador.py` — `EnviadorEmail` (SMTP com anexo), `EnviadorWhatsApp` (API Twilio), `EnviadorRelatorio` (orquestra o envio).
- `estoque/templates/estoque/relatorio_estoque.html` — interface Bootstrap 5 com painel de filtros e painel de configuração de entrega, JS para exibir/ocultar campos condicionais.
- `CONFIGURACAO_RELATORIO_EMAIL_WHATSAPP.md` — guia de configuração SMTP (Gmail/Office365/SendGrid) e Twilio WhatsApp (não incluído neste cluster; verificar se ainda existe na raiz ou já foi arquivado em outro lugar).

**Arquivos modificados:**
- `estoque/views.py` — views `relatorio_estoque(request)` (GET exibe formulário, POST processa) e `processar_relatorio(request, form)`.
- `estoque/urls.py` — rota `estoque/relatorio/`.
- `templates/sidebar.html` — item de menu "Relatório de Estoque".
- `requirements.txt` — dependências `openpyxl==3.13.0`, `twilio==9.6.0`, `xhtml2pdf==0.2.16` (verificar versões atuais antes de assumir compatibilidade).

### Configuração necessária (não incluída por padrão)
Variáveis SMTP (`EMAIL_BACKEND`, `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_USE_TLS`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL`) e Twilio (`TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER`) em `core/settings.py` — nenhuma delas vem configurada por padrão; sem elas, apenas o modo "Apenas Baixar" funciona.

### Segurança
`@login_required`, filtro por empresa (multi-tenant), validação de formulário (e-mail/telefone), proteção CSRF padrão do Django.

### Testes realizados (à época)
5/5 testes manuais confirmados: criação do formulário (9 campos), busca de lotes (14 lotes de teste encontrados), geração de PDF (~2.6-2.7 KB), geração de Excel (~5.8-5.9 KB), validação do formulário. Performance registrada: relatórios até 1000 linhas em menos de 2 segundos.

### Status final
Documentado como "produção" nos 4 arquivos, com ressalva explícita de que Email e WhatsApp exigem configuração adicional do usuário antes de funcionar (credenciais SMTP/Twilio não vêm prontas). Roadmap futuro listado (não confirmado como implementado): agendamento automático de relatórios, envio para múltiplos destinatários, gráficos no PDF, exportação CSV/JSON, histórico de relatórios gerados, assinatura digital.

## C. Nota sobre arquivo fora de tema: `RESUMO_FINAL_TRABALHO.md`

Apesar de ter sido agrupado neste cluster de arquivos de estoque, o conteúdo de `RESUMO_FINAL_TRABALHO.md` **não é sobre estoque** — é sobre a expansão do seed de pragas pré-cadastradas por empresa (de ~30 para 88 pragas, `cadastros/pragas_seed.py`, signal `seed_pragas_on_create`, comando `python manage.py seed_pragas`), datado de 2025-02-04. Esse tema se sobrepõe ao cluster de arquivamento `docs/archive/seed-pragas/`, tratado por outra frente de trabalho neste mesmo esforço de reorganização de documentação — consulte aquele cluster para o histórico completo do seed de pragas. O arquivo foi movido para `fontes/` deste cluster por completude, já que assim constava na lista de origem desta consolidação, mas seu conteúdo real pertence tematicamente ao outro cluster.
