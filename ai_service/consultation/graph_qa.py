"""
Graph QA Engine — Text-to-Cypher pipeline for querying behavior Knowledge Graph.

Flow:
  1. User question (natural language)
  2. LLM generates Cypher query based on graph schema
  3. Execute Cypher on Neo4j behavior graph
  4. LLM formats results into natural language response
"""

import logging
import re

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from .llm_factory import get_llm
from kb.neo4j_store import get_driver

logger = logging.getLogger(__name__)

# Schema description of the behavior graph for LLM context
BEHAVIOR_GRAPH_SCHEMA = """
Node labels and properties:
- User {user_id: string}  — e.g. 'U001', 'U500'
- Product {product_id: string, name: string, category: string}  — e.g. 'P001', name: 'iPhone 15 Pro Max', category: 'electronics'
- Action {action_type: string}  — values: 'view', 'click', 'add_to_cart', 'purchase', 'wishlist', 'review', 'share', 'compare'
- Device {device_name: string}  — values: 'mobile', 'desktop', 'tablet'
- Session {session_id: string, timestamp: string, duration_seconds: integer}

Relationships:
- (User)-[:HAS_SESSION]->(Session)        — User owns a session
- (Session)-[:PERFORMED]->(Action)        — Session performed an action
- (Action)-[:ON_PRODUCT]->(Product)       — Action was on a product
- (Session)-[:USED_DEVICE]->(Device)      — Session used a device
- (User)-[:INTERESTED_IN]->(Product)      — User showed interest (view/click)
- (User)-[:PURCHASED]->(Product)          — User purchased product
"""

# Prompt to generate Cypher from natural language
CYPHER_GENERATION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """Bạn là chuyên gia Neo4j Cypher. Nhiệm vụ: chuyển câu hỏi tiếng Việt thành Cypher query.

Graph schema:
{schema}

Quy tắc:
- Chỉ trả về Cypher query, KHÔNG giải thích
- Dùng MATCH, WHERE, RETURN, ORDER BY, LIMIT
- Luôn thêm LIMIT 20 nếu không có limit cụ thể
- Nếu hỏi về 1 user cụ thể mà không nói user_id, dùng user_id đã cung cấp
- Nếu không thể tạo Cypher query, trả về: UNSUPPORTED
- KHÔNG dùng DETACH DELETE, CREATE, SET, MERGE hay bất kỳ lệnh ghi nào
- Chỉ đọc dữ liệu (read-only queries)

Ví dụ:
Q: User nào mua hàng nhiều nhất?
MATCH (u:User)-[:PURCHASED]->(p:Product) RETURN u.user_id AS user, count(p) AS purchases ORDER BY purchases DESC LIMIT 10

Q: Sản phẩm nào được xem nhiều nhất?
MATCH (u:User)-[:INTERESTED_IN]->(p:Product) RETURN p.name AS product_name, p.category AS category, count(u) AS views ORDER BY views DESC LIMIT 10

Q: User U001 có hành vi gì?
MATCH (u:User {{user_id: 'U001'}})-[:HAS_SESSION]->(s:Session)-[:PERFORMED]->(a:Action) RETURN a.action_type AS action, count(s) AS times ORDER BY times DESC

Q: Thiết bị nào phổ biến nhất?
MATCH (s:Session)-[:USED_DEVICE]->(d:Device) RETURN d.device_name AS device, count(s) AS sessions ORDER BY sessions DESC

Q: Danh mục electronics có bao nhiêu sản phẩm?
MATCH (p:Product) WHERE p.category = 'electronics' RETURN count(p) AS total_products

Q: Sản phẩm nào phù hợp với tôi?
MATCH (u:User {{user_id: 'U001'}})-[:PURCHASED]->(p:Product) RETURN p.name AS product_name, p.category AS category LIMIT 10

Q: User U001 mua sản phẩm gì?
MATCH (u:User {{user_id: 'U001'}})-[:PURCHASED]->(p:Product) RETURN p.name AS product_name, p.category AS category

Q: Lịch sử mua hàng của tôi
MATCH (u:User {{user_id: 'U001'}})-[:PURCHASED]->(p:Product) RETURN p.name AS product_name, p.category AS category"""),
    ("human", """User ID hiện tại: {user_id}

Câu hỏi: {question}

Cypher query:"""),
])

