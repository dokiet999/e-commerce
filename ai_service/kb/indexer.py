"""
KB Indexer — indexes documents and product data into ChromaDB and Neo4j.

ChromaDB : semantic similarity search (vector embeddings)
Neo4j    : structured knowledge graph (topics, categories, product relations)

Usage:
    python manage.py index_kb
    python manage.py index_kb --source products
    python manage.py index_kb --source docs
"""

import os
import glob
import logging

import requests
from langchain_text_splitters import RecursiveCharacterTextSplitter

from .vector_store import get_vectorstore, get_embeddings, reset_vectorstore
from .neo4j_store import (
    index_document_chunks,
    index_product,
    init_constraints,
    clear_graph,
)

logger = logging.getLogger(__name__)

CHUNK_SIZE = 500
CHUNK_OVERLAP = 50


def get_text_splitter():
    return RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=['\n## ', '\n### ', '\n\n', '\n', '. ', ' ', ''],
    )


def index_documents():
    """Index all markdown documents from kb/data/ directory."""
    data_dir = os.path.join(os.path.dirname(__file__), 'data')
    if not os.path.exists(data_dir):
        logger.warning(f"Data directory not found: {data_dir}")
        return 0

    splitter = get_text_splitter()
    vs = get_vectorstore()

    total_chunks = 0
    for filepath in glob.glob(os.path.join(data_dir, '*.md')):
        filename = os.path.basename(filepath)
        logger.info(f"Indexing {filename}...")

        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        chunks = splitter.split_text(content)
        if not chunks:
            continue

        # Create metadata for each chunk
        metadatas = [
            {
                'source': filename,
                'source_type': 'document',
                'chunk_index': i,
            }
            for i in range(len(chunks))
        ]

        ids = [f"doc_{filename}_{i}" for i in range(len(chunks))]

        vs.add_texts(texts=chunks, metadatas=metadatas, ids=ids)

        # Also index into Neo4j knowledge graph
        index_document_chunks(filename, chunks, source_type='document')

        total_chunks += len(chunks)
        logger.info(f"  -> {len(chunks)} chunks indexed")

    logger.info(f"Total document chunks indexed: {total_chunks}")
    return total_chunks


def index_products():
    """Index product data from the product service."""
    try:
        from django.conf import settings
        product_url = settings.PRODUCT_SERVICE_URL
    except Exception:
        product_url = 'http://localhost:8002'

    try:
        resp = requests.get(f'{product_url}/api/products/', timeout=10)
        resp.raise_for_status()
        products = resp.json()
    except Exception as e:
        logger.error(f"Failed to fetch products: {e}")
        return 0

    if not products:
        logger.warning("No products found")
        return 0

    # Also fetch categories
    categories = {}
    try:
        cat_resp = requests.get(f'{product_url}/api/products/categories/', timeout=10)
        if cat_resp.ok:
            for cat in cat_resp.json():
                categories[cat['id']] = cat['name']
    except Exception:
        pass

    splitter = get_text_splitter()
    vs = get_vectorstore()

    total_chunks = 0
    for p in products:
        cat_name = categories.get(p.get('category'), 'Unknown')
        # Build product text
        text = (
            f"Sản phẩm: {p['name']}\n"
            f"Danh mục: {cat_name}\n"
            f"Giá: ${p['price']}\n"
            f"Tình trạng: {'Còn hàng' if p.get('stock', 0) > 0 else 'Hết hàng'} "
            f"({p.get('stock', 0)} sản phẩm)\n"
        )
        if p.get('description'):
            text += f"Mô tả: {p['description']}\n"

        chunks = splitter.split_text(text)
        metadatas = [
            {
                'source': f"product_{p['id']}",
                'source_type': 'product',
                'product_id': str(p['id']),
                'product_name': p['name'],
                'category': cat_name,
                'price': str(p['price']),
                'chunk_index': i,
            }
            for i in range(len(chunks))
        ]

        ids = [f"product_{p['id']}_{i}" for i in range(len(chunks))]
        vs.add_texts(texts=chunks, metadatas=metadatas, ids=ids)

        # Also index into Neo4j knowledge graph
        index_product(
            product_id=p['id'],
            name=p['name'],
            category_name=cat_name,
            price=p['price'],
            stock=p.get('stock', 0),
            description=p.get('description', ''),
        )

        total_chunks += len(chunks)

    logger.info(f"Total product chunks indexed: {total_chunks}")
    return total_chunks


def index_all():
    """Index everything: documents + products into ChromaDB and Neo4j."""
    reset_vectorstore()
    # Initialize Neo4j constraints then clear existing graph
    try:
        init_constraints()
        clear_graph()
    except Exception as e:
        logger.warning(f"Neo4j not available, skipping graph indexing: {e}")

    doc_count = index_documents()
    product_count = index_products()
    total = doc_count + product_count
    logger.info(f"KB indexing complete: {total} total chunks ({doc_count} docs + {product_count} products)")
    return total
