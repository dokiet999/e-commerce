"""
RAG Engine — LangChain LCEL pipeline for consultation chatbot.

Retrieval strategy (three-stage):
  1. Router    — detect if question is about user behavior → Graph QA
  2. ChromaDB  — semantic / vector similarity search (primary)
  3. Neo4j     — graph traversal for topic-based and category-based enrichment
"""

import logging

from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_core.messages import HumanMessage, AIMessage

from .llm_factory import get_llm
from .prompts import CONSULTATION_PROMPT, format_behavior_context
from .graph_qa import is_behavior_query, graph_qa_response
from kb.vector_store import get_retriever
from kb.neo4j_store import search_by_topic, get_products_by_category

logger = logging.getLogger(__name__)

_rag_chain = None


def _product_url(product_id):
    """Return the frontend URL for a product id, or empty string if invalid."""
    product_id = str(product_id or '').strip()
    if not product_id.isdigit():
        return ''
    return f'/product/{product_id}/'


def _append_product_links(response, sources, limit=3):
    """Append product links to the answer so API clients also get direct URLs."""
    product_sources = [
        source for source in sources
        if source.get('source_type') == 'product'
        and source.get('product_name')
        and source.get('product_url')
    ]
    if not product_sources or '/product/' in response:
        return response

    lines = ['Link san pham:']
    for source in product_sources[:limit]:
        lines.append(f"- {source['product_name']}: {source['product_url']}")

    return response.rstrip() + '\n\n' + '\n'.join(lines)


def _format_docs(docs):
    """Format retrieved documents into a context string."""
    if not docs:
        return "Không tìm thấy thông tin liên quan trong cơ sở dữ liệu."

    formatted = []
    for i, doc in enumerate(docs, 1):
        source = doc.metadata.get('source', 'unknown')
        source_type = doc.metadata.get('source_type', 'document')
        content = doc.page_content.strip()

        if source_type == 'product':
            product_name = doc.metadata.get('product_name', '')
            formatted.append(f"[Sản phẩm: {product_name}]\n{content}")
        else:
            formatted.append(f"[Tài liệu: {source}]\n{content}")

    return '\n\n---\n\n'.join(formatted)


def _enrich_with_neo4j(question, behavior_profile=None):
    """
    Query Neo4j to enrich context with structured graph knowledge.

    Strategy:
    - Extract keywords from question to find relevant topics
    - If behavior_profile has preferred_categories, fetch products from Neo4j
    Returns a formatted string appended to ChromaDB context.
    """
    neo4j_parts = []

    try:
        # Topic-based search: look for policy/guide keywords in question
        keywords = _extract_query_keywords(question)
        for keyword in keywords[:2]:
            chunks = search_by_topic(keyword, limit=2)
            for c in chunks:
                neo4j_parts.append(
                    f"[KB Graph — Chủ đề: {c['topic']}]\n{c['text']}"
                )

        # Category-based product enrichment from behavior profile
        if behavior_profile:
            preferred = behavior_profile.get('preferred_categories', {})
            if preferred:
                # Get top preferred category
                top_category = max(preferred, key=preferred.get)
                products = get_products_by_category(top_category, limit=3)
                if products:
                    lines = [f"[Sản phẩm gợi ý từ danh mục '{top_category}']"]
                    for p in products:
                        stock_label = 'Còn hàng' if p['stock'] > 0 else 'Hết hàng'
                        lines.append(
                            f"- {p['name']} | Giá: ${p['price']} | {stock_label}"
                        )
                    neo4j_parts.append('\n'.join(lines))

    except Exception as e:
        logger.warning(f"Neo4j enrichment skipped: {e}")

    return '\n\n---\n\n'.join(neo4j_parts)


POLICY_KEYWORDS = [
    'đổi trả', 'hoàn tiền', 'vận chuyển', 'giao hàng', 'thanh toán',
    'bảo hành', 'khuyến mãi', 'giảm giá', 'tài khoản', 'đặt hàng',
    'hủy đơn', 'shipping', 'return', 'payment', 'warranty',
    'chính sách', 'policy', 'quy trình', 'liên hệ', 'hỗ trợ',
]


