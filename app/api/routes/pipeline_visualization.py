from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sse_starlette.sse import EventSourceResponse
import json
import asyncio
import os
import time
from app.services.global_pipeline_monitor import GlobalPipelineMonitor
from app.core.logging import logger

router = APIRouter()

# Configure templates directory
templates_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "templates")
templates = Jinja2Templates(directory=templates_path)

@router.get("/visualizer", response_class=HTMLResponse)
async def get_visualizer_page(request: Request):
    """Render the pipeline visualizer HTML page."""
    return templates.TemplateResponse("pipeline-visualizer.html", {"request": request})

@router.get("/pipeline/monitor")
async def monitor_pipeline(request: Request):
    """
    Stream all pipeline execution events using Server-Sent Events (SSE).
    This endpoint allows clients to monitor all pipeline executions in real-time.
    """
    # Get the global pipeline monitor
    monitor = GlobalPipelineMonitor()
    
    # Register this client
    client_queue = await monitor.register_client()
    
    # Define the event generator
    async def event_generator():
        try:
            # Send an initial ping event
            yield {
                "event": "ping",
                "data": json.dumps({"timestamp": time.time()})
            }
            
            # Stream events from the queue
            while True:
                try:
                    # Wait for an event with timeout
                    event_name, data = await asyncio.wait_for(client_queue.get(), timeout=30.0)
                    
                    # Convert data to JSON string
                    json_data = json.dumps(data)
                    
                    # Yield the event
                    yield {
                        "event": event_name,
                        "data": json_data
                    }
                    
                except asyncio.TimeoutError:
                    # Send a ping event to keep the connection alive
                    yield {
                        "event": "ping",
                        "data": json.dumps({"timestamp": time.time()})
                    }
        
        except asyncio.CancelledError:
            # Handle client disconnection
            logger.info("Client disconnected from pipeline monitor")
            
        finally:
            # Unregister the client
            await monitor.unregister_client(client_queue)
    
    # Return the EventSourceResponse
    return EventSourceResponse(event_generator())