# Olist | Tech Challenge FIAP — Fase 1

Projeto individual de análise comercial e operacional do marketplace Olist, desenvolvido para o Tech Challenge da Pós-Tech em Data Analytics da FIAP.

O projeto reúne uma apresentação executiva, análises reproduzíveis em Python, bases de dados, resultados consolidados e a gravação da apresentação.

---

## Comece por aqui

Há **duas formas de visualizar a apresentação executiva**. Escolha a que for mais conveniente:

### Opção 1 — Apresentação online

Acesse diretamente pelo GitHub Pages:

**[Abrir apresentação executiva online](https://caetanojpn-cyber.github.io/olist-fiap-tech-challenge/presentation_html/)**

Essa opção abre a apresentação no navegador, sem precisar baixar ou localizar os arquivos do projeto.

### Opção 2 — Apresentação local

Também é possível abrir a apresentação diretamente pelos arquivos entregues:

1. Extraia o arquivo ZIP completo para uma pasta do computador.
2. Entre na pasta `Olist_FIAP_Entrega`.
3. Abra a pasta `presentation_html`.
4. Abra o arquivo `index.html` em um navegador (Chrome, Edge ou Firefox).

A apresentação será carregada a partir dos arquivos locais, sem depender do GitHub Pages. **Observação:** a apresentação utiliza Chart.js e fontes carregadas por CDN; portanto, é necessário estar conectado à internet para que os gráficos e as fontes externas sejam exibidos corretamente. A opção local evita depender do link online da apresentação, mas não é totalmente independente de internet.

---

## Vídeo da apresentação

O pacote ZIP inclui também o arquivo **`Olist.mp4`**, localizado no nível principal do ZIP, ao lado da pasta `Olist_FIAP_Entrega`.

O vídeo também pode ser assistido online pelo YouTube:

**[Assistir à apresentação no YouTube](https://youtu.be/mUM6Fx8_LhI)**

Duração: **4min53s**.

---

## Código-fonte e documentação

O código completo, a documentação e o histórico do projeto estão disponíveis no GitHub:

**[Acessar repositório GitHub](https://github.com/caetanojpn-cyber/olist-fiap-tech-challenge)**

---

## Conteúdo do projeto

- `presentation_html/`: apresentação executiva interativa em HTML, CSS e JavaScript.
- `src/analysis.py`: pipeline de análise dos dados.
- `presentation_html/build_data.py`: geração do conjunto de dados utilizado pelos gráficos.
- `data/`: bases de entrada utilizadas no projeto.
- `outputs/`: resultados tabulares e dados consolidados dos gráficos.
- `requirements.txt`: dependências Python necessárias para reproduzir as análises.

## Como reproduzir as análises

Com Python instalado, abra um terminal na pasta raiz `Olist_FIAP_Entrega` e execute:

```bash
python -m pip install -r requirements.txt
python src/analysis.py
python presentation_html/build_data.py
```

Depois, abra ou atualize `presentation_html/index.html`.

## Estrutura dos arquivos

```text
Pacote de entrega/
├── Olist.mp4
└── Olist_FIAP_Entrega/
    ├── README.md
    ├── requirements.txt
    ├── data/
    ├── outputs/
    ├── src/
    │   └── analysis.py
    └── presentation_html/
        ├── index.html
        ├── styles.css
        ├── app.js
        ├── chart_data.js
        └── build_data.py
```

## Escopo e interpretação

A análise utiliza o Brazilian E-Commerce Public Dataset by Olist. Os indicadores e modelos são observacionais e descrevem associações no período analisado. GMV não equivale a receita reconhecida e o frete registrado não equivale ao custo logístico da operação.

---

**Autor:** João Pedro Nogueira Caetano  
**Instituição:** FIAP  
**Curso:** Pós-Tech em Data Analytics  
**RM:** 378530 | **Turma:** 16DTAT
