import pandas as pd
import numpy as np
from neo4j import GraphDatabase
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import networkx as nx
import warnings
warnings.filterwarnings('ignore')

# ==============================================================================
# BƯỚC 1 - KẾT NỐI NEO4J
# ==============================================================================
print("=" * 80)
print("BƯỚC 1 - KẾT NỐI NEO4J")
print("=" * 80)

NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "neo4j_password"  # Từ docker-compose.yml

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
driver.verify_connectivity()
print(f"Kết nối thành công tới {NEO4J_URI}")

# ==============================================================================
# BƯỚC 2 - THIẾT KẾ SCHEMA & TẠO CONSTRAINTS
# ==============================================================================
print("\n" + "=" * 80)
print("BƯỚC 2 - THIẾT KẾ SCHEMA VÀ TẠO CONSTRAINTS")
print("=" * 80)


def run_query(query, parameters=None):
    with driver.session() as session:
        result = session.run(query, parameters or {})
        return [record.data() for record in result]


# Xóa dữ liệu cũ (nếu có)
print("Xóa dữ liệu cũ...")
run_query("MATCH (n) DETACH DELETE n")

# Tạo constraints cho uniqueness
constraints = [
    "CREATE CONSTRAINT IF NOT EXISTS FOR (u:User) REQUIRE u.user_id IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (p:Product) REQUIRE p.product_id IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (a:Action) REQUIRE a.action_type IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (d:Device) REQUIRE d.device_name IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (s:Session) REQUIRE s.session_id IS UNIQUE",
]

for c in constraints:
    run_query(c)
    print(f"  ✓ {c.split('FOR')[1].split('REQUIRE')[0].strip()}")

print("Constraints tạo thành công!")

# ==============================================================================
# BƯỚC 3 - IMPORT DATA THEO BATCH
# ==============================================================================
print("\n" + "=" * 80)
print("BƯỚC 3 - IMPORT DATA")
print("=" * 80)

df = pd.read_csv('data_user500.csv')
print(f"Đọc {len(df)} dòng từ data_user500.csv")

BATCH_SIZE = 100
total_batches = (len(df) + BATCH_SIZE - 1) // BATCH_SIZE

# Cypher query để tạo nodes và relationships cho 1 batch
IMPORT_QUERY = """
UNWIND $rows AS row

MERGE (u:User {user_id: row.user_id})

MERGE (p:Product {product_id: row.product_id})
SET p.category = row.category

MERGE (a:Action {action_type: row.action})

MERGE (d:Device {device_name: row.device})

MERGE (s:Session {session_id: row.session_id})
SET s.timestamp = row.timestamp, s.duration_seconds = row.duration_seconds

MERGE (u)-[:HAS_SESSION]->(s)
MERGE (s)-[:PERFORMED]->(a)
MERGE (a)-[:ON_PRODUCT]->(p)
MERGE (s)-[:USED_DEVICE]->(d)

WITH u, p, row
WHERE row.action IN ['view', 'click']
MERGE (u)-[:INTERESTED_IN]->(p)
"""

PURCHASE_QUERY = """
UNWIND $rows AS row
WITH row
WHERE row.action = 'purchase'
MATCH (u:User {user_id: row.user_id})
MATCH (p:Product {product_id: row.product_id})
MERGE (u)-[:PURCHASED]->(p)
"""

for i in range(0, len(df), BATCH_SIZE):
    batch = df.iloc[i:i + BATCH_SIZE]
    rows = batch.to_dict('records')

    batch_num = i // BATCH_SIZE + 1
    run_query(IMPORT_QUERY, {"rows": rows})
    run_query(PURCHASE_QUERY, {"rows": rows})

    if batch_num % 10 == 0 or batch_num == total_batches:
        print(f"  Batch {batch_num}/{total_batches} ({min(i + BATCH_SIZE, len(df))}/{len(df)} dòng)")

# Thống kê nodes và relationships
stats = run_query("""
    MATCH (n)
    RETURN labels(n)[0] AS label, count(n) AS count
    ORDER BY count DESC
""")
print("\nThống kê Nodes:")
for s in stats:
    print(f"  {s['label']}: {s['count']}")

