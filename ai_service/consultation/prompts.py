"""
Prompt templates for the RAG consultation chatbot.
"""

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

SYSTEM_PROMPT = """Bạn là trợ lý tư vấn mua sắm AI của eCommerceStore — một cửa hàng thương mại điện tử trực tuyến.

Nhiệm vụ của bạn:
- Tư vấn sản phẩm phù hợp với nhu cầu khách hàng
- Trả lời câu hỏi về chính sách cửa hàng (đổi trả, vận chuyển, thanh toán)
- Hướng dẫn mua hàng, so sánh sản phẩm
- Đề xuất sản phẩm dựa trên hành vi và sở thích khách hàng

Quy tắc:
- Trả lời bằng tiếng Việt, thân thiện và chuyên nghiệp
- Chỉ giới thiệu sản phẩm và thông tin CÓ trong dữ liệu được cung cấp
- KHÔNG bịa đặt giá, tồn kho hoặc thông tin sản phẩm không có trong context
- Nếu không có thông tin, hãy thành thật nói rằng bạn không có thông tin đó và đề nghị khách hàng liên hệ CSKH
- Giữ câu trả lời ngắn gọn, có cấu trúc rõ ràng
- Khi gợi ý sản phẩm, luôn kèm giá và tình trạng tồn kho nếu có
- Không tiết lộ suy luận nội bộ, phân tích, kế hoạch, chain-of-thought hoặc ghi chú.
- Chỉ trả về câu trả lời cuối cùng cho khách hàng. Không bắt đầu bằng "Okay", "Let me", hoặc giải thích cách bạn suy nghĩ.

{behavior_context}"""

BEHAVIOR_CONTEXT_TEMPLATE = """
Thông tin hành vi khách hàng:
- Xu hướng: {predicted_intent}
- Danh mục yêu thích: {preferred_categories}
- Mức giá trung bình quan tâm: {price_range}
- Khả năng mua hàng: {purchase_likelihood}
"""

NO_BEHAVIOR_CONTEXT = ""

CONSULTATION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", """Dựa trên thông tin từ cơ sở dữ liệu:

{context}

Câu hỏi của khách hàng: {question}"""),
])


def format_behavior_context(profile_data):
    """Format behavior profile into prompt context string."""
    if not profile_data:
        return NO_BEHAVIOR_CONTEXT

    predicted_intent = profile_data.get('predicted_intent', 'chưa xác định')
    intent_vi = {
        'browsing': 'đang tìm hiểu, khám phá sản phẩm',
        'buying': 'có ý định mua hàng cao',
        'comparing': 'đang so sánh các sản phẩm',
        'returning': 'có thể muốn đổi/trả hàng',
    }

    preferred = profile_data.get('preferred_categories', {})
    if preferred:
        cat_str = ', '.join(
            f"category {k} ({v} lần xem)"
            for k, v in sorted(preferred.items(), key=lambda x: -x[1])[:3]
        )
    else:
        cat_str = 'chưa có dữ liệu'

    price_range = profile_data.get('price_range_preference', {})
    if price_range:
        price_str = f"${price_range.get('min', '?')} - ${price_range.get('max', '?')}"
    else:
        price_str = 'chưa có dữ liệu'

    purchase = profile_data.get('purchase_likelihood')
    purchase_str = f"{purchase:.0%}" if purchase is not None else 'chưa có dữ liệu'

    return BEHAVIOR_CONTEXT_TEMPLATE.format(
        predicted_intent=intent_vi.get(predicted_intent, predicted_intent),
        preferred_categories=cat_str,
        price_range=price_str,
        purchase_likelihood=purchase_str,
    )
