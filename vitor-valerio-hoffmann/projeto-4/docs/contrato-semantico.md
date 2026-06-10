# Contrato Semântico dos Dados

O **Contrato Semântico** é a ferramenta central de revisão e validação do pipeline.
Ele é implementado em `src/models.py` (Pydantic) e reforçado pelo *system prompt*
em `src/extraction/llm_extractor.py`. Juntos, eles **blindam o banco** contra
alucinações do LLM e contra variações de layout dos PDFs.

## Por que Pydantic + tool use?

1. O modelo Pydantic vira um **JSON Schema** (`EXTRACTION_TOOL_SCHEMA`) passado ao
   Claude como uma *tool*. O LLM é **forçado** a responder exatamente nesse formato.
2. A resposta é re-validada por Pydantic no Python. Se algo fugir do contrato
   (tipo errado, trimestre fora de 1–4, empresa vazia), a validação **falha** e o
   documento é reprocessado com a mensagem de erro anexada ao prompt (retry).
3. Resultado: nenhum dado malformado ou inventado chega ao banco.

## Esquema

### `MetricaEmpresa`
| Campo | Tipo | Regra |
|-------|------|-------|
| `empresa` | `str` | Obrigatório, não-vazio |
| `ano` | `int` | 2000–2100 |
| `trimestre` | `int` | 1–4 |
| `lancamentos_vgv` | `float \| None` | R$ milhões; `None` se ausente |
| `lancamentos_unidades` | `int \| None` | unidades; `None` se ausente |
| `vendas_vgv` | `float \| None` | R$ milhões; `None` se ausente |
| `vendas_unidades` | `int \| None` | unidades; `None` se ausente |
| `vso` | `float \| None` | % (métrica operacional bruta) |
| `fonte_url` | `str \| None` | preenchido pelo pipeline (linhagem) |
| `pagina` | `int \| None` | preenchido na extração (linhagem) |

### `PreviaOperacional`
Envelope do documento: `documento_tipo`, `periodo_referencia` e a lista de
`metricas` (um doc pode conter várias empresas, como o Boletim de Conjuntura).

## Regras de blindagem (system prompt)

1. **Somente valores absolutos.** Ignorar explicitamente as variações percentuais
   (ex.: "+14%", "-32%") que o marketing de RI destaca. Extrair os números brutos
   (VGV em R$, unidades) para que o banco calcule o histórico real.
2. **Ausente = `null`.** Nunca inventar, estimar ou inferir um valor que não está
   no documento. Campo não encontrado → `null`.
3. **Tipos exatos.** Respeitar os tipos do contrato; normalizar unidades para
   R$ **milhões** e remover separadores de milhar.
4. **Sem inferência temporal.** Não criar trimestres que não aparecem no documento.

## Resiliência a layout

Como o contrato descreve **o que** extrair (semântica) e não **onde** (coordenadas),
o mesmo esquema funciona tanto no formato de tabela do Boletim 3T25 quanto em
prévias em formato de slides (ex.: MRV 1T26). A compreensão de contexto fica a
cargo do LLM; o contrato apenas valida o resultado.
