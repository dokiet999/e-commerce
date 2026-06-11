import logging

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from shared.rbac import get_user_id
from behavior.models import BehaviorEvent, UserBehaviorProfile
from .models import ChatSession, ChatMessage
from .serializers import ChatRequestSerializer
from .rag_engine import get_chat_response

logger = logging.getLogger(__name__)


def _get_user_and_session(request):
    """Extract user_id from JWT and session_id from header."""
    user_id = get_user_id(request)
    session_id = (
        request.headers.get('X-Session-Id')
        or request.META.get('HTTP_X_USER_SESSION_ID')
    )
    return user_id, session_id


def _get_behavior_profile(user_id, session_id):
    """Get behavior profile and ML prediction for user."""
    profile = None
    if user_id:
        profile = UserBehaviorProfile.objects.filter(user_id=user_id).first()
    if not profile and session_id:
        profile = UserBehaviorProfile.objects.filter(session_id=session_id).first()

    if not profile:
        return None

    result = {
        'predicted_intent': profile.predicted_intent,
        'preferred_categories': profile.preferred_categories,
        'price_range_preference': profile.price_range_preference,
        'purchase_likelihood': profile.purchase_likelihood,
    }

    # Try ML prediction if available
    try:
        events = BehaviorEvent.objects.all()
        if user_id:
            events = events.filter(user_id=user_id)
        else:
            events = events.filter(session_id=session_id)

        event_list = list(events.values(
            'event_type', 'product_id', 'category_id', 'metadata', 'created_at'
        )[:50])

        if event_list:
            from ml.inference import predict_behavior
            prediction = predict_behavior(event_list)
            result.update({
                'predicted_intent': prediction['predicted_intent'],
                'purchase_likelihood': prediction['purchase_likelihood'],
            })
    except Exception as e:
        logger.debug(f"ML prediction unavailable: {e}")

    return result


@api_view(['POST'])
def chat(request):
    """Send a message and get AI consultation response."""
    serializer = ChatRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    user_id, session_id = _get_user_and_session(request)
    message = serializer.validated_data['message']
    chat_session_id = serializer.validated_data.get('chat_session_id')

    # Get or create chat session
    chat_session = None
    if chat_session_id:
        try:
            chat_session = ChatSession.objects.get(
                id=chat_session_id, is_active=True,
            )
        except ChatSession.DoesNotExist:
            pass

    if not chat_session:
        chat_session = ChatSession.objects.create(
            user_id=user_id,
            session_id=session_id,
        )

    # Save user message
    ChatMessage.objects.create(
        chat_session=chat_session,
        role='user',
        content=message,
    )

    # Get chat history (last 10 messages)
    history_msgs = ChatMessage.objects.filter(
        chat_session=chat_session,
    ).order_by('-created_at')[:10]

    chat_history = [
        (msg.role, msg.content)
        for msg in reversed(list(history_msgs))
    ][:-1]  # Exclude the message we just saved (it's passed as question)

    # Get behavior profile
    behavior_profile = _get_behavior_profile(user_id, session_id)

    # Get RAG response (routes to Graph QA for behavior queries)
    graph_user_id = f'U{user_id:03d}' if isinstance(user_id, int) and user_id <= 500 else None
    result = get_chat_response(
        question=message,
        chat_history=chat_history,
        behavior_profile=behavior_profile,
        user_id=graph_user_id,
    )

    # Save assistant response
    ChatMessage.objects.create(
        chat_session=chat_session,
        role='assistant',
        content=result['response'],
        metadata={'sources': result['sources']},
    )

    return Response({
        'response': result['response'],
        'sources': result['sources'],
        'chat_session_id': str(chat_session.id),
    })


@api_view(['GET'])
def chat_history(request):
    """Get chat history for the current session."""
    user_id, session_id = _get_user_and_session(request)
    chat_session_id = request.query_params.get('chat_session_id')

    if chat_session_id:
        try:
            session = ChatSession.objects.get(id=chat_session_id)
        except ChatSession.DoesNotExist:
            return Response({'error': 'Session not found'}, status=404)
    else:
        # Get most recent active session
        qs = ChatSession.objects.filter(is_active=True)
        if user_id:
            qs = qs.filter(user_id=user_id)
        elif session_id:
            qs = qs.filter(session_id=session_id)
        else:
            return Response({'messages': []})

        session = qs.first()
        if not session:
            return Response({'messages': []})

    messages = ChatMessage.objects.filter(chat_session=session).order_by('created_at')

    return Response({
        'chat_session_id': str(session.id),
        'messages': [
            {
                'role': msg.role,
                'content': msg.content,
                'created_at': msg.created_at.isoformat(),
            }
            for msg in messages
        ],
    })


@api_view(['DELETE'])
def clear_chat(request):
    """End/clear current chat session."""
    user_id, session_id = _get_user_and_session(request)
    chat_session_id = request.query_params.get('chat_session_id')

    if chat_session_id:
        try:
            session = ChatSession.objects.get(id=chat_session_id)
            session.is_active = False
            session.save()
        except ChatSession.DoesNotExist:
            pass
    else:
        qs = ChatSession.objects.filter(is_active=True)
        if user_id:
            qs = qs.filter(user_id=user_id)
        elif session_id:
            qs = qs.filter(session_id=session_id)
        qs.update(is_active=False)

    return Response({'status': 'cleared'})
