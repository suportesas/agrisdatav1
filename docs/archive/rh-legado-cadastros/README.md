Owner: Documentacao (Legado)
Status: Deprecated
Last Updated: 2026-07-10
Scope: Sistema de RH (Férias, Afastamentos, Rescisões) implementado originalmente dentro do app cadastros

> ⚠️ **HISTÓRICO / DESATUALIZADO**: Este documento descreve o RH como parte do app `cadastros`. O RH foi posteriormente migrado para um app dedicado `rh/` (ver migração `cadastros/migrations/0112_remove_rh_models.py`). Para o estado atual, consulte `docs/2_MODULOS/MODULO_RH.md`.

# Sistema de RH (legado, dentro de `cadastros`)

Registro histórico consolidado, mesclado a partir de 4 arquivos originais:
- `CHECKLIST_RH.md`
- `GUIA_RAPIDO_SISTEMA_RH.md`
- `HISTORICO_IMPLEMENTACAO_RH.md`
- `SISTEMA_RH_COMPLETO.md`

Todos os 4 arquivos descrevem a mesma entrega original de RH — feita **dentro do app `cadastros`** — cobrindo Férias, Afastamentos e Rescisões de funcionários. Essa implementação foi posteriormente extraída para um app `rh/` dedicado (hoje registrado em `core/settings.py`, com `rh/apps.py` e `rh/models.py` próprios), e os models originais foram removidos de `cadastros` pela migração `cadastros/migrations/0112_remove_rh_models.py`. **Nenhuma das URLs, nomes de view ou caminhos de template abaixo deve ser considerada válida hoje** — este documento serve apenas como registro histórico do que foi construído originalmente.

## O que foi implementado (estado histórico, dentro de `cadastros`)

Data da implementação original: **20 de fevereiro de 2026**, sobre Django 5.2.7 / Python 3.13.6 (versões da época).

### Modelos (`cadastros/models.py`, à época)
- **`FeriasFuncionario`** (~30 campos): período aquisitivo e período de gozo, `dias_ferias` (máx. 30, CLT), `dias_abono` (abono pecuniário, máx. 10 dias / 1/3), valores (`valor_bruto`, `valor_terco_constitucional`, `valor_descontos`), upload de recibo, `status` (AGENDADA/EM_GOZO/CONCLUIDA/CANCELADA).
- **`AfastamentoFuncionario`** (~40 campos): tipos ATESTADO/ACIDENTE/MATERNIDADE/PATERNIDADE/AUXILIO_DOENCA, dados médicos (CID, médico, CRM), campos de CAT (Comunicação de Acidente de Trabalho: `emitiu_cat`, `numero_cat`, `data_emissao_cat`, upload), campos de INSS (`encaminhado_inss` — automático para afastamentos > 15 dias —, `numero_beneficio_inss`), `status` (ATIVO/ENCERRADO/CANCELADO).
- **`RescisaoContrato`** (~50 campos): tipos PEDIDO_DEMISSAO/ACORDO/JUSTA_CAUSA/SEM_JUSTA_CAUSA, aviso prévio, verbas rescisórias (saldo de salário, férias vencidas/proporcionais, 1/3, 13º proporcional, outras verbas), FGTS com multa automática (40% sem justa causa, 20% acordo), descontos (INSS, IRRF, outros), método `calcular_valor_liquido()`, documentos (TRCT, exame demissional, homologação obrigatória para contratos > 1 ano), `direito_seguro_desemprego`, `status` (EM_PROCESSO/CONCLUIDA/CANCELADA).
- Migration histórica: `cadastros/migrations/0058_afastamentofuncionario_feriasfuncionario_and_more.py` (posteriormente revertida/removida por `0112_remove_rh_models.py`).

### Views, forms, URLs e templates (histórico)
- `cadastros/views_rh.py` (~900 linhas): dashboard (`rh_dashboard`) + 13 views CRUD (3 list, 3 create, 3 detail, 3 update, 3 delete) para os três recursos, todas com filtro multi-tenant por empresa.
- `cadastros/forms.py`: `FeriasFuncionarioForm` (16 campos), `AfastamentoFuncionarioForm` (23 campos), `RescisaoContratoForm` (35 campos), Bootstrap 5, filtro de `funcionario` por empresa.
- `cadastros/urls.py`: 28 rotas nomeadas sob `/cadastros/rh/...` (dashboard, `ferias/*`, `afastamentos/*`, `rescisoes/*`).
- 13 templates em `cadastros/templates/cadastros/rh/` (dashboard + list/form/detail/confirm_delete para cada um dos 3 recursos), Bootstrap 5 + Font Awesome, cards responsivos, badges de status coloridas.
- Upload de arquivos organizado em `MEDIA_ROOT/rh/{ferias,afastamentos,cat,rescisoes}/YYYY/MM/`.

### Conformidade legal (CLT) implementada
Férias até 30 dias + abono pecuniário até 10 dias (1/3), período aquisitivo de 12 meses; afastamentos > 15 dias encaminhados automaticamente ao INSS; CAT para acidentes de trabalho; FGTS com multa de 40% (sem justa causa) ou 20% (acordo); TRCT e homologação obrigatória para contratos > 1 ano; rastreamento de direito a seguro-desemprego.

### Segurança (histórico)
`@login_required` em todas as views, filtro multi-tenant por `request.user.empresa` em querysets e formulários, CSRF em todos os forms, confirmação obrigatória antes de exclusão.

## Status conhecido à época
Documentado como "100% completo, backend e frontend prontos para produção", faltando apenas a integração do link/menu na sidebar (`CHECKLIST_RH.md` lista isso como pendência prioritária) e testes com dados reais/QA formal. Não há confirmação nos documentos-fonte de que a integração de menu chegou a ser feita antes da posterior extração do RH para o app dedicado `rh/`.

## O que fazer com esta informação hoje
Não usar nenhum caminho de URL, nome de view (`views_rh.py`), template (`cadastros/templates/cadastros/rh/...`) ou modelo (`FeriasFuncionario`, `AfastamentoFuncionario`, `RescisaoContrato` em `cadastros.models`) listado aqui como referência de código atual — todos foram removidos de `cadastros` pela migração `0112_remove_rh_models.py`. Os conceitos de negócio (regras de CLT, campos de férias/afastamento/rescisão, cálculos de FGTS) permanecem potencialmente úteis como referência de requisitos, mas a implementação real deve ser conferida no app `rh/` atual e em `docs/2_MODULOS/MODULO_RH.md`.
