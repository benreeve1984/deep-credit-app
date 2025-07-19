"""
FastHTML web application demonstrating queue-with-background + webhook callback pattern.

This app provides:
- A web interface for submitting long-running prompts to OpenAI
- Background processing with webhook callbacks
- Real-time status polling using HTMX
- Secure webhook verification

Endpoints:
- GET /: Main web interface
- POST /api/queue: Queue a new background task
- POST /api/webhook: Receive OpenAI webhook callbacks
- GET /api/status/<id>: Check task status and get results
"""

import asyncio
import json
import os
from typing import Dict, Any, Optional
from fasthtml.common import *
from starlette.requests import Request
from starlette.responses import JSONResponse

# Import our OpenAI client (local to this directory)
from openai_client import openai_client

# In-memory storage for task results
# In production, you'd use Redis, PostgreSQL, or another persistent store
task_storage: Dict[str, Dict[str, Any]] = {}

# Create the FastHTML app with explicit secret key to avoid filesystem writes
app, rt = fast_app(
    # Provide a secret key to prevent FastHTML from trying to write .sesskey file in serverless env
    secret_key="demo-secret-key-for-serverless-deployment",
    hdrs=[
        # Include HTMX for dynamic frontend interactions
        Script(src="https://unpkg.com/htmx.org@1.9.9"),
        # Basic styling for a clean interface
        Style("""
            body { 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                max-width: 800px; 
                margin: 0 auto; 
                padding: 20px;
                line-height: 1.6;
            }
            .container { margin: 20px 0; }
            .form-group { margin: 15px 0; }
            label { display: block; margin-bottom: 5px; font-weight: 500; }
            textarea, button { 
                width: 100%; 
                padding: 12px; 
                border: 1px solid #ddd; 
                border-radius: 6px;
                font-size: 14px;
            }
            textarea { 
                min-height: 120px; 
                resize: vertical; 
                font-family: inherit;
            }
            button { 
                background: #007bff; 
                color: white; 
                border: none; 
                cursor: pointer;
                font-weight: 500;
            }
            button:hover { background: #0056b3; }
            button:disabled { 
                background: #6c757d; 
                cursor: not-allowed; 
            }
            .status { 
                padding: 15px; 
                border: 1px solid #ddd; 
                border-radius: 6px; 
                margin: 15px 0;
                background: #f8f9fa;
            }
            .status.loading { border-color: #007bff; }
            .status.completed { border-color: #28a745; background: #d4edda; }
            .status.error { border-color: #dc3545; background: #f8d7da; }
            .result { 
                white-space: pre-wrap; 
                background: white; 
                padding: 15px; 
                border-radius: 4px;
                margin-top: 10px;
                border: 1px solid #e9ecef;
            }
            .spinner {
                display: inline-block;
                width: 16px;
                height: 16px;
                border: 2px solid #f3f3f3;
                border-top: 2px solid #007bff;
                border-radius: 50%;
                animation: spin 1s linear infinite;
                margin-right: 8px;
            }
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
        """)
    ]
)

@rt("/")
async def homepage():
    """
    Main page with form for submitting prompts and displaying results.
    
    Uses HTMX to:
    - Submit forms without page refresh
    - Poll for status updates every 2 seconds
    - Swap content dynamically based on task status
    """
    # Check if environment variables are configured
    try:
        openai_client._ensure_client()
    except ValueError as e:
        return Titled("Configuration Required",
            Div(
                H1("⚙️ Configuration Required"),
                P("Your FastHTML + OpenAI webhook demo is deployed, but needs configuration:"),
                
                Div(
                    H3("🔧 Required Environment Variables"),
                    P("Please set these in your Vercel dashboard:"),
                    Pre("""OPENAI_API_KEY=your_openai_api_key_here
OPENAI_WEBHOOK_SECRET=your_webhook_secret_here""", 
                        style="background: #f5f5f5; padding: 15px; border-radius: 5px;"),
                    
                    H3("🔗 Webhook URL"),
                    P("Configure this URL in your OpenAI dashboard:"),
                    Pre("https://deep-credit-app.vercel.app/api/webhook", 
                        style="background: #f5f5f5; padding: 15px; border-radius: 5px;"),
                    
                    P(f"Error: {str(e)}", style="color: red; font-style: italic;"),
                    
                    cls="container"
                ),
                
                cls="container"
            )
        )
    return Titled("OpenAI Background Processing Demo",
        Div(
            H1("OpenAI Background Processing Demo"),
            P("Submit a prompt below. It will be processed in the background using OpenAI's API, "
              "and you'll see real-time updates as the task completes."),
            
            # Main form for submitting prompts
            Form(
                Div(
                    Label("Enter your prompt:", For="prompt"),
                    Textarea(
                        placeholder="Ask me anything... For example: 'Write a short story about a robot learning to paint'",
                        name="prompt",
                        id="prompt",
                        required=True
                    ),
                    cls="form-group"
                ),
                
                Div(
                    Button(
                        "Queue Task",
                        type="submit",
                        id="submit-btn"
                    ),
                    cls="form-group"
                ),
                
                # HTMX attributes for form submission
                hx_post="/api/queue",
                hx_target="#status-container",
                hx_swap="innerHTML",
                # Disable the submit button during request
                hx_disabled_elt="#submit-btn"
            ),
            
            # Container where status updates will be displayed
            Div(id="status-container", cls="container"),
            
            cls="container"
        )
    )

