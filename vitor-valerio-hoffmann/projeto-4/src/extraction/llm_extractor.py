"""Extração semântica via Claude com saída estruturada (Contrato Semântico).

Usa `client.messages.parse()` com `output_format=PreviaOperacional`: o SDK gera o
JSON Schema a partir do Pydantic, força o modelo a respondê-lo e revalida a
resposta com Pydantic. Se a saída fugir do contrato, `parsed_output` vem `None` e
nós tratamos como erro de extração (blindagem do banco).
"""
from __future__ import annotations

import json
from pathlib import Path

import anthropic

from src.config import settings
from src.extraction.chunker import selecionar_chunks
from src.extraction.parser import DocumentoParseado, usar_fullscan
from src.models import PreviaOperacional

# System prompt = regras de blindagem do Contrato Semântico.
SYSTEM_PROMPT = """\
Você é um extrator de dados financeiros de prévias operacionais e relatórios de \
incorporadoras brasileiras (setor habitacional). Sua tarefa é extrair, de forma \
estruturada, as métricas operacionais ABSOLUTAS por empresa e por trimestre.

REGRAS OBRIGATÓRIAS (a violação contamina um banco de dados):
1. Extraia SOMENTE valores absolutos (VGV em R$, número de unidades). IGNORE \
   completamente as variações percentuais destacadas pelo marketing (ex.: "+14%", \
   "-32%", "9m 25/24"). Essas porcentagens NÃO devem virar nenhum valor numérico.
2. Valores monetários (VGV, vendas) devem ser normalizados para R$ MILHÕES. \
   Remova separadores de milhar. Se o documento estiver em R$ mil, converta.
3. Se uma métrica NÃO estiver presente no documento, retorne null. NUNCA invente, \
   estime ou infira um número que não está explícito.
4. Não crie trimestres que não aparecem no documento. Use exatamente o ano e o \
   trimestre indicados.
5. Respeite os tipos do contrato: trimestre é 1, 2, 3 ou 4.

O documento abaixo pode estar em formato de tabela ou de slides de apresentação — \
extraia pela compreensão do conteúdo, não pela posição visual.
"""


def extrair_previa(
    doc: DocumentoParseado,
    fonte_url: str | None = None,
) -> PreviaOperacional:
    """Envia o documento ao Claude e devolve a PreviaOperacional validada.

    Decide entre full-scan (docs curtos) e chunking semântico (docs longos).
    Levanta `RuntimeError` se o modelo não produzir uma saída válida pelo contrato.
    """
    if usar_fullscan(doc):
        texto = doc.texto_completo
    else:
        texto = selecionar_chunks(doc)

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    response = client.messages.parse(
        model=settings.llm_model,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": (
                    "Extraia as métricas operacionais absolutas do documento a "
                    "seguir, seguindo rigorosamente o contrato.\n\n"
                    f"--- DOCUMENTO ---\n{texto}"
                ),
            }
        ],
        output_format=PreviaOperacional,
    )

    previa = response.parsed_output
    if previa is None:
        motivo = getattr(response, "stop_reason", "desconhecido")
        raise RuntimeError(
            f"LLM não retornou saída válida pelo Contrato Semântico (stop_reason={motivo})"
        )

    # Anexa a linhagem (fonte) a cada métrica — não é responsabilidade do LLM.
    if fonte_url:
        for metrica in previa.metricas:
            if not metrica.fonte_url:
                metrica.fonte_url = fonte_url

    return previa


def carregar_previa_mock(
    caminho_fixture: str | Path,
    fonte_url: str | None = None,
) -> PreviaOperacional:
    """Modo offline: carrega uma extração já gravada (fixture JSON) em vez de
    chamar o Claude.

    Útil para a correção/demonstração sem gastar chave de API. A fixture passa
    pela MESMA validação do Contrato Semântico (Pydantic) que a saída real do
    LLM, então o caminho mock respeita exatamente as mesmas regras.
    """
    caminho_fixture = Path(caminho_fixture)
    dados = json.loads(caminho_fixture.read_text(encoding="utf-8"))
    previa = PreviaOperacional.model_validate(dados)

    if fonte_url:
        for metrica in previa.metricas:
            if not metrica.fonte_url:
                metrica.fonte_url = fonte_url

    return previa
