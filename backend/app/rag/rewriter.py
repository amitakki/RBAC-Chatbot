"""
Optional HyDE (Hypothetical Document Embeddings) query rewriter (RC-70).

Enabled via the ENABLE_QUERY_REWRITE=true environment variable.
If rewriting fails for any reason the original question is returned unchanged
so the pipeline always degrades gracefully.
"""

from __future__ import annotations

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage


_REWRITE_TEMPLATE = (
    "You are a search assistant. Write a brief, factual passage (2-3 sentences) "
    "that would directly answer the following question about a company's internal "
    "documents. Do not add disclaimers or caveats.\n\nQuestion: {question}"
)


def rewrite_query(question: str, llm: BaseChatModel) -> str:
    """Return a HyDE-expanded query string for better semantic retrieval.

    Asks the LLM to produce a hypothetical answer passage, whose embedding
    is typically closer to real answer chunks than the raw question embedding.

    Args:
        question: The user's original question.
        llm: Shared chat model instance from the pipeline.

    Returns:
        The rewritten query string, or *question* unchanged if the LLM call fails.
    """
    try:
        prompt = _REWRITE_TEMPLATE.format(question=question)
        response = llm.invoke([HumanMessage(content=prompt)])
        return response.content.strip() or question
    except Exception:
        return question
