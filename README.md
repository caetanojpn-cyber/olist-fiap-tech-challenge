# Olist | Tech Challenge FIAP — Fase 1

Projeto de análise comercial e operacional do marketplace Olist, com apresentação executiva e código reproduzível.

## Entregáveis

- `presentation_html/`: apresentação interativa em HTML, CSS e JavaScript. Abra `index.html` no navegador para visualizar.
- `src/analysis.py`: pipeline de análise dos dados.
- `presentation_html/build_data.py`: geração do conjunto de dados utilizado pelos gráficos.
- `data/`: bases de entrada utilizadas no projeto.
- `outputs/`: resultados tabulares e dados consolidados dos gráficos.

## Como visualizar a apresentação

Abra `presentation_html/index.html` no navegador. Para melhor experiência, utilize a extensão Live Server do Visual Studio Code.

A apresentação carrega Chart.js e as fontes tipográficas por CDN. É necessária conexão com a internet para esses recursos externos.

## Como reproduzir as análises

No terminal, a partir da pasta raiz do projeto:

```bash
python -m pip install -r requirements.txt
python src/analysis.py
python presentation_html/build_data.py
```

Depois, abra ou atualize `presentation_html/index.html`.

## Estrutura

```text
Olist_FIAP_Entrega/
├── Apresentacao_Executiva.pdf
├── presentation_html/
│   ├── index.html
│   ├── styles.css
│   ├── app.js
│   ├── chart_data.js
│   └── build_data.py
├── src/
│   └── analysis.py
├── data/
├── outputs/
└── requirements.txt
```

## Escopo e interpretação

A análise utiliza o Brazilian E-Commerce Public Dataset by Olist. Os indicadores e modelos são observacionais e descrevem associações no período analisado. GMV não equivale a receita reconhecida e o frete registrado não equivale ao custo logístico da operação.

**Autor:** João Pedro Nogueira Caetano  
**Instituição:** FIAP
