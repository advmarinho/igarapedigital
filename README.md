# 🦷📄 Igarapé Digital – Extrator PDF Saúde/Odonto para Excel

**Desenvolvido por:** [Anderson Marinho](https://github.com/advmarinho)  
**Tecnologias:** Python, CustomTkinter, pdfplumber, Pandas  
**Licença:** MIT

---

## 📌 Visão Geral

Este projeto tem como objetivo automatizar a **extração de dados de faturas em PDF** da **Porto Seguro Saúde e Odonto**, convertendo-as diretamente em arquivos **Excel (.xlsx)** de forma organizada, limpa e estruturada para análise, conciliação e auditoria.

A aplicação possui uma **interface gráfica moderna e simples**, feita com `CustomTkinter`, e atende a dois tipos de documentos:

- 📑 **Faturas de Saúde**
- 🦷 **Faturas de Odontologia**

---

## 🎯 Funcionalidades

✔️ Importação de PDFs da Porto Seguro  
✔️ Reconhecimento inteligente por expressões regulares  
✔️ Extração robusta dos campos: Nome, CPF, Plano, Rubrica, Valores, IOF, etc.  
✔️ Cálculo automático de totais familiares (saúde)  
✔️ Interface com barra de progresso  
✔️ Exportação automática para Excel (.xlsx)

---

## 🛠️ Como usar

### 1. Clone o repositório

```bash
git clone https://github.com/advmarinho/igarape-pdf-extractor.git
cd igarape-pdf-extractor
```

### 2. Instale os requisitos

Use um ambiente virtual se desejar:

```bash
pip install -r requirements.txt
```

**Requisitos principais:**
- `customtkinter`
- `pdfplumber`
- `pandas`

### 3. Execute o aplicativo

```bash
python app.py
```

### 4. Selecione o tipo de fatura

- Clique em **"Importar Saúde"** ou **"Importar Odonto"**
- Escolha o arquivo PDF
- Escolha onde salvar o Excel gerado

---

## 🧪 Exemplo de uso

| Campo              | Exemplo                      |
|-------------------|------------------------------|
| Nome              | NOME SOBRENOME               |
| CPF               | 123.456.789-00               |
| Plano             | OPERADORA APTO               |
| Tp                | Titular / Dependente         |
| Rubrica           | Mensalidade / Total Prêmio   |
| Valor             | R$ 89,32                     |
| Valor Total       | R$ 125,50                    |
| IOF               | R$ 2,21                      |

---

## 🧩 Estrutura do Projeto

```plaintext
📁 igarape-pdf-extractor/
│
├── app.py               # Código principal (interface + lógica)
├── README.md            # Este documento
├── requirements.txt     # Dependências do projeto
└── exemplos/            # PDFs de exemplo (não incluídos por privacidade)
```

---

## 📚 Sobre os layouts

### Seguro Saúde
- Os blocos começam após `Seguro Dep`
- Utiliza duas expressões regex para variações de layout
- Calcula total familiar via soma ou campo explícito

### Seguro Odonto
- Tenta regex robusto com campos nomeados
- Em fallback, usa regex alternativo mais flexível
- Captura IOF por rubrica em blocos posteriores

---

## 📈 Aplicações práticas

- Auditoria de valores cobrados por plano
- Comparação entre fatura, folha e boleto
- Detecção de coparticipações elevadas
- Análise de comportamento familiar em uso do plano

---

## 🧑‍💻 Desenvolvedor

**Anderson Marinho**  
- Especialista em Departamento Pessoal  
- Advogado | Automação em RH | Python Developer  
- Projeto: [Igarapé Digital](https://github.com/advmarinho)

---

## 📄 Licença

Este projeto está sob a licença [MIT](LICENSE).

---

## 🙌 Agradecimentos

Este app foi desenvolvido com dedicação para auxiliar profissionais de RH, financeiro, auditoria e saúde corporativa a tomarem decisões com mais dados, menos retrabalho e mais segurança jurídica.

---

> “Digitalizar é libertar o tempo para focar nas pessoas.”  
> — *Igarapé Digital*