# Predefined Cypher templates for common questions (fallback for small LLMs)
# Patterns are checked in order — put more specific patterns first
PREDEFINED_QUERIES = [
    {
        'name': 'top_purchased_products',
        'patterns': [
            'sản phẩm nào được mua', 'san pham nao duoc mua',
            'sản phẩm được mua nhiều', 'san pham duoc mua nhieu',
            'sản phẩm mua nhiều nhất', 'san pham mua nhieu nhat',
            'sản phẩm bán chạy', 'san pham ban chay',
            'sản phẩm phổ biến nhất', 'san pham pho bien nhat',
            'mua nhiều nhất', 'mua nhieu nhat',
            'được mua nhiều', 'duoc mua nhieu',
        ],
        'cypher': "MATCH (u:User)-[:PURCHASED]->(p:Product) RETURN p.name AS product_name, p.category AS category, count(u) AS purchases ORDER BY purchases DESC LIMIT 10",
    },
    {
        'name': 'top_purchasers',
        'patterns': [
            'user nào mua nhiều', 'user nao mua nhieu',
            'người dùng nào mua nhiều', 'nguoi dung nao mua nhieu',
            'khách hàng mua nhiều nhất', 'khach hang mua nhieu nhat',
            'khach hang tot nhat', 'khách hàng tốt nhất',
            'top purchasers', 'top customers',
        ],
        'cypher': "MATCH (u:User)-[:PURCHASED]->(p:Product) RETURN u.user_id AS user, count(p) AS purchases ORDER BY purchases DESC LIMIT 10",
    },
    {
        'name': 'top_viewed',
        'patterns': ['xem nhieu nhat', 'xem nhiều nhất', 'san pham pho bien', 'sản phẩm phổ biến', 'most viewed', 'trending', 'top san pham', 'top sản phẩm'],
        'cypher': "MATCH (u:User)-[:INTERESTED_IN]->(p:Product) RETURN p.name AS product_name, p.category AS category, count(u) AS views ORDER BY views DESC LIMIT 10",
    },
    {
        'name': 'user_actions',
        'patterns': ['hanh vi', 'hành vi', 'behavior', 'hoat dong', 'hoạt động', 'actions', 'co hanh vi', 'có hành vi'],
        'cypher_template': "MATCH (u:User {{user_id: '{user_id}'}})-[:HAS_SESSION]->(s:Session)-[:PERFORMED]->(a:Action) RETURN a.action_type AS action, count(s) AS times ORDER BY times DESC",
    },
    {
        'name': 'top_devices',
        'patterns': ['thiet bi', 'thiết bị', 'device', 'mobile', 'desktop', 'tablet'],
        'cypher': "MATCH (s:Session)-[:USED_DEVICE]->(d:Device) RETURN d.device_name AS device, count(s) AS sessions ORDER BY sessions DESC",
    },
    {
        'name': 'category_count',
        'patterns': ['danh muc', 'danh mục', 'category', 'bao nhieu san pham', 'bao nhiêu sản phẩm'],
        'cypher': "MATCH (p:Product) RETURN p.category AS category, count(p) AS products ORDER BY products DESC",
    },
    {
        'name': 'user_purchases',
        'patterns': ['lich su mua', 'lịch sử mua', 'da mua', 'đã mua', 'purchased', 'purchase history'],
        'cypher_template': "MATCH (u:User {{user_id: '{user_id}'}})-[:PURCHASED]->(p:Product) RETURN p.name AS product_name, p.category AS category",
    },
    {
        'name': 'user_interests',
        'patterns': ['quan tam', 'quan tâm', 'thich gi', 'thích gì', 'interest', 'xem gi', 'xem gì', 'phu hop', 'phù hợp', 'goi y', 'gợi ý', 'de xuat', 'đề xuất', 'recommend'],
        'cypher_template': "MATCH (u:User {{user_id: '{user_id}'}})-[:INTERESTED_IN]->(p:Product) RETURN p.name AS product_name, p.category AS category, count(*) AS interest_score ORDER BY interest_score DESC LIMIT 10",
    },
    {
        'name': 'stats',
        'patterns': ['thong ke', 'thống kê', 'tong quan', 'tổng quan', 'analytics', 'overview', 'statistics'],
        'cypher': "MATCH (u:User) WITH count(u) AS users MATCH (p:Product) WITH users, count(p) AS products MATCH (s:Session) WITH users, products, count(s) AS sessions MATCH ()-[r:PURCHASED]->() RETURN users, products, sessions, count(r) AS total_purchases",
    },
]


