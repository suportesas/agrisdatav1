# Changelog

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

(Tests updated/verified: cadastros tests all pass.)