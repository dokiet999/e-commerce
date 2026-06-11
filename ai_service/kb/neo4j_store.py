"""
Neo4j Knowledge Graph store for the Knowledge Base.

Graph schema:
    (:Document {id, filename, source_type})
    (:Chunk {id, text, chunk_index})
    (:Product {id, name, price, stock, category})
    (:Category {name})
    (:Topic {name})          -- extracted from markdown headings

Relationships:
    (:Document)-[:HAS_CHUNK]->(:Chunk)
    (:Chunk)-[:BELONGS_TO]->(:Document)
    (:Chunk)-[:MENTIONS_TOPIC]->(:Topic)
    (:Product)-[:IN_CATEGORY]->(:Category)
    (:Product)-[:MENTIONED_IN]->(:Chunk)
    (:Chunk)-[:RELATED_TO]->(:Chunk)    -- same document, adjacent chunks
"""

import logging
import os

logger = logging.getLogger(__name__)

_driver = None


def get_driver():
    """Get or create the Neo4j driver (singleton)."""
    global _driver
    if _driver is not None:
        return _driver

    try:
        from neo4j import GraphDatabase
    except ImportError:
        raise ImportError("neo4j driver not installed. Run: pip install neo4j")

    try:
        from django.conf import settings
        uri = settings.NEO4J_URI
        user = settings.NEO4J_USER
        password = settings.NEO4J_PASSWORD
    except Exception:
        uri = os.environ.get('NEO4J_URI', 'bolt://localhost:7687')
        user = os.environ.get('NEO4J_USER', 'neo4j')
        password = os.environ.get('NEO4J_PASSWORD', 'neo4j_password')

    _driver = GraphDatabase.driver(uri, auth=(user, password))
    logger.info(f"Neo4j connected at {uri}")
    return _driver


def close_driver():
    global _driver
    if _driver:
        _driver.close()
        _driver = None


def init_constraints():
    """Create uniqueness constraints and indexes."""
    driver = get_driver()
    with driver.session() as session:
        constraints = [
            "CREATE CONSTRAINT doc_id IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE",
            "CREATE CONSTRAINT chunk_id IF NOT EXISTS FOR (c:Chunk) REQUIRE c.id IS UNIQUE",
            "CREATE CONSTRAINT product_id IF NOT EXISTS FOR (p:Product) REQUIRE p.id IS UNIQUE",
            "CREATE CONSTRAINT category_name IF NOT EXISTS FOR (cat:Category) REQUIRE cat.name IS UNIQUE",
            "CREATE CONSTRAINT topic_name IF NOT EXISTS FOR (t:Topic) REQUIRE t.name IS UNIQUE",
        ]
        for cypher in constraints:
            try:
                session.run(cypher)
            except Exception as e:
                logger.warning(f"Constraint may already exist: {e}")
    logger.info("Neo4j constraints initialized")


# ---------------------------------------------------------------------------
# Document indexing
# ---------------------------------------------------------------------------

def index_document_chunks(filename, chunks, source_type='document'):
    """
    Store a document and its chunks in Neo4j.

    Args:
        filename: str — e.g. 'faq.md'
        chunks: list of str — text chunks
        source_type: 'document' or 'product'
    """
    driver = get_driver()
    doc_id = f"doc_{filename}"

    with driver.session() as session:
        # Create Document node
        session.run(
            """
            MERGE (d:Document {id: $doc_id})
            SET d.filename = $filename,
                d.source_type = $source_type
            """,
            doc_id=doc_id,
            filename=filename,
            source_type=source_type,
        )

        prev_chunk_id = None
        for i, text in enumerate(chunks):
            chunk_id = f"{doc_id}_chunk_{i}"

            # Extract topics from markdown headings (## Topic)
            topics = _extract_topics(text)

            # Create Chunk node
            session.run(
                """
                MERGE (c:Chunk {id: $chunk_id})
                SET c.text = $text,
                    c.chunk_index = $index,
                    c.source = $filename
                WITH c
                MATCH (d:Document {id: $doc_id})
                MERGE (d)-[:HAS_CHUNK]->(c)
                MERGE (c)-[:BELONGS_TO]->(d)
                """,
                chunk_id=chunk_id,
                text=text,
                index=i,
                filename=filename,
                doc_id=doc_id,
            )

            # Link adjacent chunks
            if prev_chunk_id:
                session.run(
                    """
                    MATCH (prev:Chunk {id: $prev_id}), (curr:Chunk {id: $curr_id})
                    MERGE (prev)-[:RELATED_TO]->(curr)
                    MERGE (curr)-[:RELATED_TO]->(prev)
                    """,
                    prev_id=prev_chunk_id,
                    curr_id=chunk_id,
                )

            # Link to Topic nodes
            for topic in topics:
                session.run(
                    """
                    MERGE (t:Topic {name: $topic})
                    WITH t
                    MATCH (c:Chunk {id: $chunk_id})
                    MERGE (c)-[:MENTIONS_TOPIC]->(t)
                    """,
                    topic=topic,
                    chunk_id=chunk_id,
                )

            prev_chunk_id = chunk_id

    logger.info(f"Neo4j: indexed '{filename}' — {len(chunks)} chunks")


