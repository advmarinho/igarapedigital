import os
import re
import itertools
import pdfplumber
import pandas as pd
import customtkinter as ctk
from tkinter import filedialog, messagebox

# ---------------------- EXPRESSÕES REGULARES - SAÚDE ----------------------------
RE_HEADER_SAUDE = re.compile(r"""
    ^\s*
    (?:(?P<seguro>\d{8})\s+)?             
    (?P<dep>\d{1,2})\s+                   
    (?P<nome>[A-ZÀ-Ü][^\d\n]+?)           
    \s*
    (?P<reg_func>\d{4,7})?                
    \s+
    (?P<idade>\d{1,3})\s+                 
    (?P<parentesco>Titular|Conjuge|Filh[oa])
    """, re.MULTILINE | re.VERBOSE
)

RE_HEADER_SAUDE_ALT = re.compile(r"""
    ^\s*
    (?:(?P<seguro>\d{7,9})\s+)?             
    (?P<dep>\d{1,2})\s+                   
    (?P<nome>[A-ZÀ-Üa-zà-ü\s\.'\-]+?)           
    \s*
    (?P<reg_func>\d{4,8})?                
    \s+
    (?P<idade>\d{1,3})\s+                 
    (?P<parentesco>Titular|Conjuge|Filh[oa]|filho|filha)
    """, re.MULTILINE | re.VERBOSE
)

VAL = r"(?P<val>\d[\d\.]*,\d{2})"
RE_VALS_SAUDE = {
    "premio_base": re.compile(r"Prêmio\s+Base\s*" + VAL),
    "desc_copart": re.compile(r"(Desc(?:onto)?\s+por\s+Co[- ]?Part(?:\.|icipação)?\s*\(-?\))?\s*" + VAL),
    "total_copart": re.compile(r"Total\s+Co[- ]?Part\.\s*R?\$?\s*" + VAL),
    "consultas": re.compile(r"CONSULTAS[^\d]*" + VAL),
    "exames": re.compile(r"EXAMES[^\d]*" + VAL),
    "pronto_socorro": re.compile(r"PRONTO[-\s]?SOCORRO[^\d]*" + VAL),
    "pro_rata": re.compile(r"Pro[-\s]?Rata[^\d]*" + VAL),
    "iof": re.compile(r"\bIOF\s*" + VAL),
    "total_dep": re.compile(r"TOTAL\s+DO\s+DEP\.\s*" + VAL),
}

# ---------------------- UTILIDADES ----------------------------
def to_float(s: str | None) -> float | None:
    if not s: return None
    return float(s.replace(".", "").replace(",", "."))

def extrair_tabela_seguro(txt: str) -> str | None:
    padroes = [
        r"Seguro\s+Dep",
        r"Seguro\s*:\s*Dep",
        r"N[oº]?\s*Seguro\s+Dep"
    ]
    for padrao in padroes:
        if re.search(padrao, txt):
            return re.split(padrao, txt, maxsplit=1)[-1]
    return None

