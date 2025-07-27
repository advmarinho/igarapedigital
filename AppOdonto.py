import os
import re
import pdfplumber
import pandas as pd
import customtkinter as ctk
from tkinter import filedialog, messagebox

# ---------------------- UTILIDADES ----------------------------
def to_float(s: str | None) -> float | None:
    """Converte '1.234,56' para 1234.56."""
    return float(s.replace(".", "").replace(",", ".")) if s else None

# ---------------------- EXPRESSÕES REGULARES ----------------------------
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
    (?P<num>\d+)\s+                                      # N° Beneficiário
    (?P<nome>[^0-9\n]+?)\s*(?P<matricula>\d+)\s+         # Nome + Matrícula
    (?P<cpf>\d{3}\.\d{3}\.\d{3}-\d{2})\s+                # CPF
    (?P<plano>.+?)(?=\s+[TD]\s+\d+)\s+                   # Plano (até Tp)
    (?P<tp>[TD])\s+                                      # Tp (T/D)
    (?P<id>\d+)\s+                                       # Id interno
    (?:(?P<dependencia>Conjuge|Filh[oa])\s+)?            # Dependência
    (?P<dt_inclusao>\d{2}/\d{2}/\d{4})\s+                # Dt Inclusão
    (?P<rubrica>.+?)\s+                                  # Rubrica
    (?P<valor>\d[\d\.]*,\d{2})                           # Valor da rubrica
    (?:\s+(?P<valor_total>\d[\d\.]*,\d{2}))?             # Valor Total (só Titulares)
""", re.MULTILINE | re.VERBOSE)

RE_IOF = re.compile(r"Cobran[çc]a de IOF[^\d]*(?P<iof>\d[\d\.]*,\d{2})")


# ---------------------- PROCESSAMENTO ----------------------------
def processar_odonto(pdf_path: str) -> pd.DataFrame:
    registros = []
    with pdfplumber.open(pdf_path) as pdf:
        texto = "\n".join(page.extract_text() or "" for page in pdf.pages)

    texto = re.sub(
        r'([A-ZÀ-Üa-zà-ü])\n(?=\d{3}\.\d{3}\.\d{3}-\d{2})',
        r'\1 ',
        texto
    )

    # Primeiro tenta o regex seguro
    detalhes = list(RE_ODONTO_SEGURO.finditer(texto))

    if not detalhes:
        print("⚠️ Layout inesperado. Tentando regex alternativo (menos seguro).")
        detalhes = list(RE_ODONTO.finditer(texto))

    if not detalhes:
        raise ValueError("❌ Nenhum dado encontrado com os padrões conhecidos. Layout pode ter mudado.")

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

    df["num"]         = df["num"].astype(int)
    df["matricula"]   = df["matricula"].astype(int)
    df["id"]          = df["id"].astype(int)
    df["Dt Inclusão"] = pd.to_datetime(df["dt_inclusao"], dayfirst=True).dt.date

    df["Valor"]       = df["valor"].map(to_float)
    df["Valor Total"] = df["valor_total"].map(to_float)
    df["IOF"]         = df["iof"].astype(float)

    df["Tp"]          = df["tp"].map({"T": "Titular", "D": "Dependente"})
    df["Dependência"] = df["dependencia"].fillna("Titular")

    df.rename(columns={
        "num":       "N° Beneficiário",
        "nome":      "Nome",
        "matricula": "Matrícula",
        "cpf":       "CPF",
        "plano":     "Plano",
        "rubrica":   "Rubrica",
        "id":        "Id"
    }, inplace=True)

    cols = [
        "N° Beneficiário", "Nome", "Matrícula", "CPF", "Plano",
        "Tp", "Id", "Dependência", "Dt Inclusão",
        "Rubrica", "Valor", "Valor Total", "IOF"
    ]
    return df[cols].sort_values("N° Beneficiário")


# ---------------------- INTERFACE CUSTOMTKINTER ----------------------------
class OdontoApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Igarapé Digital – Odonto → Excel")
        self.geometry("520x320")
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("dark-blue")

        ctk.CTkLabel(self, text="📄 Extrair Fatura Odonto", font=("Arial", 20)).pack(pady=(30, 10))
        ctk.CTkButton(self, text="📥 Selecionar PDF", command=self.executar).pack(pady=10)

        self.progress = ctk.CTkProgressBar(self, mode="indeterminate")
        self.progress.pack(pady=20)
        self.progress.stop()
        self.progress.pack_forget()

        ctk.CTkLabel(self, text="CustomerThink | Igarapé Digital", font=("Arial", 12)).pack(side="bottom", pady=10)

    def mostrar_progresso(self):
        self.progress.pack(pady=20)
        self.progress.start()

    def esconder_progresso(self):
        self.progress.stop()
        self.progress.pack_forget()

    def executar(self):
        self.mostrar_progresso()
        self.after(100, self.processar_salvar)

    def processar_salvar(self):
        path = filedialog.askopenfilename(
            title="Selecione o PDF de Odonto",
            filetypes=[("PDF files", "*.pdf")]
        )
        if not path:
            self.esconder_progresso()
            return

        try:
            df = processar_odonto(path)
            if df.empty:
                raise ValueError("Nenhum registro de Odonto encontrado.")

            nome_xlsx = os.path.splitext(os.path.basename(path))[0] + "_odonto.xlsx"
            save_path = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                initialfile=nome_xlsx,
                filetypes=[("Excel files", "*.xlsx")],
                title="Salvar como"
            )
            if not save_path:
                self.esconder_progresso()
                return

            df.to_excel(save_path, index=False)
            messagebox.showinfo("Sucesso", f"Excel salvo em:\n{save_path}")

        except Exception as e:
            messagebox.showerror("Erro", str(e))
        finally:
            self.esconder_progresso()


# ---------------------- EXECUÇÃO ----------------------------
if __name__ == "__main__":
    app = OdontoApp()
    app.mainloop()