rel_stats = run_query("""
    MATCH ()-[r]->()
    RETURN type(r) AS type, count(r) AS count
    ORDER BY count DESC
""")
print("\nThống kê Relationships:")
for s in rel_stats:
    print(f"  {s['type']}: {s['count']}")

# ==============================================================================
# BƯỚC 4 - TRUY VẤN MINH HỌA
# ==============================================================================
print("\n" + "=" * 80)
print("BƯỚC 4 - TRUY VẤN MINH HỌA")
print("=" * 80)

# Query 1: Top 10 sản phẩm được xem nhiều nhất
print("\n--- Query 1: Top 10 sản phẩm được xem nhiều nhất ---")
q1 = run_query("""
    MATCH (s:Session)-[:PERFORMED]->(a:Action {action_type: 'view'})-[:ON_PRODUCT]->(p:Product)
    RETURN p.product_id AS product, p.category AS category, count(s) AS view_count
    ORDER BY view_count DESC
    LIMIT 10
""")
for r in q1:
    print(f"  {r['product']} ({r['category']}): {r['view_count']} views")

# Query 2: User nào có nhiều hành vi nhất
print("\n--- Query 2: Top 10 User có nhiều hành vi nhất ---")
q2 = run_query("""
    MATCH (u:User)-[:HAS_SESSION]->(s:Session)
    RETURN u.user_id AS user, count(s) AS session_count
    ORDER BY session_count DESC
    LIMIT 10
""")
for r in q2:
    print(f"  {r['user']}: {r['session_count']} sessions")

# Query 3: Tỉ lệ purchase theo category
print("\n--- Query 3: Tỉ lệ purchase theo category ---")
q3 = run_query("""
    MATCH (s:Session)-[:PERFORMED]->(a:Action {action_type: 'purchase'})-[:ON_PRODUCT]->(p:Product)
    WITH p.category AS category, count(s) AS purchase_count
    MATCH (s2:Session)-[:PERFORMED]->(:Action)-[:ON_PRODUCT]->(p2:Product)
    WHERE p2.category = category
    WITH category, purchase_count, count(s2) AS total_actions
    RETURN category, purchase_count, total_actions,
           round(100.0 * purchase_count / total_actions, 2) AS purchase_rate_pct
    ORDER BY purchase_rate_pct DESC
""")
for r in q3:
    print(f"  {r['category']}: {r['purchase_count']}/{r['total_actions']} ({r['purchase_rate_pct']}%)")

# Query 4: Sản phẩm được add_to_cart nhưng chưa purchase
print("\n--- Query 4: Sản phẩm add_to_cart nhưng chưa purchase ---")
q4 = run_query("""
    MATCH (s:Session)-[:PERFORMED]->(a:Action {action_type: 'add_to_cart'})-[:ON_PRODUCT]->(p:Product)
    WHERE NOT EXISTS {
        MATCH (:Session)-[:PERFORMED]->(a2:Action {action_type: 'purchase'})-[:ON_PRODUCT]->(p)
    }
    RETURN p.product_id AS product, p.category AS category, count(s) AS cart_count
    ORDER BY cart_count DESC
    LIMIT 10
""")
if q4:
    for r in q4:
        print(f"  {r['product']} ({r['category']}): {r['cart_count']} lần add_to_cart, 0 purchase")
else:
    print("  Không có sản phẩm nào chỉ add_to_cart mà không purchase (data random)")

# Query 5: Mobile vs Desktop - ai mua nhiều hơn?
print("\n--- Query 5: Mobile vs Desktop - ai mua hàng nhiều hơn? ---")
q5 = run_query("""
    MATCH (s:Session)-[:PERFORMED]->(a:Action {action_type: 'purchase'})
    MATCH (s)-[:USED_DEVICE]->(d:Device)
    RETURN d.device_name AS device, count(s) AS purchase_count
    ORDER BY purchase_count DESC
""")
for r in q5:
    print(f"  {r['device']}: {r['purchase_count']} purchases")

