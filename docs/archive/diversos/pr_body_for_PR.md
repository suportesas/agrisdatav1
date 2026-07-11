# PR: Fixes for DocumentoFornecedor uploads and Fornecedor form validation

Summary
- The upload forms for `DocumentoFornecedor` and `DocumentoFazenda` were rejecting POSTs because they included fields that the views populate (`fornecedor`, `fazenda`, `enviado_por`) and `dias_antecedencia_alerta` was treated as required. Also, `FornecedorForm` required `regime_tributario` at form level causing create/update flows to fail in some minimal payload cases.

What I changed
- `cadastros/forms.py`: exclude `fornecedor`/`fazenda` and `enviado_por` in document forms; set `dias_antecedencia_alerta` optional in `DocumentoFornecedorForm`; added date widgets for document forms to render ISO date values correctly; made `regime_tributario` not required in `FornecedorForm`.
- `cadastros/views.py`: added document edit views for fazenda and fornecedor, handling file replacement and validation.
- `cadastros/tests.py` + `cadastros/tests/`: added tests validating document upload, edit flows, and that date values render correctly in edit forms.
- `cadastros/signals.py` + `cadastros/models.py`: added address synchronization between `Fornecedor` and `FornecedorEndereco` (signals for `post_save`/`post_delete` and `Fornecedor.save()` propagation); added unit tests for sync behavior.
- `cadastros/migrations/0007_...`: migration adjusting document fields (generated).

Testing
- `python manage.py test cadastros` — all tests pass (30 tests).

Notes for reviewer
- No new migrations required for these form-level changes.
- See `CHANGELOG.md` for the short changelog entry.

Please review and suggest any edits to the PR description or commit message before I open the PR.