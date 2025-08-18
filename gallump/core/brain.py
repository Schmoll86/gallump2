"""
Brain Module - Handles ALL Claude/Anthropic AI interactions
Single responsibility: Manage AI conversation and strategy generation
"""

import os
import json
import logging
import re
from datetime import datetime
from typing import Dict, List, Optional
from anthropic import Anthropic
from dotenv import load_dotenv

# Import context from context_builder and types
from gallump.core.context_builder import Context
from gallump.core.types import SessionContext

logger = logging.getLogger(__name__)
load_dotenv()


class Brain:
    """
    Manages all AI/trading conversation for Gallump
    ONLY handles Claude interaction - context building is delegated
    """
    
    def __init__(self, session_id: Optional[str] = None, session_manager=None):
        """Initialize Brain with Anthropic client and optional session"""
        api_key = os.getenv('ANTHROPIC_API_KEY')
        self.client = Anthropic(api_key=api_key) if api_key else None
        self.session_id = session_id
        self.session_manager = session_manager
        # Note: memories removed - now handled by SessionManager
        
        if not api_key:
            logger.warning("ANTHROPIC_API_KEY not found in environment")
    
    # Note: remember() and recall() methods removed - now handled by SessionManager
    # Session context is passed in via converse() method
    
    def converse(self, user_message: str, market_context: Context, 
                 session_context: Optional[SessionContext] = None) -> Dict:
        """
        Main conversational endpoint - processes user message with market and session context
        
        Args:
            user_message: User's trading thesis or question
            market_context: Complete Context object from ContextBuilder
            session_context: Optional SessionContext with conversation history
            
        Returns:
            Dict with 'response' (text) and 'recommendations' (list of strategies)
        """
        # Use PromptBuilder to construct the prompt (single responsibility)
        from gallump.core.prompt_builder import PromptBuilder
        prompt_builder = PromptBuilder()
        
        # Build prompt with both market and session context
        prompt = prompt_builder.build_trading_prompt(
            user_message=user_message,
            market_context=market_context,
            session_context=session_context
        )
        
        # Get Claude's response
        response = self._call_claude(prompt)
        
        # Parse any trading recommendations from the response
        recommendations = self._parse_recommendations(response)
        
        # Log the interaction
        self._log('conversation_turn', {
            'user_message': user_message,
            'symbol': market_context.symbol,
            'response_length': len(response),
            'recommendations_count': len(recommendations),
            'session_id': self.session_id
        })
        
        return {
            'response': response,  # Full text response for UI
            'recommendations': recommendations  # Parsed trading strategies
        }
    
    
    def _call_claude(self, prompt: str) -> str:
        """
        Call Claude API with prompt
        
        Args:
            prompt: The formatted prompt
            
        Returns:
            Claude's response text
        """
        if not self.client:
            return "Error: Claude API not configured. Please set ANTHROPIC_API_KEY."
        
        try:
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",  # Latest available model
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2500
            )
            return response.content[0].text
            
        except Exception as e:
            logger.error(f"Claude API call failed: {e}")
            return f"I apologize, but I encountered an error processing your request: {str(e)}"
    
    def _parse_recommendations(self, response: str) -> List[Dict]:
        """
        Extract structured trading recommendations from Claude's response
        
        Args:
            response: Claude's full text response
            
        Returns:
            List of parsed strategy dictionaries
        """
        try:
            # Find JSON array by looking for balanced brackets
            # Start from the first '[' and find its matching ']'
            start = response.find('[')
            if start == -1:
                return []
            
            # Track bracket depth to find matching closing bracket
            depth = 0
            end = -1
            in_string = False
            escape_next = False
            
            for i in range(start, len(response)):
                char = response[i]
                
                # Handle string literals
                if not escape_next:
                    if char == '"' and not in_string:
                        in_string = True
                    elif char == '"' and in_string:
                        in_string = False
                    elif char == '\\' and in_string:
                        escape_next = True
                        continue
                        
                    # Track brackets when not in string
                    if not in_string:
                        if char == '[':
                            depth += 1
                        elif char == ']':
                            depth -= 1
                            if depth == 0:
                                end = i + 1
                                break
                else:
                    escape_next = False
            
            if end == -1:
                logger.debug("No complete JSON array found")
                return []
            
            # Extract the JSON string
            json_str = response[start:end]
            
            # Clean up common issues
            # Remove JavaScript-style comments
            json_str = re.sub(r'//.*?(?=\n|$)', '', json_str)  # Remove // comments
            json_str = re.sub(r'/\*.*?\*/', '', json_str, flags=re.DOTALL)  # Remove /* */ comments
            # Remove any non-numeric max_loss/max_gain fields
            json_str = re.sub(r'"max_loss":\s*"[^"]*",?\s*', '', json_str)
            json_str = re.sub(r'"max_gain":\s*"[^"]*",?\s*', '', json_str)
            # Fix trailing commas
            json_str = re.sub(r',\s*}', '}', json_str)
            json_str = re.sub(r',\s*]', ']', json_str)
            
            # Parse the cleaned JSON
            strategies = json.loads(json_str)
            
            # Validate each strategy has required fields
            validated = []
            for strategy in strategies:
                if self._validate_strategy(strategy):
                    validated.append(strategy)
                else:
                    logger.warning(f"Invalid strategy format: {strategy}")
            
            logger.info(f"Successfully parsed {len(validated)} strategies")
            return validated
            
        except (json.JSONDecodeError, Exception) as e:
            logger.error(f"Failed to parse strategies: {e}")
            logger.debug(f"Response was: {response[:500]}")
            return []
    
    def parse_annotations(self, response: str, user_message: str, symbol: Optional[str] = None) -> List[Dict]:
        """
        Extract annotation requests from Claude's response.
        Looks for patterns like "save this mistake", "remember this", etc.
        
        Args:
            response: Claude's response text
            user_message: Original user message
            symbol: Current symbol context
            
        Returns:
            List of annotations to save
        """
        annotations = []
        
        # Pattern matching for different annotation types
        patterns = {
            'mistake': r'(?:save|remember|note).*?mistake[s]?:?\s*(.+?)(?:\.|$)',
            'insight': r'(?:save|remember|note).*?insight[s]?:?\s*(.+?)(?:\.|$)',
            'strategy_liked': r'(?:liked|good|successful).*?strategy:?\s*(.+?)(?:\.|$)',
            'lesson': r'(?:lesson learned|learned):?\s*(.+?)(?:\.|$)',
            'warning': r'(?:warning|caution|careful):?\s*(.+?)(?:\.|$)'
        }
        
        for note_type, pattern in patterns.items():
            matches = re.findall(pattern, response, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                annotations.append({
                    'type': note_type,
                    'text': match.strip(),
                    'related_symbol': symbol,
                    'author': 'claude'
                })
        
        # Check if user explicitly asked to save something
        if any(phrase in user_message.lower() for phrase in ['save this', 'remember this', 'note this']):
            annotations.append({
                'type': 'observation',
                'text': f"User request: {user_message}\nClaude response: {response[:500]}",
                'related_symbol': symbol,
                'author': 'user'
            })
        
        return annotations
    
    def _validate_strategy(self, strategy: Dict) -> bool:
        """
        Validate strategy has required fields
        
        Args:
            strategy: Strategy dictionary to validate
            
        Returns:
            True if valid, False otherwise
        """
        required_fields = ['name', 'orders']
        if not all(field in strategy for field in required_fields):
            return False
        
        # Validate each order
        for order in strategy.get('orders', []):
            order_fields = ['symbol', 'action', 'quantity']
            if not all(field in order for field in order_fields):
                return False
        
        return True
    
    def _log(self, tag: str, data: Dict):
        """
        Log interaction data
        
        Args:
            tag: Log tag/category
            data: Data to log
        """
        entry = {
            'timestamp': datetime.now().isoformat(),
            'tag': tag,
            'data': data
        }
        logger.info(json.dumps(entry))