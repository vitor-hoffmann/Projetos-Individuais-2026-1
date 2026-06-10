"""Configuração central do pipeline (lida de variáveis de ambiente / .env)."""
from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Raiz do projeto (vitor-valerio-hoffmann/projeto-4/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Parâmetros de execução do pipeline de UDA."""

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_prefix="UDA_",
        extra="ignore",
    )

    # Chave da API Anthropic (sem prefixo UDA_, nome padrão do SDK)
    anthropic_api_key: str = ""

    # Modelo Claude usado na extração semântica
    llm_model: str = "claude-sonnet-4-6"

    # Acima deste número estimado de tokens, usa chunking em vez de full-scan
    fullscan_token_limit: int = 6000

    # Caminho do banco SQLite (relativo à raiz do projeto, se não absoluto)
    db_path: str = "data/catalog.db"

    # Intervalo de polling do scheduler de ingestão, em horas
    poll_interval_hours: int = 24

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # A chave da Anthropic não usa o prefixo UDA_, então lê manualmente
        import os

        if not self.anthropic_api_key:
            self.anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY", "")

    @property
    def db_file(self) -> Path:
        p = Path(self.db_path)
        return p if p.is_absolute() else PROJECT_ROOT / p


settings = Settings()