@rt("/api/queue")
async def queue_task(request: Request):
    """Queue a new background task with OpenAI."""
    try:
        # Parse form data (HTMX sends form data, not JSON)
        form_data = await request.form()
        prompt = form_data.get("prompt", "").strip()
        
        if not prompt:
            return Div(
                P("❌ Error: Please provide a prompt"),
                cls="status error"
            )
        
        # Get the base URL for webhook callbacks
        base_url = str(request.base_url).rstrip('/')
        webhook_url = f"{base_url}/api/webhook"
        
        # Create background task with OpenAI
        response = await openai_client.create_background_response(
            prompt=prompt,
            webhook_url=webhook_url
        )
        
        task_id = response["id"]
        
        # Store initial task state in memory
        task_storage[task_id] = {
            "id": task_id,
            "prompt": prompt,
            "status": "processing",
            "output": None,
            "created_at": asyncio.get_event_loop().time(),
            "webhook_url": webhook_url
        }
        
        # For demonstration, we'll simulate the webhook callback after a short delay
        asyncio.create_task(simulate_webhook_callback(task_id, response["content"]))
        
        # Return HTMX response that starts polling for status
        return Div(
            Div(
                Span(cls="spinner"),
                f"Task queued! ID: {task_id}",
                cls="status loading"
            ),
            # HTMX polling: check status every 2 seconds
            Div(
                id="status-updates",
                hx_get=f"/api/status/{task_id}",
                hx_trigger="every 2s",
                hx_swap="outerHTML"
            )
        )
        
    except Exception as e:
        return Div(
            P(f"❌ Error: {str(e)}"),
            cls="status error"
        )

async def simulate_webhook_callback(task_id: str, content: str):
    """Simulate webhook callback after a delay."""
    await asyncio.sleep(4)
    
    if task_id in task_storage:
        task_storage[task_id].update({
            "status": "completed",
            "output": content,
            "completed_at": asyncio.get_event_loop().time()
        })

@rt("/api/webhook")
async def webhook_callback(request: Request):
    """Receive webhook callbacks from OpenAI when background tasks complete."""
    try:
        body = await request.body()
        signature = request.headers.get("X-OpenAI-Signature", "")
        
        if not openai_client.verify_webhook_signature(body, signature):
            return JSONResponse(
                {"error": "Invalid webhook signature"}, 
                status_code=401
            )
        
        payload = openai_client.parse_webhook_payload(body)
        if not payload:
            return JSONResponse(
                {"error": "Invalid payload format"}, 
                status_code=400
            )
        
        task_id = payload.get("id")
        event_type = payload.get("type", "")
        
        if not task_id or task_id not in task_storage:
            return JSONResponse(
                {"error": "Task not found"}, 
                status_code=404
            )
        
        if event_type == "response.completed":
            output_text = payload.get("output", {}).get("text", "")
            task_storage[task_id].update({
                "status": "completed",
                "output": output_text,
                "completed_at": asyncio.get_event_loop().time()
            })
            
        elif event_type == "response.failed":
            error_message = payload.get("error", {}).get("message", "Unknown error")
            task_storage[task_id].update({
                "status": "failed",
                "error": error_message,
                "completed_at": asyncio.get_event_loop().time()
            })
        
        return JSONResponse({"status": "received"})
        
    except Exception as e:
        return JSONResponse(
            {"error": f"Webhook processing failed: {str(e)}"}, 
            status_code=500
        )

@rt("/api/status/{task_id}")
async def get_task_status(task_id: str):
    """Get the current status of a background task."""
    task = task_storage.get(task_id)
    
    if not task:
        return Div(
            P("❌ Task not found"),
            cls="status error",
            id="status-updates"
        )
    
    status = task["status"]
    
    if status == "processing":
        return Div(
            Div(
                Span(cls="spinner"),
                f"Processing... (Task ID: {task_id})",
                cls="status loading"
            ),
            id="status-updates",
            hx_get=f"/api/status/{task_id}",
            hx_trigger="every 2s",
            hx_swap="outerHTML"
        )
    
    elif status == "completed":
        return Div(
            Div(
                P("✅ Task completed successfully!"),
                Div(
                    Strong("Result:"),
                    Div(task["output"], cls="result")
                ),
                cls="status completed"
            ),
            id="status-updates"
        )
    
    elif status == "failed":
        error_msg = task.get("error", "Unknown error occurred")
        return Div(
            Div(
                P("❌ Task failed"),
                P(f"Error: {error_msg}"),
                cls="status error"
            ),
            id="status-updates"
        )
    
    else:
        return Div(
            P(f"❓ Unknown status: {status}"),
            cls="status error",
            id="status-updates"
        )

@rt("/health")
async def health_check():
    """Simple health check endpoint."""
    return JSONResponse({"status": "healthy", "service": "openai-webhook-demo"})

# Export for Vercel
app_for_vercel = app 