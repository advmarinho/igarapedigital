import customtkinter as ctk
from tkinter import filedialog, messagebox
import cv2
import pytesseract
import os
import re
import numpy as np
import pandas as pd
from pdf2image import convert_from_path
from PIL import Image

pytesseract.pytesseract.tesseract_cmd = r"/usr/bin/tesseract"

class OCRDinamicoApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("OCR Adaptativo - Documentos")
        self.geometry("920x740")
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")

        self.dados_extraidos = []

        botoes = ctk.CTkFrame(self)
        botoes.pack(fill="x", padx=10, pady=(10, 0))
        ctk.CTkButton(botoes, text="Selecionar Arquivo", command=self.select_file).pack(side="left", padx=5)
        ctk.CTkButton(botoes, text="Extrair Dados", command=self.extract_adaptive).pack(side="left", padx=5)
        ctk.CTkButton(botoes, text="Exportar Excel", command=self.export_excel).pack(side="left", padx=5)
        self.lbl_path = ctk.CTkLabel(botoes, text="Nenhum arquivo selecionado")
        self.lbl_path.pack(side="left", padx=20)

        tabs = ctk.CTkTabview(self)
        tabs.pack(fill="both", expand=True, padx=10, pady=10)
        self.tab_ocr = tabs.add("Texto OCR Bruto")
        self.tab_campos = tabs.add("Campos Extraídos")

        self.txt_ocr = ctk.CTkTextbox(self.tab_ocr, width=880, height=630)
        self.txt_ocr.pack(fill="both", expand=True, padx=10, pady=10)

        self.txt_result = ctk.CTkTextbox(self.tab_campos, width=880, height=630)
        self.txt_result.pack(fill="both", expand=True, padx=10, pady=10)

        self.file_path = None

    def select_file(self):
        path = filedialog.askopenfilename(title="Escolha o PDF ou imagem",
                                          filetypes=[("PDF ou Imagem", "*.pdf *.png *.jpg *.jpeg *.tiff *.bmp")])
        if path:
            self.file_path = path
            self.lbl_path.configure(text=os.path.basename(path))

    def preprocess_image(self, img):
        gray = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2GRAY)
        denoised = cv2.fastNlMeansDenoising(gray, h=10)
        _, binary = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return binary

    def extract_text_from_images(self):
        ext = os.path.splitext(self.file_path)[1].lower()
        pages = []
        pil_imgs = convert_from_path(self.file_path, dpi=400) if ext == ".pdf" else [Image.open(self.file_path)]

        for pil in pil_imgs:
            proc = self.preprocess_image(pil)
            text = pytesseract.image_to_string(proc, lang='por', config='--psm 3')
            pages.append(text)
        return pages

    def gerar_regex_dinamico(self, texto_ocr):
        texto = texto_ocr.upper().replace('\n', ' ')
        resultados = {}
        padroes = {
            "CPF": r"(\d{3}\.\d{3}\.\d{3}-\d{2})",
            "RG": r"(\d{1,2}\.\d{3}\.\d{3}-[\dX])",
            "Data Nascimento": r"(\d{2}/\d{2}/\d{4})",
            "Nome": r"NOME[:\-]?\s*([A-ZÀ-Ú\s]+)",
            "Órgão Expedidor": r"ÓRGÃO EXPEDIDOR[:\-]?\s*([A-ZÀ-Ú\s]+)",
            "Filiação": r"FILIAÇÃO[:\-]?\s*([A-ZÀ-Ú\s]+)"
        }
        for campo, padrao in padroes.items():
            match = re.search(padrao, texto)
            if match:
                resultados[campo] = match.group(1).strip()
        return resultados

    def extract_adaptive(self):
        if not self.file_path:
            messagebox.showwarning("Aviso", "Selecione um arquivo primeiro.")
            return

        self.txt_ocr.delete("0.0", "end")
        self.txt_result.delete("0.0", "end")
        self.dados_extraidos.clear()

        paginas_texto = self.extract_text_from_images()
        all_ocr, campos_texto = [], []

        for idx, texto in enumerate(paginas_texto, 1):
            all_ocr.append(f"--- Página {idx} ---\n{texto.strip()}")
            resultados = self.gerar_regex_dinamico(texto)

            resultado_formatado = [f"--- Página {idx} ---"]
            resultado_dict = {"Arquivo": os.path.basename(self.file_path), "Página": idx}

            for campo, valor in resultados.items():
                resultado_formatado.append(f"{campo}: {valor}")
                resultado_dict[campo] = valor

            campos_texto.append("\n".join(resultado_formatado))
            self.dados_extraidos.append(resultado_dict)

        self.txt_ocr.insert("0.0", "\n\n".join(all_ocr))
        self.txt_result.insert("0.0", "\n\n".join(campos_texto))

    def export_excel(self):
        if not self.dados_extraidos:
            messagebox.showwarning("Nada a exportar", "Execute a extração primeiro.")
            return
        caminho = filedialog.asksaveasfilename(defaultextension=".xlsx",
                                               filetypes=[("Planilha Excel", "*.xlsx")])
        if caminho:
            df = pd.DataFrame(self.dados_extraidos)
            df.to_excel(caminho, index=False)
            messagebox.showinfo("Sucesso", f"Exportado com sucesso:\n{caminho}")

if __name__ == "__main__":
    app = OCRDinamicoApp()
    app.mainloop()
