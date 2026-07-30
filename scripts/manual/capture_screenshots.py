"""Captura screenshots reais do sistema para o manual do usuario.

Requer o servidor de desenvolvimento rodando (python manage.py runserver) e
login valido de um usuario com dados na empresa a ser fotografada.

Uso:
    python scripts/manual/capture_screenshots.py --modulo compras
    python scripts/manual/capture_screenshots.py            # todos os modulos do screens.json

As telas a capturar ficam descritas em scripts/manual/screens.json, um item por
tela, agrupadas por modulo. Cada item pode referenciar um registro real do
banco (pk_from) para montar URLs de detalhe sem hardcodar IDs.
"""
import argparse
import json
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
SCREENS_FILE = Path(__file__).resolve().parent / "screens.json"
SCREENSHOTS_DIR = BASE_DIR / "docs" / "manual" / "screenshots"

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")
sys.path.insert(0, str(BASE_DIR))

import django  # noqa: E402

django.setup()


def resolve_pk(app_label, model_name, filters=None, order_by="-id"):
    from django.apps import apps

    model = apps.get_model(app_label, model_name)
    qs = model.objects.all()
    if filters:
        qs = qs.filter(**filters)
    obj = qs.order_by(order_by).first()
    if obj is None:
        return None
    return obj.pk


def load_screens(modulo_filter=None):
    with open(SCREENS_FILE, "r", encoding="utf-8") as fh:
        screens = json.load(fh)
    if modulo_filter:
        screens = [s for s in screens if s["modulo"] == modulo_filter]
    return screens


def build_path(screen):
    path = screen["path"]
    if "pk_from" in screen:
        pk = resolve_pk(**screen["pk_from"])
        if pk is None:
            return None
        path = path.format(pk=pk)
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--modulo", default=None, help="Captura apenas as telas deste modulo")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--username", default="AS_Edson")
    parser.add_argument("--password", default="Senha@123")
    args = parser.parse_args()

    from playwright.sync_api import sync_playwright

    screens = load_screens(args.modulo)
    if not screens:
        print(f"Nenhuma tela encontrada para modulo={args.modulo!r} em {SCREENS_FILE}")
        return

    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(viewport={"width": 1440, "height": 900}, device_scale_factor=1.5)
        page = context.new_page()

        page.goto(f"{args.base_url}/login/")
        page.fill("#id_username", args.username)
        page.fill("#id_password", args.password)
        page.click("button.btn-entrar")
        page.wait_for_load_state("networkidle")

        ok, skipped, failed = 0, 0, 0
        for screen in screens:
            path = build_path(screen)
            if path is None:
                print(f"[SKIP] {screen['modulo']}/{screen['slug']} - nenhum registro encontrado para montar a URL")
                skipped += 1
                continue

            out_dir = SCREENSHOTS_DIR / screen["modulo"]
            out_dir.mkdir(parents=True, exist_ok=True)
            out_path = out_dir / f"{screen['slug']}.png"

            try:
                try:
                    page.goto(f"{args.base_url}{path}", wait_until="networkidle", timeout=25000)
                except Exception:
                    # algumas telas de relatorio sao lentas ou tem polling continuo;
                    # cai para esperar so o load do documento com timeout maior.
                    page.wait_for_load_state("load", timeout=60000)
                page.screenshot(path=str(out_path), full_page=True)
                print(f"[OK] {screen['modulo']}/{screen['slug']} -> {path}")
                ok += 1
            except Exception as exc:
                print(f"[FAIL] {screen['modulo']}/{screen['slug']} ({path}): {exc}")
                failed += 1

        browser.close()
        print(f"\nConcluido: {ok} ok, {skipped} sem dado, {failed} falharam.")


if __name__ == "__main__":
    main()
