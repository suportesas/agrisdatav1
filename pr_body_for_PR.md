# PR: Fixes for DocumentoFornecedor uploads and Fornecedor form validation

Summary
- The upload forms for `DocumentoFornecedor` and `DocumentoFazenda` were rejecting POSTs because they included fields that the views populate (`fornecedor`, `fazenda`, `enviado_por`) and `dias_antecedencia_alerta` was treated as required. Also, `FornecedorForm` required `regime_tributario` at form level causing create/update flows to fail in some minimal payload cases.

What I changed
- `cadastros/forms.py`: exclude `fornecedor`/`fazenda` and `enviado_por` in document forms; set `dias_antecedencia_alerta` optional in `DocumentoFornecedorForm`; make `regime_tributario` not required in `FornecedorForm`.
- `cadastros/views.py`: cleaned up upload view (removed debug prints).
- `cadastros/tests.py`: verified / added tests that cover document upload and fornecedor create/update flows.

Testing
- `python manage.py test cadastros` — all tests pass (30 tests).

Notes for reviewer
- No new migrations required for these form-level changes.
- See `CHANGELOG.md` for the short changelog entry.

Please review and suggest any edits to the PR description or commit message before I open the PR.