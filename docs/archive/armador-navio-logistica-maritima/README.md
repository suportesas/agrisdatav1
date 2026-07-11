Owner: Documentacao (Legado)
Status: Deprecated
Last Updated: 2026-07-10
Scope: Cadastro de Armador (armadora/shipping company) e Navio no app cadastros, e reorganização do menu lateral em "Logística Marítima" (exportação)

# Cadastro de Armador & Navio e menu de Logística Marítima

Registro histórico consolidado, mesclado a partir de 5 arquivos originais:
- `CHECKLIST_ARMADOR_NAVIO.md`
- `IMPLEMENTACAO_ARMADOR_NAVIO.md`
- `IMPLEMENTACAO_COMPLETA_ARMADOR_NAVIO.md`
- `MENU_ATUALIZADO_ARMADOR_NAVIO.md`
- `MENU_LOGISTICA_MARITIMA.md`

Os 5 documentos narram, em sequência cronológica, a mesma entrega: backend (models/forms/views/admin) → templates → integração de menu → reorganização final do menu em submenu dedicado.

## O que foi implementado

Cadastro completo de **Armador** (armadora/shipping company, atende RF-028, RF-308, RF-805, RF-808) e **Navio** (RF-028) no app `cadastros`, com dados relacionados multi-valor (endereços, contatos, dados bancários) e vínculo N:N com `Porto`.

### Modelos (`cadastros/models.py`, ~400 linhas adicionadas)
- **`Armador`**: identidade (`codigo` único por empresa, `nome`, `nome_fantasia`, `cnpj` com estrutura pronta para busca via ReceitaWS, `pais`, `website`); endereço e contato principais "espelhados" diretamente no model (`cep`, `endereco`, `numero`, `complemento`, `bairro`, `cidade`, `uf`, `email`, `telefone`, `celular`); campos operacionais (`tipos_navio`, `capacidade_media`, `tempo_transito_dias`); indicadores comerciais RF-808 (`confiabilidade_percentual`, `percentual_rolagem_historico`, `custo_medio_rolagem`); auditoria (`ativo`, `data_criacao`, `data_atualizacao`, `criado_por`).
- **`ArmadorEndereco`** (multiendereço): tipos MATRIZ/FILIAL/OPERACIONAL/FATURAMENTO/ENTREGA, suporte a preenchimento via ViaCEP, um endereço padrão por armador (unicidade garantida).
- **`ArmadorContato`** (multicontato): tipos PRINCIPAL/FINANCEIRO/OPERACIONAL/COMERCIAL/TÉCNICO/EMERGÊNCIA, flags `whatsapp` e `preferencial`.
- **`ArmadorDadoBancario`** (multibanco): dados bancários tradicionais + PIX (5 tipos de chave: CPF/CNPJ/EMAIL/TELEFONE/CHAVE_ALEATORIA), conta padrão única por armador.
- **`Navio`**: `codigo`, `nome`, `imo` (opcional), `bandeira`, FK opcional para `Armador`, `tipo` (Container/Reefer/Break Bulk/Multipurpose/General/Tanker/RoRo — 7 tipos), capacidade (`capacidade_containers` em TEUs, `capacidade_toneladas`), características físicas (`ano_construcao`, `comprimento_metros`, `velocidade_media_nós`), `portos_operacao` (M2M com `Porto`), `status` (ATIVO/INATIVO/MANUTENCAO/DESCARTE).

Migração aplicada: `cadastros/migrations/0039_armador_armadorcontato_armadordadobancario_and_more.py`.