def index_product(product_id, name, category_name, price, stock, description=''):
    """
    Store a product node and its category in Neo4j.

    Args:
        product_id: int or str
        name: str
        category_name: str
        price: float
        stock: int
        description: str
    """
    driver = get_driver()
    with driver.session() as session:
        # Create Category node
        session.run(
            "MERGE (cat:Category {name: $name})",
            name=category_name,
        )

        # Create Product node linked to Category
        session.run(
            """
            MERGE (p:Product {id: $product_id})
            SET p.name = $name,
                p.product_id = $product_id,
                p.price = $price,
                p.stock = $stock,
                p.category = $category_name,
                p.description = $description
            WITH p
            MATCH (cat:Category {name: $category_name})
            MERGE (p)-[:IN_CATEGORY]->(cat)
            """,
            product_id=str(product_id),
            name=name,
            price=float(price),
            stock=int(stock),
            description=description or '',
            category_name=category_name,
        )
    logger.debug(f"Neo4j: indexed product '{name}' in '{category_name}'")


# ---------------------------------------------------------------------------
# Behavior event projection
# ---------------------------------------------------------------------------

def index_behavior_event(event):
    """
    Project a persisted BehaviorEvent into Neo4j.

    PostgreSQL remains the source of truth. This graph projection is best used
    for Graph QA and relationship queries.
    """
    driver = get_driver()
    event_id = str(event.id)
    user_id = str(event.user_id) if event.user_id is not None else None
    graph_user_id = f"U{int(event.user_id):03d}" if event.user_id is not None else None
    session_id = event.session_id or f"event_session_{event_id}"
    action_type = event.event_type
    product_id = str(event.product_id) if event.product_id is not None else None
    category_id = str(event.category_id) if event.category_id is not None else None
    created_at = event.created_at.isoformat() if event.created_at else None
    device = (event.metadata or {}).get('device') or 'unknown'
    search_query = event.search_query or ''

    with driver.session() as session:
        session.run(
            """
            MERGE (s:Session {session_id: $session_id})
            SET s.timestamp = $created_at

            MERGE (a:Action {action_type: $action_type})

            MERGE (e:BehaviorEvent {id: $event_id})
            SET e.event_type = $action_type,
                e.user_id = $user_id,
                e.session_id = $session_id,
                e.product_id = $product_id,
                e.category_id = $category_id,
                e.search_query = $search_query,
                e.created_at = $created_at

            MERGE (s)-[:PERFORMED]->(a)
            MERGE (s)-[:HAS_EVENT]->(e)
            MERGE (e)-[:OF_TYPE]->(a)

            MERGE (d:Device {device_name: $device})
            MERGE (s)-[:USED_DEVICE]->(d)
            """,
            event_id=event_id,
            user_id=user_id,
            session_id=session_id,
            action_type=action_type,
            product_id=product_id,
            category_id=category_id,
            search_query=search_query,
            created_at=created_at,
            device=device,
        )

        if graph_user_id:
            session.run(
                """
                MERGE (u:User {user_id: $graph_user_id})
                SET u.id = $user_id
                WITH u
                MATCH (s:Session {session_id: $session_id})
                MATCH (e:BehaviorEvent {id: $event_id})
                MERGE (u)-[:HAS_SESSION]->(s)
                MERGE (u)-[:DID_EVENT]->(e)
                """,
                graph_user_id=graph_user_id,
                user_id=user_id,
                session_id=session_id,
                event_id=event_id,
            )

        if product_id:
            session.run(
                """
                MERGE (p:Product {product_id: $product_id})
                SET p.category_id = $category_id
                WITH p
                MATCH (a:Action {action_type: $action_type})
                MATCH (e:BehaviorEvent {id: $event_id})
                MERGE (a)-[:ON_PRODUCT]->(p)
                MERGE (e)-[:ON_PRODUCT]->(p)
                """,
                product_id=product_id,
                category_id=category_id,
                action_type=action_type,
                event_id=event_id,
            )

            if graph_user_id and action_type in ('product_view', 'page_view', 'search'):
                session.run(
                    """
                    MATCH (u:User {user_id: $graph_user_id})
                    MATCH (p:Product {product_id: $product_id})
                    MERGE (u)-[:INTERESTED_IN]->(p)
                    """,
                    graph_user_id=graph_user_id,
                    product_id=product_id,
                )

            if graph_user_id and action_type in ('checkout', 'purchase'):
                session.run(
                    """
                    MATCH (u:User {user_id: $graph_user_id})
                    MATCH (p:Product {product_id: $product_id})
                    MERGE (u)-[:PURCHASED]->(p)
                    """,
                    graph_user_id=graph_user_id,
                    product_id=product_id,
                )

        if category_id:
            session.run(
                """
                MERGE (cat:Category {id: $category_id})
                WITH cat
                MATCH (e:BehaviorEvent {id: $event_id})
                MERGE (e)-[:IN_CATEGORY]->(cat)
                """,
                category_id=category_id,
                event_id=event_id,
            )

    logger.debug("Neo4j: projected behavior event %s", event_id)