# ==============================================================================
# BƯỚC 5 - VISUALIZE SUBGRAPH
# ==============================================================================
print("\n" + "=" * 80)
print("BƯỚC 5 - VISUALIZE SUBGRAPH (20 dòng đầu)")
print("=" * 80)

# Lấy subgraph từ 20 dòng đầu
sub_df = df.head(20)

G = nx.DiGraph()

# Màu sắc cho từng loại node
color_map = {
    'User': '#FF6B6B',
    'Product': '#4ECDC4',
    'Action': '#45B7D1',
    'Device': '#96CEB4',
    'Session': '#FFEAA7',
}

node_types = {}

for _, row in sub_df.iterrows():
    user = row['user_id']
    product = row['product_id']
    action = row['action']
    device = row['device']
    session = row['session_id']

    # Add nodes
    G.add_node(user)
    node_types[user] = 'User'

    G.add_node(product)
    node_types[product] = 'Product'

    G.add_node(action)
    node_types[action] = 'Action'

    G.add_node(device)
    node_types[device] = 'Device'

    short_session = session[-5:]  # Rút gọn session_id để hiển thị
    G.add_node(short_session)
    node_types[short_session] = 'Session'

    # Add edges
    G.add_edge(user, short_session, label='HAS_SESSION')
    G.add_edge(short_session, action, label='PERFORMED')
    G.add_edge(action, product, label='ON_PRODUCT')
    G.add_edge(short_session, device, label='USED_DEVICE')

    if row['action'] in ['view', 'click']:
        G.add_edge(user, product, label='INTERESTED_IN')
    if row['action'] == 'purchase':
        G.add_edge(user, product, label='PURCHASED')

# Vẽ đồ thị
fig, ax = plt.subplots(figsize=(18, 14))

pos = nx.spring_layout(G, k=1.8, iterations=50, seed=42)

# Node colors theo type
node_colors = [color_map.get(node_types.get(n, 'Session'), '#CCCCCC') for n in G.nodes()]

# Node size tỉ lệ với degree
degrees = dict(G.degree())
node_sizes = [max(300, degrees[n] * 200) for n in G.nodes()]

# Vẽ edges
nx.draw_networkx_edges(G, pos, ax=ax, edge_color='#999999',
                       arrows=True, arrowsize=15, alpha=0.6,
                       connectionstyle="arc3,rad=0.1")

# Vẽ nodes
nx.draw_networkx_nodes(G, pos, ax=ax, node_color=node_colors,
                       node_size=node_sizes, alpha=0.9, edgecolors='white', linewidths=1.5)

# Vẽ labels
nx.draw_networkx_labels(G, pos, ax=ax, font_size=7, font_weight='bold')

# Edge labels
edge_labels = nx.get_edge_attributes(G, 'label')
nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, ax=ax,
                             font_size=5, font_color='#555555')

# Legend
legend_elements = [
    plt.scatter([], [], c=color_map['User'], s=150, label=f"User ({sum(1 for v in node_types.values() if v == 'User')})"),
    plt.scatter([], [], c=color_map['Product'], s=150, label=f"Product ({sum(1 for v in node_types.values() if v == 'Product')})"),
    plt.scatter([], [], c=color_map['Action'], s=150, label=f"Action ({sum(1 for v in node_types.values() if v == 'Action')})"),
    plt.scatter([], [], c=color_map['Device'], s=150, label=f"Device ({sum(1 for v in node_types.values() if v == 'Device')})"),
    plt.scatter([], [], c=color_map['Session'], s=150, label=f"Session ({sum(1 for v in node_types.values() if v == 'Session')})"),
]
ax.legend(handles=legend_elements, loc='upper left', fontsize=10, framealpha=0.9)

ax.set_title('Knowledge Base Graph - Subgraph (20 dòng đầu)\nNode size ~ degree', fontsize=14, fontweight='bold')
ax.axis('off')

plt.tight_layout()
plt.savefig('knowledge_graph.png', dpi=150, bbox_inches='tight')
print("Đã lưu biểu đồ: knowledge_graph.png")
print(f"Subgraph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

# Đóng kết nối
driver.close()
print("\nĐã đóng kết nối Neo4j.")
print("HOÀN TẤT!")