### Backend (forms, views, admin)
- `cadastros/forms_armador.py` (191 linhas) — `ArmadorForm`, `ArmadorEnderecoForm`, `ArmadorContatoForm`, `ArmadorDadoBancarioForm`, `NavioForm`, todos com classes Bootstrap 5 e placeholders para integração futura com APIs de CNPJ/CEP.
- `cadastros/views_armador.py` (427 linhas) — 18 views CRUD (`armador_list/detail/create/update/delete`, `armador_endereco_*`, `armador_contato_*`, `armador_banco_*`, `navio_list/detail/create/update/delete`), todas com `@login_required`, filtro multi-tenant por `request.user.empresa`, paginação de 20 itens.
- `cadastros/urls_armador.py` (46 linhas, 23 rotas) — depois integradas em `cadastros/urls.py`.
- `cadastros/admin.py` (~190 linhas adicionadas) — 6 classes admin com inlines e filtros.

### Templates (11 arquivos, Bootstrap 5)
`cadastros/templates/cadastros/armador/`: `list.html`, `detail.html` (com abas: Informações, Endereços, Contatos, Dados Bancários, Navios), `form.html`, `confirm_delete.html`, `endereco_form.html`, `contato_form.html`, `banco_form.html`.
`cadastros/templates/cadastros/navio/`: `list.html`, `detail.html` (abas: Informações, Portos), `form.html`, `confirm_delete.html`.

### Menu de navegação (2 iterações)
1. Primeira iteração: itens "Armadores" e "Navios" adicionados soltos na seção CADASTROS do `templates/sidebar.html` (ícones `bi-ship` e `bi-buildings`), junto com o registro das 21 URLs em `cadastros/urls.py` e os imports das views em `cadastros/views.py`.
2. Reorganização final: Porto + Armador + Navio agrupados em um submenu **"Logística Marítima"** dentro do menu **Exportação** (não mais em CADASTROS), com ícones `bi-water` (Portos), `bi-ship` (Armadores), `bi-sailboat` (Navios), seguindo o mesmo padrão `nested-submenu` já usado para "Funcionários".

### Segurança e padrões
Multi-tenancy via FK obrigatória para `Empresa` em todos os modelos, filtro automático por `request.user.empresa` nas views e no admin para não-superuser, `@login_required`, CSRF em todos os forms, unicidade de `codigo`+empresa e `cnpj`+empresa (quando preenchido), unicidade de endereço/contato/conta "padrão" por armador.

## Quando foi feito
Backend e templates concluídos e "prontos para produção" em **9 de fevereiro de 2026** (data confirmada em `IMPLEMENTACAO_COMPLETA_ARMADOR_NAVIO.md`); a reorganização de menu em "Logística Marítima" é posterior a essa data (documento sem timestamp explícito, mas referencia os templates já existentes).

## Status final
Backend + templates + menu totalmente implementados e documentados como prontos para produção. Explicitamente **não implementado** (deixado como opcional/futuro nos documentos-fonte): integração real com APIs externas de CNPJ (ReceitaWS) e CEP (ViaCEP) — os campos/hooks existem mas os placeholders não foram conectados a uma chamada HTTP real; API REST dedicada para Armador/Navio; testes unitários e de integração; relatórios (PDF/Excel); dashboards/gráficos de indicadores; notificações; importação em lote (Excel/CSV).

## Gotchas / avisos ainda relevantes
- Antes de assumir que a integração de CNPJ/CEP está ativa, confirmar em `cadastros/forms_armador.py` e no JavaScript associado se há de fato uma chamada à ReceitaWS/ViaCEP implementada — os documentos-fonte deixam isso como pendência.
- O nome da URL `armador_list`/`navio_list` referenciado nos templates de menu (`{% url 'armador_list' %}`) não usa namespace de app (`cadastros:armador_list`) nos exemplos dos documentos originais — verificar no `cadastros/urls.py` atual se o namespacing padrão do projeto (`app_name = 'cadastros'`, conforme `CLAUDE.md`) foi de fato respeitado, já que a maioria das outras rotas do projeto usa namespace.
- Verificar se o menu final realmente ficou sob "Exportação → Logística Marítima" (conforme a segunda iteração) e não duplicado também em "Cadastros" (conforme a primeira iteração) — os dois documentos de menu descrevem estados sucessivos, não cumulativos.
