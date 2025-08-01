#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Výpočet osobního příplatku (osobního ohodnocení) na základě
# platových tabulek v souboru "Platové tabulky 2025.ods".
#
# Logika (veřejný sektor podle ZP): maximální osobní příplatek = 100 %
# z platového tarifu 12. platového stupně v dané třídě.
#
# Skript:
# - načte ODS,
# - najde tabulku s třídami 1-16 a stupni 1-12,
# - vezme hodnotu 12. stupně pro zadanou třídu jako "max",
# - vypočte částku = max * (zvolené % / 100) * (úvazek % / 100).
#
# Potřeby: Python 3.9+, pandas, odfpy
#     pip install pandas odfpy

import sys
from pathlib import Path

try:
    import pandas as pd
except Exception as e:
    print("Chybí knihovna pandas. Nainstalujte: pip install pandas", file=sys.stderr)
    sys.exit(1)

ODS_FILENAME_DEFAULT = "platove-tabulky-2025.ods"

def fmt_kc(x: float) -> str:
    try:
        return f"{x:,.0f} Kč".replace(",", " ")
    except Exception:
        return f"{int(round(x))} Kč"

def load_class_maxima(ods_path: Path) -> dict:
    # Vrátí dict {třída: tarif_12_stupen} pro třídy 1..16.
    # Předpokládá list s 'Platový stupeň' řádky 1..12 a v prvním řádku nad sloupci 1..16.
    # Snaží se automaticky najít správný list.
    try:
        xl = pd.ExcelFile(ods_path, engine="odf")
    except Exception as e:
        print("Soubor nelze otevřít přes pandas/odf. Ujistěte se, že máte 'odfpy'.", file=sys.stderr)
        raise

    for sheet in xl.sheet_names:
        try:
            df = pd.read_excel(ods_path, sheet_name=sheet, engine="odf")
        except Exception:
            continue

        if df.empty or df.shape[1] < 10 or df.shape[0] < 5:
            continue

        # Tato ODS má sloupec 'Platovýstupeň' a čísla tříd v řádku 0 přes sloupce 2..
        try:
            header_row = df.iloc[0, 2:]
            classes = []
            for val in header_row:
                try:
                    classes.append(int(val))
                except Exception:
                    classes.append(None)
            if sum(1 for c in classes if isinstance(c, int)) < 5:
                continue
            class_to_col = {}
            for idx, cls in enumerate(classes, start=2):
                if isinstance(cls, int):
                    class_to_col[cls] = df.columns[idx]
            row_12 = df[df.iloc[:, 0] == 12]
            if row_12.empty:
                row_12 = df[df.iloc[:, 0] == 12.0]
            if row_12.empty:
                continue
            row_12 = row_12.iloc[0]

            maxima = {}
            for cls, col in class_to_col.items():
                try:
                    v = row_12[col]
                    if pd.isna(v):
                        continue
                    maxima[int(cls)] = int(float(v))
                except Exception:
                    continue

            if len([k for k in maxima.keys() if 1 <= k <= 16]) >= 10:
                return maxima
        except Exception:
            continue

    raise RuntimeError("Nepodařilo se automaticky najít tabulku s třídami/stupni v ODS.")

def prompt_float(prompt: str, min_val: float, max_val: float) -> float:
    while True:
        s = input(prompt).strip().replace(",", ".")
        try:
            v = float(s)
        except ValueError:
            print("Zadejte číslo.")
            continue
        if not (min_val <= v <= max_val):
            print(f"Hodnota musí být v intervalu <{min_val}; {max_val}>.")
            continue
        return v

def prompt_int(prompt: str, valid: set) -> int:
    while True:
        s = input(prompt).strip()
        if not s.isdigit():
            print("Zadejte celé číslo.")
            continue
        v = int(s)
        if v not in valid:
            print(f"Povoleny hodnoty: {sorted(valid)}")
            continue
        return v

def main():
    script_dir = Path(__file__).resolve().parent
    if len(sys.argv) >= 2:
        ods_path = Path(sys.argv[1]).expanduser()
    else:
        ods_path = script_dir / ODS_FILENAME_DEFAULT

    if not ods_path.exists():
        print(f"Soubor s tabulkou nenalezen: {ods_path}", file=sys.stderr)
        print("Spusťte skript ze stejné složky jako ODS, nebo zadejte cestu jako argument.")
        sys.exit(2)

    try:
        maxima = load_class_maxima(ods_path)
    except Exception as e:
        print(f"Chyba při načítání ODS: {e}", file=sys.stderr)
        sys.exit(3)

    print("Výpočet osobního příplatku podle tabulek v souboru:", ods_path.name)
    cls = prompt_int("Zadejte platovou třídu (1–16): ", set(range(1, 17)))
    if cls not in maxima:
        print(f"Třída {cls} v tabulce nenalezena.", file=sys.stderr)
        sys.exit(4)

    fte = prompt_float("Zadejte výši úvazku v % (např. 100 nebo 80): ", 1.0, 200.0)
    perc = prompt_float("Zadejte zvolenou výši osobního příplatku v % (0–100): ", 0.0, 100.0)

    max_allowed = maxima[cls]
    amount = max_allowed * (perc / 100.0) * (fte / 100.0)

    print("\n--- Výsledek ---")
    print(f"Platová třída: {cls}")
    print(f"Max. základ (100 % z 12. stupně): {fmt_kc(max_allowed)}")
    print(f"Zvolená výše osobního příplatku(z max 100%): {perc:.2f} %")
    print(f"Úvazek: {fte:.2f} %")
    print(f"Vypočtená částka osobního příplatku: {fmt_kc(amount)} / měsíc")
    print("----------------")

if __name__ == "__main__":
    main()
