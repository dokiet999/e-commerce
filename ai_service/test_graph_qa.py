"""
Test script for Graph QA pipeline: Text → Cypher → Neo4j → LLM → Answer
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ai_config.settings')
django.setup()

from consultation.graph_qa import is_behavior_query, graph_qa_response, _extract_cypher, _execute_cypher

print("=" * 70)
print("TEST 1: Keyword detection (is_behavior_query)")
print("=" * 70)

test_questions = [
    ("User nào mua hàng nhiều nhất?", True),
    ("Sản phẩm nào phù hợp với tôi?", True),
    ("Thống kê hành vi người dùng", True),
    ("Người dùng thường dùng thiết bị gì?", True),
    ("Chính sách bảo hành như thế nào?", False),
    ("Cách thanh toán bằng thẻ tín dụng", False),
    ("Lịch sử mua hàng của tôi", True),
    ("Top sản phẩm trending", True),
]

for q, expected in test_questions:
    result = is_behavior_query(q)
    status = "✓" if result == expected else "✗"
    print(f"  {status} '{q}' → {result} (expected {expected})")

print()
print("=" * 70)
print("TEST 2: Direct Cypher execution on behavior graph")
print("=" * 70)

test_queries = [
    ("Count users", "MATCH (u:User) RETURN count(u) AS total_users"),
    ("Count products", "MATCH (p:Product) RETURN count(p) AS total_products"),
    ("Top 5 purchased products", """
        MATCH (u:User)-[:PURCHASED]->(p:Product)
        RETURN p.product_id AS product, p.category AS category, count(u) AS purchases
        ORDER BY purchases DESC LIMIT 5
    """),
    ("Top devices", """
        MATCH (s:Session)-[:USED_DEVICE]->(d:Device)
        RETURN d.device_name AS device, count(s) AS sessions
        ORDER BY sessions DESC
    """),
    ("User U001 actions", """
        MATCH (u:User {user_id: 'U001'})-[:HAS_SESSION]->(s:Session)-[:PERFORMED]->(a:Action)
        RETURN a.action_type AS action, count(s) AS times
        ORDER BY times DESC
    """),
]

for name, cypher in test_queries:
    try:
        results = _execute_cypher(cypher)
        print(f"\n  ✓ {name}:")
        for r in results:
            print(f"    {r}")
    except Exception as e:
        print(f"\n  ✗ {name}: {e}")

print()
print("=" * 70)
print("TEST 3: Cypher safety check (_extract_cypher)")
print("=" * 70)

safe_tests = [
    ("MATCH (u:User) RETURN count(u)", True),
    ("CREATE (u:User {name: 'hack'})", False),
    ("MATCH (u:User) DETACH DELETE u", False),
    ("MATCH (u:User) SET u.name = 'hack'", False),
    ("```cypher\nMATCH (u:User) RETURN count(u)\n```", True),
    ("UNSUPPORTED", False),
    ("random text not cypher", False),
]

for text, should_pass in safe_tests:
    result = _extract_cypher(text)
    passed = result is not None
    status = "✓" if passed == should_pass else "✗"
    print(f"  {status} '{text[:50]}...' → {'ALLOWED' if passed else 'BLOCKED'} (expected {'ALLOW' if should_pass else 'BLOCK'})")

print()
print("=" * 70)
print("TEST 4: Full Graph QA pipeline (requires LLM)")
print("=" * 70)

llm_available = os.environ.get('OPENAI_API_KEY') or os.environ.get('OLLAMA_BASE_URL')
if not llm_available:
    print("  ⚠ Skipping LLM tests — set OPENAI_API_KEY or OLLAMA_BASE_URL")
    print("  To test manually:")
    print("    from consultation.graph_qa import graph_qa_response")
    print("    result = graph_qa_response('User nào mua hàng nhiều nhất?')")
    print("    print(result)")
else:
    test_llm_questions = [
        "User nào mua hàng nhiều nhất?",
        "Sản phẩm nào được xem nhiều nhất?",
        "User U001 có hành vi gì?",
        "Thiết bị nào phổ biến nhất?",
        "Danh mục electronics có bao nhiêu sản phẩm?",
    ]

    for q in test_llm_questions:
        print(f"\n  Q: {q}")
        try:
            result = graph_qa_response(q, user_id='U001')
            print(f"  Cypher: {result['cypher']}")
            print(f"  Results count: {len(result['results'])}")
            print(f"  Answer: {result['response'][:200]}")
        except Exception as e:
            print(f"  ✗ Error: {e}")

print("\n" + "=" * 70)
print("DONE")
print("=" * 70)
