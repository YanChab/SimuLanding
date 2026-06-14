"""Régénère une référence FRAÎCHE en exécutant la macro Excel sur une COPIE du classeur.

Le CSV de référence d'origine (``Results_MLG.csv``) a été mis en cache avec des cotes
de rainures différentes de celles actuellement saisies (section figée à 6.364 mm² au
lieu de 1.667 mm²). Ce script ouvre une copie temporaire du ``.xlsm``, exécute
``DropCalcul`` puis ``Affichage`` (qui remplissent la feuille « Results MLG ») avec les
entrées courantes, puis exporte le résultat dans ``Results_MLG_fresh.csv``.

L'original n'est JAMAIS modifié : tout se passe sur la copie, fermée sans sauvegarde.
"""
from __future__ import annotations

import csv
import shutil
import sys
from pathlib import Path

import win32com.client as win32

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "DROSIM_SA61-_#Simulation drop test avion complet.xlsm"
TMP = ROOT / "_extract" / "_tmp_run.xlsm"
OUT = ROOT / "_extract" / "reference" / "Results_MLG_fresh.csv"
SECTION_OUT = ROOT / "_extract" / "reference" / "section_fresh.csv"

# Sous-programmes à enchaîner (module de feuille « Feuil1 »).
MACROS = ["DropCalcul", "Affichage"]


def _run_macro(app, wb, name: str) -> None:
    """Exécute un sous-programme, en essayant plusieurs qualifications de nom."""
    candidates = [name, f"Feuil1.{name}", f"'{wb.Name}'!{name}", f"'{wb.Name}'!Feuil1.{name}"]
    last_err = None
    for cand in candidates:
        try:
            app.Run(cand)
            return
        except Exception as exc:  # noqa: BLE001
            last_err = exc
    raise RuntimeError(f"Impossible d'exécuter la macro {name!r}: {last_err}")


def _dump_used_range(ws, path: Path) -> int:
    used = ws.UsedRange
    values = used.Value  # tuple de tuples
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with path.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.writer(fh)
        for row in values:
            writer.writerow(["" if c is None else c for c in row])
            n += 1
    return n


def main() -> int:
    if not SRC.exists():
        print(f"Classeur introuvable: {SRC}", file=sys.stderr)
        return 2
    shutil.copy2(SRC, TMP)
    print(f"Copie -> {TMP.name}")

    app = win32.DispatchEx("Excel.Application")
    app.Visible = False
    app.DisplayAlerts = False
    app.EnableEvents = False
    app.ScreenUpdating = False
    wb = None
    try:
        wb = app.Workbooks.Open(str(TMP), ReadOnly=False)
        try:
            app.AutomationSecurity = 1  # msoAutomationSecurityLow (macros activées)
        except Exception:  # noqa: BLE001
            pass
        for m in MACROS:
            print(f"Exécution macro: {m} ...")
            _run_macro(app, wb, m)
        ws = wb.Worksheets("Results MLG")
        n = _dump_used_range(ws, OUT)
        print(f"Results MLG -> {OUT.name} ({n} lignes)")
        try:
            wsm = wb.Worksheets("MLG")
            rng = wsm.Range("J51:K551").Value
            with SECTION_OUT.open("w", newline="", encoding="utf-8-sig") as fh:
                w = csv.writer(fh)
                w.writerow(["pos_mm", "section_mm2"])
                for row in rng:
                    if row[0] is None:
                        break
                    w.writerow(["" if c is None else c for c in row])
            print(f"Section BH -> {SECTION_OUT.name}")
        except Exception as exc:  # noqa: BLE001
            print(f"(section non exportée: {exc})")
    finally:
        if wb is not None:
            wb.Close(SaveChanges=False)
        app.Quit()
        try:
            TMP.unlink(missing_ok=True)
        except Exception:  # noqa: BLE001
            pass
    print("Terminé.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