def _match_predefined_query(question, user_id=None):
    """Try to match question to a predefined Cypher template."""
    q_lower = question.lower()
    for entry in PREDEFINED_QUERIES:
        for pattern in entry['patterns']:
            if pattern in q_lower:
                if 'cypher_template' in entry:
                    uid = user_id or 'U001'
                    return entry['cypher_template'].format(user_id=uid)
                return entry['cypher']
    return None


# Prompt to format Cypher results into natural language
ANSWER_GENERATION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """Bạn là trợ lý tư vấn mua sắm AI. Dựa trên dữ liệu từ Knowledge Graph, 
hãy trả lời câu hỏi bằng tiếng Việt một cách tự nhiên, thân thiện.

Quy tắc:
- Trả lời ngắn gọn, có cấu trúc
- Nếu dữ liệu trống, nói rằng chưa có thông tin
- Đưa ra gợi ý/nhận xét dựa trên data nếu phù hợp
- Sử dụng bullet points hoặc bảng khi liệt kê nhiều items"""),
    ("human", """Câu hỏi: {question}

Cypher query đã chạy:
{cypher}

Kết quả từ Knowledge Graph:
{results}

Trả lời:"""),
])

# Keywords that indicate a behavior/graph query (vs general consultation)
BEHAVIOR_KEYWORDS = [
    'hành vi', 'behavior', 'mua gì', 'xem gì', 'sản phẩm nào',
    'phù hợp', 'gợi ý', 'recommend', 'đề xuất', 'lịch sử',
    'history', 'purchased', 'viewed', 'top sản phẩm', 'trending',
    'user', 'người dùng', 'khách hàng', 'thống kê', 'analytics',
    'mobile', 'desktop', 'tablet', 'device', 'thiết bị',
    'category', 'danh mục', 'add_to_cart', 'wishlist', 'compare',
    'so sánh', 'yêu thích', 'giỏ hàng', 'mua hàng', 'purchase',
    'bao nhiêu', 'nhiều nhất', 'ít nhất', 'tỉ lệ', 'phần trăm',
]


def is_behavior_query(question):
    """Check if a question is about user behavior (should query graph)."""
    q_lower = question.lower()
    return any(kw in q_lower for kw in BEHAVIOR_KEYWORDS)


def _extract_cypher(text):
    """Extract Cypher query from LLM output, stripping markdown fences."""
    if not text or 'UNSUPPORTED' in text:
        return None

    # Remove markdown code fences
    text = re.sub(r'```(?:cypher)?\s*', '', text)
    text = re.sub(r'```', '', text)
    text = text.strip()

    # Safety check: reject write operations
    write_ops = ['CREATE', 'MERGE', 'DELETE', 'SET ', 'REMOVE', 'DROP', 'DETACH']
    text_upper = text.upper()
    for op in write_ops:
        if op in text_upper and 'CONSTRAINT' not in text_upper:
            logger.warning(f"Rejected write operation in Cypher: {text[:100]}")
            return None

    if not text.upper().startswith(('MATCH', 'OPTIONAL', 'WITH', 'CALL', 'RETURN')):
        return None

    return text


def _execute_cypher(cypher, limit=20):
    """Execute a read-only Cypher query and return results."""
    driver = get_driver()
    with driver.session() as session:
        result = session.run(cypher)
        records = [dict(record) for record in result]
        return records[:limit]


def _enrich_records_with_names(records):
    """Replace product_id (P009) with product names in query results.
    Falls back to product service if names not in Neo4j results."""
    if not records:
        return records

    # If records already have product_name, no enrichment needed
    if any('product_name' in r for r in records):
        return records

    # Check if any record has product-related keys without names
    product_keys = {'product', 'product_id', 'p.product_id'}
    has_product = any(
        k in product_keys for record in records for k in record.keys()
    )
    if not has_product:
        return records

    # Look up names from Neo4j directly
    name_map = {}
    try:
        driver = get_driver()
        with driver.session() as session:
            result = session.run("MATCH (p:Product) WHERE p.name IS NOT NULL RETURN p.product_id AS pid, p.name AS name")
            for rec in result:
                name_map[rec['pid']] = rec['name']
    except Exception as e:
        logger.warning(f"Failed to fetch product names from Neo4j: {e}")

    if not name_map:
        return records

    enriched = []
    for record in records:
        new_record = dict(record)
        for key in list(new_record.keys()):
            if key in product_keys:
                pid = str(new_record[key])
                product_name = name_map.get(pid)
                if product_name:
                    new_record['product_name'] = product_name
        enriched.append(new_record)

    return enriched


