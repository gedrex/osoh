
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import os
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

try:
    import pandas as pd
except Exception as e:
    raise SystemExit("Chybí knihovna pandas. Nainstalujte: pip install pandas odfpy")

APP_TITLE = "Výpočet osobního příplatku (veřejný sektor)"
DEFAULT_ODS = "platove-tabulky-2025.ods"

def resource_path(relative: str) -> Path:
    """Cesta k souboru v běžném běhu i v PyInstaller .exe (sys._MEIPASS)."""
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / relative  # type: ignore[attr-defined]
    return Path(relative)

def find_ods_path() -> Path | None:
    here = Path(getattr(sys, "frozen", False) and sys.executable or __file__).resolve().parent
    cand = here / DEFAULT_ODS
    if cand.exists():
        return cand
    cand = resource_path(DEFAULT_ODS)
    if cand.exists():
        return cand
    return None

def load_class_maxima(ods_path: Path) -> dict[int, int]:
    xl = pd.ExcelFile(ods_path, engine="odf")
    for sheet in xl.sheet_names:
        try:
            df = pd.read_excel(ods_path, sheet_name=sheet, engine="odf")
        except Exception:
            continue
        if df.empty or df.shape[1] < 10 or df.shape[0] < 5:
            continue
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
    raise RuntimeError("Nepodařilo se najít tabulku tříd/stupňů v ODS.")

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.resizable(False, False)

        self.ods_path: Path | None = find_ods_path()
        self.maxima: dict[int, int] | None = None

        frm = ttk.Frame(self, padding=12)
        frm.grid(row=0, column=0, sticky="nsew")

        ttk.Label(frm, text="Soubor s tabulkou:").grid(row=0, column=0, sticky="w")
        self.ods_var = tk.StringVar(value=str(self.ods_path) if self.ods_path else "")
        self.ods_entry = ttk.Entry(frm, textvariable=self.ods_var, width=45)
        self.ods_entry.grid(row=0, column=1, sticky="we", padx=(6,6))
        ttk.Button(frm, text="Vybrat…", command=self.pick_file).grid(row=0, column=2, sticky="we")

        ttk.Label(frm, text="Platová třída (1–16):").grid(row=1, column=0, sticky="w", pady=(8,0))
        self.class_var = tk.StringVar()
        self.class_combo = ttk.Combobox(frm, textvariable=self.class_var, values=[str(i) for i in range(1,17)], width=10, state="readonly")
        self.class_combo.grid(row=1, column=1, sticky="w", padx=(6,6), pady=(8,0))
        self.class_combo.current(11)  # 12

        ttk.Label(frm, text="Úvazek (%):").grid(row=2, column=0, sticky="w", pady=(8,0))
        self.fte_var = tk.StringVar(value="100")
        self.fte_entry = ttk.Entry(frm, textvariable=self.fte_var, width=10)
        self.fte_entry.grid(row=2, column=1, sticky="w", padx=(6,6), pady=(8,0))

        ttk.Label(frm, text="Osobní příplatek (%):").grid(row=3, column=0, sticky="w", pady=(8,0))
        self.perc_var = tk.StringVar(value="0")
        self.perc_entry = ttk.Entry(frm, textvariable=self.perc_var, width=10)
        self.perc_entry.grid(row=3, column=1, sticky="w", padx=(6,6), pady=(8,0))

        btns = ttk.Frame(frm)
        btns.grid(row=4, column=0, columnspan=3, sticky="we", pady=(12,0))
        ttk.Button(btns, text="Spočítat", command=self.calculate).grid(row=0, column=0, padx=(0,6))
        ttk.Button(btns, text="Konec", command=self.destroy).grid(row=0, column=1)

        self.result = tk.Text(frm, width=56, height=6, state="disabled")
        self.result.grid(row=5, column=0, columnspan=3, pady=(10,0))

        frm.columnconfigure(1, weight=1)

        if self.ods_path:
            self.load_maxima(self.ods_path)

    def pick_file(self):
        path = filedialog.askopenfilename(title="Vybrat ODS", filetypes=[("OpenDocument Spreadsheet", "*.ods"), ("All files", "*.*")])
        if path:
            self.ods_var.set(path)
            self.load_maxima(Path(path))

    def load_maxima(self, path: Path):
        try:
            self.maxima = load_class_maxima(path)
            self.write_result(f"Načteno z: {path.name}\nTřídy dostupné: {', '.join(map(str, sorted(self.maxima.keys())))}")
        except Exception as e:
            messagebox.showerror("Chyba", f"Načtení tabulky selhalo:\n{e}")
            self.maxima = None

    def fmt_kc(self, x: float) -> str:
        try:
            return f"{x:,.0f} Kč".replace(",", " ")
        except Exception:
            return f"{int(round(x))} Kč"

    def write_result(self, text: str):
        self.result.configure(state="normal")
        self.result.delete("1.0", "end")
        self.result.insert("end", text)
        self.result.configure(state="disabled")

    def calculate(self):
        if not self.maxima:
            p = Path(self.ods_var.get())
            if p.exists():
                try:
                    self.maxima = load_class_maxima(p)
                except Exception as e:
                    messagebox.showerror("Chyba", f"Načtení tabulky selhalo:\n{e}")
                    return
            else:
                messagebox.showwarning("Chybí soubor", "Nejdřív vyberte platný .ods soubor s tabulkou.")
                return
        try:
            cls = int(self.class_var.get())
            if cls not in self.maxima:
                raise ValueError
        except Exception:
            messagebox.showwarning("Neplatná třída", "Zadejte třídu v rozmezí 1–16.")
            return
        try:
            fte = float(self.fte_var.get().replace(",", "."))
            if not (1.0 <= fte <= 200.0):
                raise ValueError
        except Exception:
            messagebox.showwarning("Neplatný úvazek", "Zadejte úvazek v % (1–200).")
            return
        try:
            perc = float(self.perc_var.get().replace(",", "."))
            if not (0.0 <= perc <= 100.0):
                raise ValueError
        except Exception:
            messagebox.showwarning("Neplatné % příplatku", "Zadejte osobní příplatek v % (0–100).")
            return
        max_allowed = self.maxima[cls]
        amount = max_allowed * (perc / 100.0) * (fte / 100.0)
        text = (
            f"Platová třída: {cls}\n"
            f"Max. základ (100 % z 12. stupně): {self.fmt_kc(max_allowed)}\n"
            f"Osobní příplatek: {perc:.2f} %\n"
            f"Úvazek: {fte:.2f} %\n"
            f"Vypočtená částka: {self.fmt_kc(amount)} / měsíc"
        )
        self.write_result(text)

if __name__ == "__main__":
    app = App()
    app.mainloop()
