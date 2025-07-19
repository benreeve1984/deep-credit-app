"""
OpenAI client wrapper with webhook verification support.

This module provides:
- Async OpenAI client setup with environment variable configuration
- Webhook signature verification for secure callback handling
- Response creation with background processing support
"""

import os
import json
import hmac
import hashlib
from typing import Dict, Any, Optional
from openai import AsyncOpenAI
from dotenv import load_dotenv

# Load environment variables from .env file (for local development)
load_dotenv()


class OpenAIClient:
    """
    Wrapper around OpenAI AsyncOpenAI client with webhook verification.
    
    This class handles:
    - Setting up the OpenAI client with API key from environment
    - Creating background responses that will trigger webhooks
    - Verifying webhook signatures for security
    """
    
    def __init__(self):
        """Initialize the OpenAI client with API key from environment."""
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.webhook_secret = os.getenv("OPENAI_WEBHOOK_SECRET")
        
        # Initialize client lazily to avoid startup errors
        self.client = None
    
    def _ensure_client(self):
        """Ensure the OpenAI client is initialized."""
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        if not self.webhook_secret:
            raise ValueError("OPENAI_WEBHOOK_SECRET environment variable is required")
        
        if self.client is None:
            self.client = AsyncOpenAI(api_key=self.api_key)
    
    async def create_background_response(
        self, 
        prompt: str, 
        webhook_url: str,
        model: str = "o3"
    ) -> Dict[str, Any]:
        """
        Create a response with background processing enabled.
        
        This initiates a long-running task that will complete asynchronously
        and send results to the specified webhook URL.
        
        Args:
            prompt: The user's prompt to process
            webhook_url: URL where completion results will be sent
            model: OpenAI model to use (defaults to gpt-4)
            
        Returns:
            Dictionary containing the response ID and status
        """
        try:
            # Ensure client is initialized
            self._ensure_client()
            
            # Create a completion request with background processing
            # Note: This is a simulated approach since OpenAI doesn't have a direct "background" API
            # In practice, you might use their Assistants API or handle long requests differently
            response = await self.client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system", 
                        "content": "You are a helpful assistant that provides detailed, thoughtful responses."
                    },
                    {"role": "user", "content": prompt}
                ],
                # For now, we'll use standard completion and simulate background processing
                # In a real implementation, you'd use OpenAI's background processing features
            )
            
            # Extract the response content
            content = response.choices[0].message.content
            
            # Generate a unique ID for this response
            response_id = f"resp_{hash(prompt + webhook_url) % 1000000}"
            
            return {
                "id": response_id,
                "status": "queued",
                "content": content,  # In real implementation, this would be None initially
                "model": model
            }
            
        except Exception as e:
            raise Exception(f"Failed to create background response: {str(e)}")
    
    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """
        Verify that a webhook request came from OpenAI by checking the signature.
        
        OpenAI signs webhook payloads with HMAC-SHA256 using your webhook secret.
        This prevents malicious actors from sending fake webhook requests.
        
        Args:
            payload: Raw request body as bytes
            signature: The X-OpenAI-Signature header value
            
        Returns:
            True if signature is valid, False otherwise
        """
        if not signature or not payload:
            return False
            
        try:
            # Extract the signature from the header (format: "sha256=<signature>")
            if not signature.startswith("sha256="):
                return False
            
            provided_signature = signature[7:]  # Remove "sha256=" prefix
            
            # Calculate the expected signature using our webhook secret
            expected_signature = hmac.new(
                self.webhook_secret.encode('utf-8'),
                payload,
                hashlib.sha256
            ).hexdigest()
            
            # Use constant-time comparison to prevent timing attacks
            return hmac.compare_digest(provided_signature, expected_signature)
            
        except Exception:
            return False
    
    def parse_webhook_payload(self, payload: bytes) -> Optional[Dict[str, Any]]:
        """
        Parse and validate a webhook payload from OpenAI.
        
        Args:
            payload: Raw request body as bytes
            
        Returns:
            Parsed payload as dictionary, or None if invalid
        """
        try:
            return json.loads(payload.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None


# Global client instance - initialized when module is imported
openai_client = OpenAIClient() 