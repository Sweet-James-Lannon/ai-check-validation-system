"""
Services Package - Business Logic Layer

This package contains all business logic services that can be easily
tested, maintained, and scaled independently of the Flask routes.

Current Services:
- ai_service: Core AI model interactions and management
- [Future] salesforce_service: API integration and data sync  
- [Future] query_classifier: AI-powered query routing
- [Future] nl2sql_engine: Natural language to SQL conversion
- [Future] vector_rag_service: Document retrieval and generation
- [Future] validation_engine: Check validation business logic
- [Future] audit_service: Compliance logging and reporting
"""

from .ai_service import ai_service

__all__ = [
    'ai_service'
]