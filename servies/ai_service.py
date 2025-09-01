"""
Core AI Service - Handles all AI model interactions and configurations
Designed for easy migration from OpenAI direct to Azure AI Fleet
"""

import openai
import os
import yaml
from typing import Dict, List, Optional
from utils.logger import get_api_logger

class AIService:
    def __init__(self):
        self.logger = get_api_logger()
        self._setup_api_key()
        
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

If asked about specific data you don't have access to, explain that you need to query the Salesforce database and ask for clarification on search parameters.""",

            "query_classification": """Classify this check validation query into one of these categories:

SQL_QUERY: Factual questions that need database lookups (specific amounts, dates, payee names, counts, etc.)
VECTOR_SEARCH: Interpretive questions needing guidance (how to handle situations, compliance advice, general patterns)

Query: "{query}"

Respond with just: SQL_QUERY or VECTOR_SEARCH"""
        }
    
    def _setup_api_key(self):
        """Setup OpenAI API key from credentials file or environment"""
        try:
            if os.path.exists('credentials.yml'):
                with open('credentials.yml', 'r') as f:
                    credentials = yaml.safe_load(f)
                    openai.api_key = credentials.get('openai')
                    self.logger.info("OpenAI API key loaded from credentials.yml")
            else:
                openai.api_key = os.getenv('OPENAI_API_KEY')
                self.logger.info("OpenAI API key loaded from environment")
                
            if not openai.api_key:
                self.logger.warning("No OpenAI API key found")
                
        except Exception as e:
            self.logger.error(f"Failed to setup OpenAI API key: {str(e)}")
    
    def chat_completion(self, 
                       messages: List[Dict[str, str]], 
                       model: str = "gpt-4",
                       max_tokens: int = 1000,
                       temperature: float = 0.7) -> Dict:
        """
        Generate chat completion with error handling
        Future: This method will route to Azure AI Fleet based on model selection
        """
        try:
            response = openai.ChatCompletion.create(
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
                "tokens_used": response.usage.total_tokens
            }
            
        except Exception as e:
            self.logger.error(f"Chat completion error: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "content": None
            }
    
    def validate_check_query(self, user_message: str, user_context: Optional[Dict] = None) -> Dict:
        """Handle check validation conversations"""
        try:
            # Prepare conversation context
            messages = [
                {"role": "system", "content": self.prompts["check_validation"]},
                {"role": "user", "content": user_message}
            ]
            
            # Add user context if available
            if user_context:
                user_info = f"User: {user_context.get('name', 'Unknown')}"
                messages[0]["content"] += f"\n\nCurrent user context: {user_info}"
            
            result = self.chat_completion(messages)
            
            if result["success"]:
                self.logger.info(f"Check validation query processed successfully")
                return {
                    "response": result["content"],
                    "status": "success",
                    "tokens_used": result.get("tokens_used", 0)
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
    
    def classify_query(self, query: str) -> Dict:
        """
        Classify if query needs SQL database lookup or vector search
        This will be used by query_classifier.py service
        """
        try:
            classification_prompt = self.prompts["query_classification"].format(query=query)
            
            messages = [{"role": "user", "content": classification_prompt}]
            
            result = self.chat_completion(
                messages=messages,
                model="gpt-3.5-turbo",
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