# Changelog

## Unreleased

### Fixed
- Fix upload forms for `DocumentoFornecedor` and `DocumentoFazenda`: forms now exclude fields filled by the view (`fornecedor` / `fazenda`, `enviado_por`) and validate file size (<=10MB). This avoids rejecting valid POSTs from the UI and test clients.
- Make `DocumentoFornecedor.dias_antecedencia_alerta` optional at form level so default model values are used when omitted in POSTs.
- Make `FornecedorForm` accept minimal create payloads by **not requiring** `regime_tributario` in the form (still present on model with default).

(Tests updated/verified: cadastros tests all pass.)