def _is_policy_query(question):
    """Check if question is about store policies (not products/behavior)."""
    q_lower = question.lower()
    return any(kw in q_lower for kw in POLICY_KEYWORDS)


def _extract_query_keywords(question):
    """Simple keyword extraction for Neo4j topic matching."""
    q_lower = question.lower()
    return [kw for kw in POLICY_KEYWORDS if kw in q_lower]


def _build_chain(behavior_context='', policy_query=False):
    """Build the RAG chain with LCEL."""
    llm = get_llm()

    if policy_query:
        # Filter to only document chunks (policy/guide files), not product chunks
        retriever = get_retriever(search_kwargs={
            'k': 4,
            'filter': {'source_type': 'document'},
        })
    else:
        retriever = get_retriever(search_kwargs={'k': 4})

    chain = (
        RunnablePassthrough.assign(
            context=lambda x: _format_docs(retriever.invoke(x['question'])),
        )
        | CONSULTATION_PROMPT.partial(behavior_context=behavior_context)
        | llm
        | StrOutputParser()
    )

    return chain, retriever


def get_chat_response(question, chat_history=None, behavior_profile=None, user_id=None):
    """
    Get a RAG-powered response for a user question.

    Retrieval strategy:
    - If question is about user behavior → Graph QA (Text-to-Cypher → Neo4j)
    - Otherwise → ChromaDB + Neo4j document enrichment

    Args:
        question: str — the user's message
        chat_history: list of (role, content) tuples
        behavior_profile: dict — user's behavior profile data
        user_id: str — user identifier for behavior graph queries (e.g. 'U001')

    Returns:
        dict with:
            response: str — the AI response
            sources: list of source metadata
    """
    # Route: behavior queries go to Graph QA (Text → Cypher → Neo4j → LLM)
    if is_behavior_query(question):
        logger.info(f"Routing to Graph QA: {question[:80]}")
        try:
            graph_result = graph_qa_response(question, user_id=user_id)
            sources = [{
                'source': 'behavior_knowledge_graph',
                'source_type': 'graph_qa',
                'cypher': graph_result.get('cypher', ''),
            }]
            return {
                'response': graph_result['response'],
                'sources': sources,
            }
        except Exception as e:
            logger.warning(f"Graph QA failed, falling back to RAG: {e}")

    behavior_context = format_behavior_context(behavior_profile)
    is_policy = _is_policy_query(question)
    chain, retriever = _build_chain(behavior_context, policy_query=is_policy)

    lc_history = []
    if chat_history:
        for role, content in chat_history:
            if role == 'user':
                lc_history.append(HumanMessage(content=content))
            elif role == 'assistant':
                lc_history.append(AIMessage(content=content))

    try:
        # Stage 1: ChromaDB semantic retrieval
        retrieved_docs = retriever.invoke(question)
        chroma_context = _format_docs(retrieved_docs)

        # Stage 2: Neo4j graph enrichment
        neo4j_context = _enrich_with_neo4j(question, behavior_profile)

        # Merge both contexts
        combined_context = chroma_context
        if neo4j_context:
            combined_context += '\n\n--- [Thông tin bổ sung từ Knowledge Graph] ---\n\n' + neo4j_context

        # Run the chain with combined context
        response = chain.invoke({
            'question': question,
            'chat_history': lc_history,
            'context': combined_context,
        })

        # Extract source metadata
        sources = []
        seen = set()
        for doc in retrieved_docs:
            source_key = doc.metadata.get('source', '')
            if source_key not in seen:
                seen.add(source_key)
                sources.append({
                    'source': source_key,
                    'source_type': doc.metadata.get('source_type', 'document'),
                    'product_name': doc.metadata.get('product_name', ''),
                    'product_id': doc.metadata.get('product_id', ''),
                })

        return {
            'response': response,
            'sources': sources,
        }

    except Exception as e:
        logger.error(f"RAG chain error: {e}", exc_info=True)
        return {
            'response': (
                'Xin lỗi, tôi đang gặp sự cố kỹ thuật. '
                'Vui lòng thử lại sau hoặc liên hệ bộ phận CSKH để được hỗ trợ.'
            ),
            'sources': [],
        }
