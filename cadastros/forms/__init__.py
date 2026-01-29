# Bootstrap to expose symbols from the legacy `cadastros/forms.py` module.
# This allows importing `from cadastros import forms` while keeping a package layout.
import importlib.util
import pathlib

# Determine the path to the original forms.py file
_forms_py = pathlib.Path(__file__).parent.parent / 'forms.py'
if _forms_py.exists():
    spec = importlib.util.spec_from_file_location('cadastros._forms_legacy', str(_forms_py))
    _mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(_mod)
    # Export public symbols
    for _k, _v in _mod.__dict__.items():
        if not _k.startswith('_'):
            globals()[_k] = _v
