"""
Chat Routes - Clean API endpoints using service layer
All AI logic delegated to services for better modularity
"""

from flask import Blueprint, request, jsonify, session
from utils.decorators import login_required
from utils.logger import get_api_logger
from services.ai_service import ai_service

chat_bp = Blueprint("chat", __name__)
api_logger = get_api_logger()

@chat_bp.route("/api/chat", methods=["POST"])
@login_required
def chat_endpoint():
    """Main chat endpoint - delegates to AI service"""
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()
        
        if not user_message:
            return jsonify({"error": "Message is required"}), 400
        
        # Get user context from session
        user = session.get("user", {})
        user_name = user.get("name", "User")
        
        api_logger.info(f"Chat request from {user_name}: {user_message[:100]}...")
        
        # Delegate to AI service
        result = ai_service.validate_check_query(user_message, user)
        
        if result["status"] == "success":
            api_logger.info(f"AI response generated for {user_name}")
            return jsonify(result)
        else:
            api_logger.error(f"AI service error: {result.get('details', 'Unknown error')}")
            return jsonify(result), 500
        
    except Exception as e:
        api_logger.error(f"Chat endpoint error: {str(e)}")
        return jsonify({
            "error": "I'm experiencing technical difficulties. Please try again in a moment.",
            "status": "error"
        }), 500

@chat_bp.route("/api/chat/health", methods=["GET"])
@login_required
def chat_health():
    """Health check endpoint - delegates to AI service"""
    try:
        health_status = ai_service.health_check()
        
        if health_status["status"] == "healthy":
            return jsonify(health_status)
        else:
            return jsonify(health_status), 503
            
    except Exception as e:
        api_logger.error(f"Chat health check error: {str(e)}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e)
        }), 503

@chat_bp.route("/api/chat/classify", methods=["POST"])
@login_required
def classify_query():
    """Query classification endpoint - delegates to AI service"""
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        
        if not query:
            return jsonify({"error": "Query is required"}), 400
        
        # Delegate to AI service
        result = ai_service.classify_query(query)
        
        if result["status"] == "success":
            return jsonify(result)
        else:
            return jsonify(result), 500
        
    except Exception as e:
        api_logger.error(f"Query classification endpoint error: {str(e)}")
        return jsonify({
            "error": "Classification failed",
            "status": "error"
        }), 500