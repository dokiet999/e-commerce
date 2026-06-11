"""
ChromaDB vector store for the Knowledge Base.
Uses LangChain's Chroma wrapper with HuggingFace embeddings.
"""

import os
import logging

from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

logger = logging.getLogger(__name__)

_vectorstore = None
_embeddings = None


def get_embeddings():
    """Get the singleton embedding model."""
    global _embeddings
    if _embeddings is None:
        try:
            from django.conf import settings
            model_name = settings.EMBEDDING_MODEL
        except Exception:
            model_name = 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'

        logger.info(f"Loading embedding model: {model_name}")
        _embeddings = HuggingFaceEmbeddings(
            model_name=model_name,
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True},
        )
    return _embeddings


def get_vectorstore(collection_name='kb_documents'):
    """Get or create the ChromaDB vector store."""
    global _vectorstore
    if _vectorstore is None:
        try:
            from django.conf import settings
            persist_dir = settings.CHROMA_PERSIST_DIR
        except Exception:
            persist_dir = os.path.join(os.path.dirname(__file__), 'chroma_db')

        os.makedirs(persist_dir, exist_ok=True)

        _vectorstore = Chroma(
            collection_name=collection_name,
            embedding_function=get_embeddings(),
            persist_directory=persist_dir,
        )
        logger.info(f"ChromaDB initialized at {persist_dir}")

    return _vectorstore


def get_retriever(search_kwargs=None):
    """Get a LangChain retriever from the vector store."""
    if search_kwargs is None:
        search_kwargs = {'k': 5}
    vs = get_vectorstore()
    return vs.as_retriever(search_kwargs=search_kwargs)


def reset_vectorstore():
    """Reset the singleton (for testing/reindexing)."""
    global _vectorstore
    _vectorstore = None