def _format_results(records):
    """Format Neo4j records into readable text for LLM."""
    if not records:
        return "Không có kết quả."

    lines = []
    for i, record in enumerate(records, 1):
        parts = []
        for key, value in record.items():
            # If value is a Neo4j Node object, extract its properties
            if hasattr(value, '_properties'):
                props = dict(value._properties)
                display = props.get('name') or props.get('product_id') or props.get('user_id') or str(props)
                parts.append(f"{key}: {display}")
            elif hasattr(value, 'items'):  # dict-like node
                display = value.get('name') or value.get('product_id') or value.get('user_id') or str(value)
                parts.append(f"{key}: {display}")
            else:
                parts.append(f"{key}: {value}")
        lines.append(f"{i}. {', '.join(parts)}")

    return '\n'.join(lines)


def graph_qa_response(question, user_id=None):
    """
    Full Text-to-Cypher pipeline:
      1. Try predefined Cypher templates (fast, reliable)
      2. Fall back to LLM-generated Cypher
      3. Execute on Neo4j
      4. LLM formats results into natural language

    Args:
        question: str — user's question in Vietnamese
        user_id: str — optional user_id for personalized queries (e.g. 'U001')

    Returns:
        dict with:
            response: str — natural language answer
            cypher: str — generated Cypher query
            results: list — raw Neo4j results
            source: str — 'behavior_graph'
    """
    llm = get_llm()
    user_id_str = user_id or 'U001'
    cypher = None

    # Strategy 1: Try predefined query templates first (reliable)
    predefined = _match_predefined_query(question, user_id=user_id_str)
    if predefined:
        cypher = predefined
        logger.info(f"Using predefined Cypher: {cypher[:80]}")

    # Strategy 2: LLM-generated Cypher (flexible but may fail with small models)
    if not cypher:
        try:
            cypher_chain = CYPHER_GENERATION_PROMPT | llm | StrOutputParser()
            raw_cypher = cypher_chain.invoke({
                'schema': BEHAVIOR_GRAPH_SCHEMA,
                'user_id': user_id_str,
                'question': question,
            })
            cypher = _extract_cypher(raw_cypher)
            if cypher:
                logger.info(f"LLM-generated Cypher: {cypher[:80]}")
        except Exception as e:
            logger.warning(f"Cypher generation error: {e}")

    if not cypher:
        return {
            'response': 'Xin lỗi, tôi không thể truy vấn thông tin này từ Knowledge Graph. '
                        'Vui lòng thử hỏi cụ thể hơn về hành vi người dùng hoặc sản phẩm.',
            'cypher': None,
            'results': [],
            'source': 'behavior_graph',
        }

    # Step 2: Execute Cypher on Neo4j
    try:
        records = _execute_cypher(cypher)
        records = _enrich_records_with_names(records)
        formatted_results = _format_results(records)
    except Exception as e:
        logger.error(f"Cypher execution error: {e}", exc_info=True)
        # If LLM query failed, try predefined as fallback
        if not predefined:
            fallback = _match_predefined_query(question, user_id=user_id_str)
            if fallback:
                try:
                    records = _execute_cypher(fallback)
                    records = _enrich_records_with_names(records)
                    formatted_results = _format_results(records)
                    cypher = fallback
                    logger.info("Fallback to predefined query succeeded")
                except Exception:
                    pass
                else:
                    # Skip to Step 3 with fallback results
                    return _generate_answer(llm, question, cypher, records, formatted_results)

        return {
            'response': 'Xin lỗi, truy vấn Knowledge Graph gặp lỗi. '
                        'Vui lòng thử lại với câu hỏi khác.',
            'cypher': cypher,
            'results': [],
            'source': 'behavior_graph',
        }

    # Step 3: Generate natural language answer
    return _generate_answer(llm, question, cypher, records, formatted_results)


def _generate_answer(llm, question, cypher, records, formatted_results):
    """Use LLM to convert Cypher results into natural language."""
    try:
        answer_chain = ANSWER_GENERATION_PROMPT | llm | StrOutputParser()
        response = answer_chain.invoke({
            'question': question,
            'cypher': cypher,
            'results': formatted_results,
        })

        return {
            'response': response,
            'cypher': cypher,
            'results': records,
            'source': 'behavior_graph',
        }

    except Exception as e:
        logger.error(f"Answer generation error: {e}", exc_info=True)
        # Fallback: return raw results
        return {
            'response': f'Kết quả từ Knowledge Graph:\n{formatted_results}',
            'cypher': cypher,
            'results': records,
            'source': 'behavior_graph',
        }
