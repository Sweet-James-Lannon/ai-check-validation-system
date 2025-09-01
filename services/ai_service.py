"""
Modern AI Service - New OpenAI API with model selection flexibility
Inspired by Matt's Streamlit implementation but adapted for Flask
"""

from openai import OpenAI
import os
from typing import Dict, List, Optional
from utils.logger import get_api_logger

class AIService:
    def __init__(self):
        self.logger = get_api_logger()
        self._setup_openai_client()
        
        # Available models - similar to Matt's CHAT_LLM_OPTIONS
        self.available_models = {
            "gpt-4": {
                "name": "GPT-4",
                "description": "Most capable model, best for complex analysis",
                "max_tokens": 4000,
                "cost_per_1k": 0.03
            },
            "gpt-4-turbo": {
                "name": "GPT-4 Turbo",
                "description": "Faster GPT-4 with better performance",
                "max_tokens": 4000,
                "cost_per_1k": 0.01
            },
            "gpt-4o": {
                "name": "GPT-4o",
                "description": "Optimized for conversation and analysis",
                "max_tokens": 4000,
                "cost_per_1k": 0.005
            },
            "gpt-4o-mini": {
                "name": "GPT-4o Mini",
                "description": "Fast and cost-effective for most tasks",
                "max_tokens": 4000,
                "cost_per_1k": 0.0015
            },
            "gpt-3.5-turbo": {
                "name": "GPT-3.5 Turbo",
                "description": "Fast and economical for simple tasks",
                "max_tokens": 2000,
                "cost_per_1k": 0.002
            }
        }
        
        # Default model
        self.default_model = "gpt-4o-mini"
        
        # In-memory conversation storage (by user session)
        self.conversations = {}
        self.max_history_length = 10  # Keep last 10 exchanges
        
        # System prompts for different contexts
        self.prompts = {
            "check_validation": """You are an expert Check Validation Assistant for a financial services company. You help analysts validate financial transactions, detect fraud patterns, and ensure compliance.

Your capabilities include:
- Analyzing check validation data from Salesforce
- Identifying fraud indicators and suspicious patterns  
- Providing compliance guidance for financial regulations
- Generating detailed reports on transaction analysis
- Explaining validation results in clear, professional language

Always respond with:
1. Professional, confident tone suitable for financial analysts
2. Specific, actionable insights when possible
3. Clear explanations of risk factors or validation issues
4. Compliance-focused recommendations
5. Reference previous conversation context when relevant

If asked about specific data you don't have access to, explain that you need to query the Salesforce database and ask for clarification on search parameters.""",

            "query_classification": """Classify this check validation query into one of these categories:

SQL_QUERY: Factual questions that need database lookups (specific amounts, dates, payee names, counts, etc.)
VECTOR_SEARCH: Interpretive questions needing guidance (how to handle situations, compliance advice, general patterns)

Query: "{query}"

Respond with just: SQL_QUERY or VECTOR_SEARCH"""
        }
    
    def _setup_openai_client(self):
        """Setup OpenAI client with new API"""
        try:
            api_key = os.getenv('OPENAI_API_KEY')
            if api_key:
                self.client = OpenAI(api_key=api_key)
                self.logger.info("OpenAI client initialized successfully")
            else:
                self.client = None
                self.logger.warning("No OPENAI_API_KEY found in environment variables")
                
        except Exception as e:
            self.client = None
            self.logger.error(f"Failed to setup OpenAI client: {str(e)}")
    
    def get_available_models(self) -> Dict:
        """Get list of available models for frontend selection"""
        return self.available_models
    
    def _get_user_id(self, user_context: Optional[Dict] = None) -> str:
        """Extract user identifier for conversation tracking"""
        if user_context and user_context.get('oid'):
            return user_context['oid']  # Use Azure AD Object ID
        elif user_context and user_context.get('preferred_username'):
            return user_context['preferred_username']
        else:
            return 'anonymous'
    
    def _get_conversation_history(self, user_id: str) -> List[Dict[str, str]]:
        """Get conversation history for a user"""
        return self.conversations.get(user_id, [])
    
    def _add_to_conversation_history(self, user_id: str, role: str, content: str):
        """Add message to conversation history"""
        if user_id not in self.conversations:
            self.conversations[user_id] = []
        
        self.conversations[user_id].append({
            "role": role,
            "content": content
        })
        
        # Keep only recent history to avoid token limits
        if len(self.conversations[user_id]) > self.max_history_length * 2:  # *2 for user+assistant pairs
            # Keep recent exchanges
            recent_messages = self.conversations[user_id][-self.max_history_length * 2:]
            self.conversations[user_id] = recent_messages
    
    def clear_conversation_history(self, user_context: Optional[Dict] = None) -> Dict:
        """Clear conversation history for a user"""
        user_id = self._get_user_id(user_context)
        
        if user_id in self.conversations:
            del self.conversations[user_id]
            self.logger.info(f"Cleared conversation history for user {user_id}")
            return {"status": "success", "message": "Conversation history cleared"}
        else:
            return {"status": "success", "message": "No conversation history to clear"}
    
    def chat_completion(self, 
                       messages: List[Dict[str, str]], 
                       model: str = None,
                       max_tokens: int = None,
                       temperature: float = 0.7) -> Dict:
        """
        Generate chat completion using new OpenAI API
        """
        if not self.client:
            return {
                "success": False,
                "error": "OpenAI client not initialized",
                "content": None
            }
        
        # Use default model if none specified
        if not model:
            model = self.default_model
        
        # Get model config
        model_config = self.available_models.get(model, self.available_models[self.default_model])
        
        # Use model-specific max_tokens if not provided
        if not max_tokens:
            max_tokens = model_config.get("max_tokens", 1000)
        
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                presence_penalty=0.1,
                frequency_penalty=0.1
            )
            
            return {
                "success": True,
                "content": response.choices[0].message.content.strip(),
                "model_used": model,
                "tokens_used": response.usage.total_tokens,
                "model_info": model_config
            }
            
        except Exception as e:
            self.logger.error(f"Chat completion error with {model}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "content": None
            }
    
    def validate_check_query(self, 
                           user_message: str, 
                           user_context: Optional[Dict] = None,
                           selected_model: str = None) -> Dict:
        """Handle check validation conversations WITH MEMORY and model selection"""
        try:
            user_id = self._get_user_id(user_context)
            
            # Get conversation history
            history = self._get_conversation_history(user_id)
            
            # Build messages with history
            messages = [
                {"role": "system", "content": self.prompts["check_validation"]}
            ]
            
            # Add conversation history
            messages.extend(history)
            
            # Add current user message
            messages.append({"role": "user", "content": user_message})
            
            # Add user context if available
            if user_context:
                user_info = f"User: {user_context.get('name', 'Unknown')}"
                messages[0]["content"] += f"\n\nCurrent user context: {user_info}"
            
            # Use selected model or default
            model_to_use = selected_model or self.default_model
            
            result = self.chat_completion(messages, model=model_to_use)
            
            if result["success"]:
                # Store conversation history
                self._add_to_conversation_history(user_id, "user", user_message)
                self._add_to_conversation_history(user_id, "assistant", result["content"])
                
                self.logger.info(f"Check validation query processed successfully for {user_id} using {model_to_use}")
                return {
                    "response": result["content"],
                    "status": "success",
                    "tokens_used": result.get("tokens_used", 0),
                    "model_used": result.get("model_used"),
                    "model_info": result.get("model_info"),
                    "conversation_length": len(self._get_conversation_history(user_id))
                }
            else:
                return {
                    "error": "I'm experiencing technical difficulties. Please try again in a moment.",
                    "status": "error",
                    "details": result["error"]
                }
                
        except Exception as e:
            self.logger.error(f"Validate check query error: {str(e)}")
            return {
                "error": "Unable to process your request",
                "status": "error"
            }
    
    def classify_query(self, query: str, model: str = None) -> Dict:
        """
        Classify if query needs SQL database lookup or vector search
        """
        try:
            classification_prompt = self.prompts["query_classification"].format(query=query)
            messages = [{"role": "user", "content": classification_prompt}]
            
            # Use fast, cheap model for classification
            result = self.chat_completion(
                messages=messages,
                model=model or "gpt-3.5-turbo",
                max_tokens=10,
                temperature=0
            )
            
            if result["success"]:
                classification = result["content"].strip()
                return {
                    "query": query,
                    "classification": classification,
                    "status": "success"
                }
            else:
                return {
                    "error": "Classification failed",
                    "status": "error"
                }
                
        except Exception as e:
            self.logger.error(f"Query classification error: {str(e)}")
            return {
                "error": "Classification failed", 
                "status": "error"
            }
    
    def health_check(self) -> Dict:
        """Check if AI service is healthy and connected"""
        if not self.client:
            return {
                "status": "unhealthy",
                "openai_connected": False,
                "error": "OpenAI client not initialized"
            }
        
        try:
            test_messages = [{"role": "user", "content": "Test connection"}]
            result = self.chat_completion(
                messages=test_messages,
                model="gpt-3.5-turbo",
                max_tokens=10
            )
            
            return {
                "status": "healthy" if result["success"] else "unhealthy",
                "openai_connected": result["success"],
                "model_available": result["success"],
                "active_conversations": len(self.conversations),
                "available_models": list(self.available_models.keys()),
                "default_model": self.default_model,
                "error": result.get("error") if not result["success"] else None
            }
            
        except Exception as e:
            self.logger.error(f"AI service health check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "openai_connected": False,
                "error": str(e)
            }

# Singleton instance for the application
ai_service = AIService()