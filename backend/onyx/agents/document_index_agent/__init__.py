"""Document Index Agent package - LLM agent for interacting with document index."""

from onyx.agents.document_index_agent.index_agent import (
    DocumentIndexAgent,
    DocumentIndexTools,
    DocumentInfo,
    create_document_index_agent,
)

__all__ = [
    "DocumentIndexAgent",
    "DocumentIndexTools",
    "DocumentInfo",
    "create_document_index_agent",
] 