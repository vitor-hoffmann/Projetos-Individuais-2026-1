# Pipeline de UDA — Conjuntura do Setor Habitacional

Projeto Individual 4 — **Vitor Valério Hoffmann**

Pipeline de Engenharia e Análise de Dados Não Estruturados (UDA) que coleta prévias
operacionais de incorporadoras (PDFs em layouts variados), extrai os **valores
absolutos** via LLM de forma resiliente a layout, e serve os dados por uma API REST
que calcula as variações usadas no *Boletim de Conjuntura do Setor Habitacional*.

> O PDF de exemplo do desafio (`exemplo_Boletim_Conjuntura_2025_3T.pdf`) é a **saída**
> desejada — variações % de Lançamentos e Vendas por empresa. Este pipeline produz
> esses números a partir dos valores brutos publicados pelas empresas.

## Componentes obrigatórios atendidos

- **Camada de Extração** — `src/extraction/`: PyMuPDF + estratégia híbrida
  (full-scan / chunking semântico) + Claude com saída estruturada.
- **Contrato Semântico** — `src/models.py` (Pydantic) + system prompt de blindagem.
  Força tipos, ignora porcentagens de marketing, trata ausente como `null`.
  Detalhes em [`docs/contrato-semantico.md`](docs/contrato-semantico.md).
- **Catálogo e Linhagem** — `src/catalog/`: SQLite com idempotência por hash
  (`documents`), dados (`metrics`) e linhagem `metric → URL/página do PDF` (`lineage`).

Arquitetura completa em [`docs/arquitetura.md`](docs/arquitetura.md).

## Stack

| Função | Tecnologia |
|--------|-----------|
| LLM (extração semântica) | Claude (`claude-sonnet-4-6`) via `messages.parse()` |
| Parsing de PDF | PyMuPDF (fitz) |
| Contrato Semântico | Pydantic v2 |
| Banco (catálogo + dados + linhagem) | SQLite |
| Ingestão contínua | requests + BeautifulSoup + APScheduler (polling) |
| API | FastAPI + Uvicorn |

## Instalação

```bash
cd vitor-valerio-hoffmann/projeto-4
python -m venv .venv && source .venv/bin/activate   # requer python3-venv
pip install -r requirements.txt
cp .env.example .env        # preencha ANTHROPIC_API_KEY
```

## Uso

### 1. Inicializar o banco
```bash
python -m src.catalog.db
```

### 2. Processar um PDF (modo manual / demonstração)
```bash
python -m src.pipeline data/samples/previa_mrv_1t26.pdf --url https://ri.mrv.com.br/.../previa.pdf
```
- Calcula o hash, checa idempotência, extrai via LLM e grava métricas + linhagem.
- Rodar de novo o **mesmo** PDF → `[IGNORADO]` (idempotência por hash).

### 2b. Modo offline (`--mock`) — testar SEM chave de API
Para avaliar o pipeline ponta-a-ponta **sem gastar chave da Anthropic**, use o
modo `--mock`: a etapa de extração via LLM é substituída por uma fixture JSON já
gravada (`data/fixtures/`). Todo o resto — hash, idempotência, catálogo, linhagem
e a validação pelo Contrato Semântico — é **idêntico** ao fluxo real.

```bash
python -m src.catalog.db
python -m src.pipeline data/samples/exemplo_Boletim_Conjuntura_2025_3T.pdf --mock
uvicorn src.api.main:app   # depois: curl "http://localhost:8000/api/conjuntura?empresa=MRV&ano=2025&trimestre=3"
```
- `--mock` sem valor resolve automaticamente a fixture em `data/fixtures/` pelo
  nome do PDF (ou cai no `boletim_demo.json`). Para apontar uma fixture específica:
  `--mock data/fixtures/minha_fixture.json`.
- A fixture de demonstração traz valores **ilustrativos** de 3T25, 2T25 e 3T24,
  para a API exibir variações T/T e A/A não-nulas.

### 3. Ingestão contínua (gatilho orientado a eventos)
```bash
python -m src.ingestion.trigger --once   # uma varredura das Centrais de Resultados
python -m src.ingestion.trigger          # scheduler (polling no intervalo configurado)
```

### 4. API
```bash
uvicorn src.api.main:app --reload
```
Exemplos:
```bash
curl "http://localhost:8000/api/conjuntura?empresa=MRV&ano=2025&trimestre=3"
curl "http://localhost:8000/api/empresas"
curl "http://localhost:8000/api/documentos"   # catálogo + linhagem (auditoria)
```
O endpoint `/api/conjuntura` devolve os **valores absolutos** e as **variações
T/T e A/A calculadas** a partir do histórico (não extraídas dos PDFs).

## Testes

```bash
pytest
```
Cobrem: idempotência por hash, validação do Contrato Semântico (Pydantic),
persistência + linhagem no catálogo, o cálculo de variações da API e o modo
offline (`--mock`) carregando fixtures pelo contrato.
Os testes rodam **offline** (não chamam a API da Anthropic nem a rede).

## Resiliência a layout (critério central)

Para validar a resiliência, processe **dois layouts diferentes** — o formato em
tabela do Boletim 3T25 e uma prévia em formato de slides (ex.: MRV 1T26). O mesmo
código extrai de ambos porque o Contrato Semântico descreve *o que* extrair, não
*onde*. Coloque os PDFs em `data/samples/` e rode o pipeline em cada um.

## Configuração (`.env`)

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `ANTHROPIC_API_KEY` | — | Chave da API Anthropic (obrigatória para extração) |
| `UDA_LLM_MODEL` | `claude-sonnet-4-6` | Modelo Claude |
| `UDA_FULLSCAN_TOKEN_LIMIT` | `6000` | Acima disso, usa chunking em vez de full-scan |
| `UDA_DB_PATH` | `data/catalog.db` | Caminho do SQLite |
| `UDA_POLL_INTERVAL_HOURS` | `24` | Intervalo do polling de ingestão |