# ---------------------------------------------------------------------------
# Query functions
# ---------------------------------------------------------------------------

def search_by_topic(topic_name, limit=5):
    """
    Find chunks that mention a topic (e.g. 'Đổi trả', 'Vận chuyển').

    Returns:
        list of dicts {chunk_id, text, source, topic}
    """
    driver = get_driver()
    with driver.session() as session:
        result = session.run(
            """
            MATCH (t:Topic)-[:MENTIONS_TOPIC]-(c:Chunk)
            WHERE toLower(t.name) CONTAINS toLower($topic)
            RETURN c.id AS chunk_id, c.text AS text, c.source AS source, t.name AS topic
            LIMIT $limit
            """,
            topic=topic_name,
            limit=limit,
        )
        return [dict(r) for r in result]


def get_products_by_category(category_name, limit=10):
    """
    Get products in a category (supports partial match).

    Returns:
        list of dicts {product_id, name, price, stock, category}
    """
    driver = get_driver()
    with driver.session() as session:
        result = session.run(
            """
            WITH
                'id' AS id_key,
                'product_id' AS product_id_key,
                'name' AS name_key,
                'price' AS price_key,
                'stock' AS stock_key,
                'category' AS category_key
            MATCH (p:Product)
            WITH
                coalesce(p[id_key], p[product_id_key]) AS product_id,
                p[name_key] AS name,
                p[price_key] AS price,
                coalesce(p[stock_key], 1) AS stock,
                p[category_key] AS product_category
            WHERE product_category IS NOT NULL
              AND toLower(product_category) CONTAINS toLower($category)
              AND stock > 0
            RETURN product_id, name, price, stock, product_category AS category
            ORDER BY coalesce(price, 0) ASC
            LIMIT $limit
            """,
            category=category_name,
            limit=limit,
        )
        return [dict(r) for r in result]


def get_related_chunks(chunk_id, limit=3):
    """Get adjacent chunks for context expansion."""
    driver = get_driver()
    with driver.session() as session:
        result = session.run(
            """
            MATCH (c:Chunk {id: $chunk_id})-[:RELATED_TO]->(related:Chunk)
            RETURN related.id AS chunk_id, related.text AS text, related.source AS source
            LIMIT $limit
            """,
            chunk_id=chunk_id,
            limit=limit,
        )
        return [dict(r) for r in result]


def get_document_structure():
    """
    Get overview of the KB graph: documents, topics, product categories.

    Returns:
        dict with documents, topics, categories
    """
    driver = get_driver()
    with driver.session() as session:
        docs = session.run(
            "MATCH (d:Document) RETURN d.filename AS filename, d.source_type AS type"
        )
        topics = session.run(
            """
            MATCH (t:Topic)<-[:MENTIONS_TOPIC]-(c:Chunk)
            RETURN t.name AS topic, count(c) AS chunk_count
            ORDER BY chunk_count DESC
            """
        )
        categories = session.run(
            """
            MATCH (p:Product)-[:IN_CATEGORY]->(cat:Category)
            RETURN cat.name AS category, count(p) AS product_count
            ORDER BY product_count DESC
            """
        )
        return {
            'documents': [dict(r) for r in docs],
            'topics': [dict(r) for r in topics],
            'categories': [dict(r) for r in categories],
        }


def clear_graph():
    """Delete all nodes and relationships (for re-indexing)."""
    driver = get_driver()
    with driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")
    logger.info("Neo4j graph cleared")


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _extract_topics(text):
    """Extract markdown heading text as topics."""
    topics = []
    for line in text.split('\n'):
        line = line.strip()
        if line.startswith('## ') or line.startswith('### '):
            topic = line.lstrip('#').strip()
            if topic:
                topics.append(topic)
    return topics
