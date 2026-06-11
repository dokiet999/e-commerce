"""Quick test for Graph QA pipeline with LLM."""
import os, sys, django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ['DJANGO_SETTINGS_MODULE'] = 'ai_config.settings'
os.environ['LLM_PROVIDER'] = 'ollama'
os.environ['OLLAMA_MODEL'] = 'gemma3:1b'
os.environ['OLLAMA_BASE_URL'] = 'http://localhost:11434'
django.setup()

from consultation.graph_qa import graph_qa_response

questions = [
    'User nao mua hang nhieu nhat?',
    'San pham nao duoc xem nhieu nhat?',
    'User U001 co hanh vi gi?',
    'Thiet bi nao pho bien nhat?',
    'Danh muc electronics co bao nhieu san pham?',
]

for q in questions:
    print(f'\nQ: {q}')
    result = graph_qa_response(q, user_id='U001')
    cypher = result['cypher']
    results = result['results'][:3]
    answer = result['response'][:300]
    print(f'Cypher: {cypher}')
    print(f'Results: {results}')
    print(f'Answer: {answer}')
    print('-' * 60)
