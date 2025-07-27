import os
import re
import itertools
import pdfplumber
import pandas as pd
import customtkinter as ctk
from tkinter import filedialog, messagebox

# ---------------------- UTILIDADES ----------------------------
def to_float(s: str | None) -> float | None:
    if not s: return None
    return float(s.replace(".", "").replace(",", "."))

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

# ---------------------- EXPRESSÕES ODONTO ----------------------------
RE_ODONTO_SEGURO = re.compile(r"""
    ^\s*
    (?P<num>\d{1,6})\s+
    (?P<nome>[A-ZÀ-Ü][^\d\n]+?)\s+
    (?P<matricula>\d+)\s+
    (?P<cpf>\d{3}\.\d{3}\.\d{3}-\d{2})\s+
    (?P<plano>[A-ZÀ-Ü\s\/\-]+(?:DOC)?(?:\s+\d{1,2})?)\s+
    (?P<tp>[TD])\s+
    (?P<id>\d+)\s+
    (?:(?P<dependencia>Conjuge|Filh[oa]|Enteada?)\s+)?
    (?P<dt_inclusao>\d{2}/\d{2}/\d{4})\s+
    (?P<rubrica>(Total|Mensalidades?)\s+[\wÀ-Ü\s\-\/]+?)\s+
    (?P<valor>\d[\d\.]*,\d{2})
    (?:\s+(?P<valor_total>\d[\d\.]*,\d{2}))?
    \s*$
""", re.MULTILINE | re.VERBOSE)

RE_ODONTO = re.compile(r"""
    ^\s*
    (?P<num>\d+)\s+
    (?P<nome>[^0-9\n]+?)\s*(?P<matricula>\d+)\s+
    (?P<cpf>\d{3}\.\d{3}\.\d{3}-\d{2})\s+
    (?P<plano>.+?)(?=\s+[TD]\s+\d+)\s+
    (?P<tp>[TD])\s+
    (?P<id>\d+)\s+
    (?:(?P<dependencia>Conjuge|Filh[oa])\s+)?
    (?P<dt_inclusao>\d{2}/\d{2}/\d{4})\s+
    (?P<rubrica>.+?)\s+
    (?P<valor>\d[\d\.]*,\d{2})
    (?:\s+(?P<valor_total>\d[\d\.]*,\d{2}))?
""", re.MULTILINE | re.VERBOSE)

RE_IOF = re.compile(r"Cobran[çc]a de IOF[^\d]*(?P<iof>\d[\d\.]*,\d{2})")

def processar_odonto(pdf_path: str) -> pd.DataFrame:
    registros = []
    with pdfplumber.open(pdf_path) as pdf:
        texto = "\n".join(page.extract_text() or "" for page in pdf.pages)

    texto = re.sub(
        r'([A-ZÀ-Üa-zà-ü])\n(?=\d{3}\.\d{3}\.\d{3}-\d{2})',
        r'\1 ',
        texto
    )

    detalhes = list(RE_ODONTO_SEGURO.finditer(texto))
    if not detalhes:
        detalhes = list(RE_ODONTO.finditer(texto))

    if not detalhes:
        raise ValueError("❌ Nenhum dado encontrado no PDF Odonto.")

    for idx, m in enumerate(detalhes):
        d = m.groupdict()
        inicio = m.end()
        fim = detalhes[idx + 1].start() if idx + 1 < len(detalhes) else len(texto)
        snippet = texto[inicio:fim]
        mi = RE_IOF.search(snippet)
        d["iof"] = to_float(mi.group("iof")) if mi else 0.0
        registros.append(d)

    df = pd.DataFrame(registros)
    if df.empty:
        return df

    df["num"] = df["num"].astype(int)
    df["matricula"] = df["matricula"].astype(int)
    df["id"] = df["id"].astype(int)
    df["Dt Inclusão"] = pd.to_datetime(df["dt_inclusao"], dayfirst=True).dt.date
    df["Valor"] = df["valor"].map(to_float)
    df["Valor Total"] = df["valor_total"].map(to_float)
    df["IOF"] = df["iof"].astype(float)
    df["Tp"] = df["tp"].map({"T": "Titular", "D": "Dependente"})
    df["Dependência"] = df["dependencia"].fillna("Titular")

    df.rename(columns={
        "num": "N° Beneficiário", "nome": "Nome", "matricula": "Matrícula",
        "cpf": "CPF", "plano": "Plano", "rubrica": "Rubrica", "id": "Id"
    }, inplace=True)

    cols = [
        "N° Beneficiário", "Nome", "Matrícula", "CPF", "Plano", "Tp", "Id",
        "Dependência", "Dt Inclusão", "Rubrica", "Valor", "Valor Total", "IOF"
    ]
    return df[cols].sort_values("N° Beneficiário")

# ---------------------- INTERFACE UNIFICADA ----------------------------
class InterfaceApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Igarapé Digital – PDF to Excel - Anderson Marinho")
        self.geometry("520x360")
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        ctk.CTkLabel(self, text="📥 Extrair Faturas Saúde / Odonto PDF to EXCEL", font=("Arial", 20)).pack(pady=20)
        ctk.CTkButton(self, text="📥 Importar Saúde", command=lambda: self.executar("saude")).pack(pady=8)
        ctk.CTkButton(self, text="📥 Importar Odonto", command=lambda: self.executar("odonto")).pack(pady=8)

        self.progress = ctk.CTkProgressBar(self, mode="indeterminate")
        self.progress.pack(pady=20)
        self.progress.stop()
        self.progress.pack_forget()

        ctk.CTkLabel(self, text="CustomerThink | Igarapé Digital | Github-Advmarinho", font=("Arial", 12)).pack(side="bottom", pady=15)

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

            nome_padrao = os.path.splitext(os.path.basename(path))[0] + f"_{tipo}.xlsx"
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
            messagebox.showerror("Erro", str(e))
        finally:
            self.esconder_progresso()

# ---------------------- RUN ----------------------------
if __name__ == "__main__":
    app = InterfaceApp()
    app.mainloop()
