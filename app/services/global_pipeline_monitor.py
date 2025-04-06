import asyncio
from typing import Dict, Any, List, Optional, Set
import time
import json
import tiktoken

class GlobalPipelineMonitor:
    """
    A singleton service that monitors all RAG pipeline executions and broadcasts events to all connected clients.
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GlobalPipelineMonitor, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self.active_clients: Set[asyncio.Queue] = set()
        self.encoding = tiktoken.get_encoding("cl100k_base")
        self._initialized = True
        
    async def register_client(self) -> asyncio.Queue:
        """Register a new client and return a queue for receiving events."""
        queue = asyncio.Queue()
        self.active_clients.add(queue)
        return queue
        
    async def unregister_client(self, queue: asyncio.Queue):
        """Unregister a client when they disconnect."""
        if queue in self.active_clients:
            self.active_clients.remove(queue)
            
    async def broadcast_event(self, event_name: str, data: Dict[str, Any]):
        """Broadcast an event to all connected clients."""
        if not self.active_clients:
            return
            
        for queue in self.active_clients:
            await queue.put((event_name, data))
            
    async def new_query(self, query: str, pipeline_type: str, user_id: Optional[str] = None):
        """Notify all clients of a new query being processed."""
        await self.broadcast_event("new_query", {
            "query": query,
            "pipeline_type": pipeline_type,
            "user_id": user_id or "anonymous",
            "timestamp": time.time()
        })
        
    async def start_embedding(self):
        """Notify clients that embedding generation has started."""
        await self.broadcast_event("embedding_start", {
            "timestamp": time.time()
        })
        
    async def complete_embedding(self, vector_size: int, time_ms: float):
        """Notify clients that embedding generation is complete."""
        await self.broadcast_event("embedding_complete", {
            "timestamp": time.time(),
            "vector_size": vector_size,
            "time_ms": time_ms
        })
        
    async def start_search(self):
        """Notify clients that vector search has started."""
        await self.broadcast_event("search_start", {
            "timestamp": time.time()
        })
        
    async def complete_search(self, results_count: int, time_ms: float):
        """Notify clients that vector search is complete."""
        await self.broadcast_event("search_complete", {
            "timestamp": time.time(),
            "results_count": results_count,
            "time_ms": time_ms
        })
        
    async def start_context_building(self):
        """Notify clients that context building has started."""
        await self.broadcast_event("context_start", {
            "timestamp": time.time()
        })
        
    async def complete_context_building(self, context_text: str, time_ms: float):
        """Notify clients that context building is complete."""
        token_count = len(self.encoding.encode(context_text))
        
        await self.broadcast_event("context_complete", {
            "timestamp": time.time(),
            "token_count": token_count,
            "character_count": len(context_text),
            "time_ms": time_ms
        })
        
    async def start_llm_generation(self):
        """Notify clients that LLM generation has started."""
        await self.broadcast_event("llm_start", {
            "timestamp": time.time()
        })
        
    async def complete_llm_generation(self, answer: str, time_ms: float):
        """Notify clients that LLM generation is complete."""
        token_count = len(self.encoding.encode(answer))
        
        await self.broadcast_event("llm_complete", {
            "timestamp": time.time(),
            "token_count": token_count,
            "character_count": len(answer),
            "time_ms": time_ms
        })
        
    async def complete_pipeline(self, answer: str, total_time_ms: float, stage_metrics: Dict[str, float] = None, query_info: Dict[str, Any] = None):
        """Notify clients that the entire pipeline is complete with detailed metrics."""
        # Create the event data with all metrics
        event_data = {
            "timestamp": time.time(),
            "total_time_ms": total_time_ms,
            "answer": answer
        }
        
        # Add stage metrics if provided
        if stage_metrics:
            for key, value in stage_metrics.items():
                event_data[f"{key}_time_ms"] = value
        
        # Include original query info for reference
        if query_info:
            event_data.update(query_info)
        
        await self.broadcast_event("complete", event_data)
        
    async def report_error(self, error_message: str):
        """Notify clients of an error in the pipeline."""
        await self.broadcast_event("error_occurred", {
            "timestamp": time.time(),
            "error": error_message
        })