# ---------------------- PROCESSAMENTO SAÚDE ----------------------------
def processar_saude(pdf_path: str) -> pd.DataFrame:
    blocos = []
    with pdfplumber.open(pdf_path) as pdf:
        for pg in pdf.pages:
            txt = pg.extract_text() or ""
            tbl = extrair_tabela_seguro(txt)
            if tbl:
                blocos.append(tbl)

    registros = []
    for texto in blocos:
        matches = list(RE_HEADER_SAUDE.finditer(texto))
        if not matches:
            matches = list(RE_HEADER_SAUDE_ALT.finditer(texto))

        total_matches = list(re.finditer(r"TOTAL\.\s*(\d[\d\.]*,\d{2})", texto))

        for m, nxt in zip(matches, itertools.chain(matches[1:], [None])):
            d = m.groupdict()
            corpo = texto[m.end():nxt.start() if nxt else len(texto)]

            for campo, rx in RE_VALS_SAUDE.items():
                mm = rx.search(corpo)
                d[campo] = to_float(mm["val"]) if mm else None

            if d.get("iof") is None:
                mm_all = re.findall(RE_VALS_SAUDE["iof"], corpo)
                if mm_all:
                    d["iof"] = max(map(to_float, mm_all))
            d["_start"] = m.start()
            registros.append(d)

        for tm in total_matches:
            total_val = to_float(tm.group(1))
            candidatos = [r for r in registros if r.get("parentesco", "") == "Titular" and r["_start"] < tm.start()]
            if candidatos:
                candidatos[-1]["_total"] = total_val

    df = pd.DataFrame(registros)
    if df.empty: return df

    df["seguro"] = df["seguro"].ffill()
    df["dep"] = df["dep"].astype(int)
    df["idade"] = df["idade"].astype(int)
    df["seguro"] = df["seguro"].astype(str)

    df["total_familiar"] = df.get("_total")
    if df["total_familiar"].isnull().all():
        total_agrupado = df.groupby(["seguro"]).agg({"total_dep": "sum"}).reset_index()
        df = df.merge(total_agrupado, on="seguro", suffixes=("", "_agrupado"))
        df["total_familiar"] = df["total_dep_agrupado"]
        df.drop(columns=["total_dep_agrupado"], inplace=True)

    df.drop(columns=["_start", "_total"], errors="ignore", inplace=True)

    num_cols = [c for c in df.columns if c not in {"seguro", "dep", "nome", "idade", "parentesco", "reg_func"}]
    df[num_cols] = df[num_cols].fillna(0.0).infer_objects()
    df.columns = [col.capitalize().replace("_", " ") for col in df.columns]
    return df.sort_values(["Seguro", "Dep"])

# ---------------------- STUB ODONTO ----------------------------
def processar_odonto(pdf_path: str) -> pd.DataFrame:
    return pd.DataFrame()

# ---------------------- INTERFACE ----------------------------
class InterfaceApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Igarapé Digital – PDF → Excel")
        self.geometry("500x350")
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        ctk.CTkLabel(self, text="Importar Faturas Saúde / Odonto", font=("Arial", 20)).pack(pady=20)

        ctk.CTkButton(self, text="📥 Importar Saúde", command=lambda: self.executar("saude")).pack(pady=10)
        ctk.CTkButton(self, text="📥 Importar Odonto", command=lambda: self.executar("odonto")).pack(pady=10)

        self.progress = ctk.CTkProgressBar(self, mode="indeterminate")
        self.progress.pack(pady=20)
        self.progress.stop()
        self.progress.pack_forget()

        ctk.CTkLabel(self, text="CustomerThink | Igarapé Digital", font=("Arial", 12)).pack(side="bottom", pady=15)

    def mostrar_progresso(self):
        self.progress.pack(pady=20)
        self.progress.start()

    def esconder_progresso(self):
        self.progress.stop()
        self.progress.pack_forget()

    def executar(self, tipo):
        self.mostrar_progresso()
        self.after(100, lambda: self.processar_e_salvar(tipo))

    def processar_e_salvar(self, tipo):
        path = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        if not path:
            self.esconder_progresso()
            return

        try:
            df = processar_saude(path) if tipo == "saude" else processar_odonto(path)
            if df.empty:
                raise ValueError("Nenhum dado encontrado no PDF.")

            nome_padrao = os.path.splitext(os.path.basename(path))[0] + ".xlsx"
            save_path = filedialog.asksaveasfilename(defaultextension=".xlsx",
                                                     initialfile=nome_padrao,
                                                     filetypes=[("Excel files", "*.xlsx")],
                                                     title="Salvar como")
            if not save_path:
                self.esconder_progresso()
                return

            df.to_excel(save_path, index=False)
            messagebox.showinfo("Sucesso", f"Excel salvo com sucesso:\n{save_path}")
        except Exception as e:
            try:
                messagebox.showerror("Erro", str(e))
            except:
                print("Erro fatal:", str(e))
        finally:
            self.esconder_progresso()

# ---------------------- RUN ----------------------------
if __name__ == "__main__":
    app = InterfaceApp()
    app.mainloop()