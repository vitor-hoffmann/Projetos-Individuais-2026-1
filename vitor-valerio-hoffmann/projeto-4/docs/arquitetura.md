# Arquitetura do Pipeline de UDA

## Visão geral

O pipeline transforma **dados não estruturados** (PDFs de prévias operacionais de
incorporadoras, em layouts variados) em **dados estruturados consultáveis** (banco
relacional + API), usando LLM para a compreensão semântica em vez de regras rígidas
de layout.

```
        ┌──────────────────────────────────────────────────────────────┐
        │  A. INGESTÃO ORIENTADA A EVENTOS  (src/ingestion/)            │
        │                                                              │
        │  APScheduler (trigger.py) --polling--> crawler.py            │
        │     varre Centrais de Resultados (sources.py)                │
        │     descobre PDFs novos -> baixa                             │
        └───────────────────────────┬──────────────────────────────────┘
                                     │  caminho do PDF + URL de origem
                                     ▼
        ┌──────────────────────────────────────────────────────────────┐
        │  pipeline.py  (orquestrador)                                  │
        │  1. sha256 do arquivo (hashing.py)                           │
        │  2. catálogo já tem esse hash? --SIM--> IGNORA (idempotência) │
        │  3. NÃO -> registra documento (status pending)               │
        └───────────────────────────┬──────────────────────────────────┘
                                     ▼
        ┌──────────────────────────────────────────────────────────────┐
        │  B. EXTRAÇÃO  (src/extraction/)                               │
        │  parser.py (PyMuPDF) -> texto por página                     │
        │     curto? full-scan : chunker.py (chunking semântico)       │
        │  llm_extractor.py -> Claude + Contrato Semântico (Pydantic)  │
        │     messages.parse(output_format=PreviaOperacional)          │
        └───────────────────────────┬──────────────────────────────────┘
                                     ▼
        ┌──────────────────────────────────────────────────────────────┐
        │  C. CATÁLOGO + LINHAGEM  (src/catalog/)                       │
        │  documents (hash, url, status)  <-- idempotência             │
        │  metrics   (valores absolutos por empresa/trimestre)         │
        │  lineage   (metric -> url + página de origem)                │
        └───────────────────────────┬──────────────────────────────────┘
                                     ▼
        ┌──────────────────────────────────────────────────────────────┐
        │  CAMADA DE SERVIÇO  (src/api/main.py — FastAPI)              │
        │  GET /api/conjuntura?empresa=&ano=&trimestre=                │
        │     valores absolutos + variações T/T e A/A CALCULADAS       │
        │  GET /api/empresas   |   GET /api/documentos (auditoria)     │
        └──────────────────────────────────────────────────────────────┘
```

## As três camadas obrigatórias

| Camada | Onde | Responsabilidade |
|--------|------|------------------|
| **Extração de Dados** | `src/extraction/` | Parsing do PDF (PyMuPDF) + motor LLM. Decide full-scan vs chunking. |
| **Contrato Semântico** | `src/models.py` + system prompt em `llm_extractor.py` | Pydantic + regras de blindagem. Força tipos, ignora %, ausente=null. Ver [contrato-semantico.md](contrato-semantico.md). |
| **Catálogo e Linhagem** | `src/catalog/` | SQLite com idempotência por hash e linhagem (cada métrica → PDF de origem). |

## Decisões de projeto (ADR-lite)

### 1. Motor nativo (PyMuPDF + Pydantic + Anthropic) em vez de framework declarativo
Frameworks como LOTUS/DocETL trazem operadores prontos, mas escondem o controle do
*Contrato Semântico*, que é o coração da avaliação. Um motor próprio em ~150 linhas
dá controle total sobre prompt de blindagem, validação e retry, e é mais fácil de
auditar.

### 2. Chunking híbrido (full-scan + fallback)
Prévias operacionais são curtas (slides/tabelas) — full-scan é simples, preciso e
barato. Para documentos longos, o `chunker.py` segmenta por página e mantém só os
trechos com sinais de tabelas operacionais (VGV, lançamentos, vendas, unidades),
economizando tokens sem depender de coordenadas. O limite é configurável
(`UDA_FULLSCAN_TOKEN_LIMIT`).

### 3. SQLite
Catálogo + dados + linhagem em um único arquivo. Zero setup, transacional, ideal
para avaliação. O `repository.py` isola o acesso, então trocar por Postgres depois
é localizado.

### 4. Variações calculadas, nunca extraídas
O LLM é instruído a IGNORAR as porcentagens de marketing e extrair só absolutos.
As variações (T/T e A/A) são calculadas pela API a partir do histórico do banco —
é assim que se obtém o "histórico real" pedido no desafio.

### 5. Idempotência por SHA-256
Antes de qualquer chamada de API (custo), o `pipeline.py` calcula o hash do PDF e
consulta o catálogo. Hash conhecido → ignora. Novo → processa. Evita reprocessar e
gastar tokens à toa.

## Resiliência a variações de layout
Como o Contrato Semântico descreve **o que** extrair (semântica) e não **onde**
(coordenadas), o mesmo código funciona tanto no formato de tabela do Boletim 3T25
quanto em prévias em formato de slides. A compreensão de contexto fica a cargo do
LLM; o Pydantic apenas valida o resultado.
