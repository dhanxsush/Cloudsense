"""
CloudSense Chatbot Module
AI-powered assistant for meteorology questions using Groq LLM.
"""

import os
import logging
from typing import Optional, List, Dict
from groq import Groq

logger = logging.getLogger(__name__)

# Groq API configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL_NAME = "llama-3.3-70b-versatile"

# System prompt for meteorology context - TOPIC RESTRICTED
SYSTEM_PROMPT = """You are CloudSense AI, an expert meteorology assistant. 

⚠️ IMPORTANT: You ONLY answer questions about:
- Tropical Cloud Clusters (TCCs) and convective systems
- Satellite data and remote sensing (INSAT-3D, IR imagery, brightness temperature)
- Weather patterns, cyclones, monsoons, severe weather
- Meteorology, atmospheric science, climate
- CloudSense platform features and data interpretation

🚫 For ANY off-topic questions (coding help, general knowledge, jokes, personal questions, 
other topics), respond ONLY with:
"I'm CloudSense AI, specialized in meteorology and satellite data analysis. I can only help with weather-related questions. Please ask me about tropical cloud clusters, satellite imagery, or weather patterns!"

When answering ON-TOPIC questions:
- Be concise and scientifically accurate
- Reference relevant meteorological concepts
- Explain CloudSense metrics (BT, area, centroid, cloud-top height)
- Provide clear explanations suitable for researchers

CloudSense metrics you can explain:
- Brightness Temperature (BT): Lower = colder, higher cloud tops (strong convection)
- Cluster Area: Size in km² (TCC minimum is 34,800 km²)
- Cloud-top Height: Estimated from BT using tropical lapse rate
- Kalman Tracking: Predicting TCC movement using velocity estimation
"""


class CloudSenseChatbot:
    """Groq-powered chatbot for meteorology assistance."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize chatbot with Groq client."""
        self.api_key = api_key or GROQ_API_KEY
        self.client = Groq(api_key=self.api_key)
        self.conversation_history: List[Dict] = []
        logger.info("CloudSense Chatbot initialized")
    
    def chat(self, message: str, include_context: Optional[str] = None) -> str:
        """
        Send message to chatbot and get response.
        
        Args:
            message: User's message
            include_context: Optional analysis context to include
            
        Returns:
            AI response text
        """
        # Build messages
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        
        # Add conversation history (last 10 messages for context)
        messages.extend(self.conversation_history[-10:])
        
        # Add context if provided
        if include_context:
            messages.append({
                "role": "system",
                "content": f"Current analysis context:\n{include_context}"
            })
        
        # Add user message
        messages.append({"role": "user", "content": message})
        
        try:
            response = self.client.chat.completions.create(
                model=MODEL_NAME,
                messages=messages,
                temperature=0.7,
                max_tokens=1024,
            )
            
            assistant_message = response.choices[0].message.content
            
            # Store in history
            self.conversation_history.append({"role": "user", "content": message})
            self.conversation_history.append({"role": "assistant", "content": assistant_message})
            
            return assistant_message
            
        except Exception as e:
            logger.error(f"Chatbot error: {e}")
            return f"I apologize, but I encountered an error: {str(e)}"
    
    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history.clear()
    
    def get_analysis_summary(self, analysis_data: Dict) -> str:
        """
        Generate natural language summary of analysis results.
        
        Args:
            analysis_data: Dictionary with cluster/trajectory data
            
        Returns:
            Human-readable summary
        """
        prompt = f"""Based on this TCC analysis data, provide a brief summary:

Data: {analysis_data}

Include:
1. Number of clusters detected
2. Key characteristics (size, intensity)
3. Movement patterns if trajectory data exists
4. Any severe weather indicators

Keep it concise (2-3 paragraphs max)."""

        return self.chat(prompt)


# Singleton instance
chatbot = CloudSenseChatbot()
