# Changelog

## [Phase 2 Decision] - 02/04/2026

### Strategic Decision
- **Opção Escolhida**: Fase 2 XE (XML Enhancement)
- **Escopo**: SEFAZ Validation + Rastreabilidade de Lote + Batch Operations
- **Estimativa**: 22 horas (~2-3 semanas para 1 dev)
- **Timeline**: Sprint 1 (Apr 4-8), Sprint 2 (Apr 11-15), Sprint 3 (Apr 18-22)
- **Documentos**: 
  - [Plano de Execução](./docs/fase2/PLANO_EXECUCAO_FASE2_XE.md)
  - [Kickoff](./docs/fase2/KICKOFF_FASE2_XE.md)
- **Bloqueadores**: Certificado A1, WSDL SEFAZ, Staging network access (a validar)

### Status Fase 1 (Completed)
- ✅ NF-e XML Parser implementado e testado (8 testes)
- ✅ Feature flag `FF_COMPRAS_XML_IMPORT` ativa
- ✅ Checklist de homologação manual criado
- ✅ Commit 2f02267 merged to main

---

## Unreleased

### Fixed
- Fix upload forms for `DocumentoFornecedor` and `DocumentoFazenda`: forms now exclude fields filled by the view (`fornecedor` / `fazenda`, `enviado_por`) and validate file size (<=10MB). This avoids rejecting valid POSTs from the UI and test clients.
- Make `DocumentoFornecedor.dias_antecedencia_alerta` optional at form level so default model values are used when omitted in POSTs.
- Make `FornecedorForm` accept minimal create payloads by **not requiring** `regime_tributario` in the form (still present on model with default).

### Added
- Sincronização de endereços entre `Fornecedor` e `FornecedorEndereco`:
  - Salvar um `Fornecedor` com campos de endereço atualizados cria/atualiza o `FornecedorEndereco` padrão.
  - Atualizar/deletar o `FornecedorEndereco` padrão atualiza/limpa os campos espelhados no `Fornecedor`.
  - Inclui sinais (`post_save` / `post_delete`) e testes unitários cobrindo criação, atualização, promoção e deleção de endereços.
- Document attachments improvements:
  - Adicionado `Editar` para documentos de Fazenda e Fornecedor (visualizar/editar sem excluir).
  - Form widgets updated: `Data de Emissão` e `Data de Validade` renderam valores ISO (YYYY-MM-DD) corretamente, `Dias de Antecedência` é number input, `Observações` é textarea.
  - Tests added to verify date rendering in edit form and edit flows for documents.

- Added `Porto` model (multi-tenant) with admin registration, basic CRUD views, forms, templates and unit tests. Migration `0008_porto.py` created.

(Tests updated/verified: cadastros tests all pass.)