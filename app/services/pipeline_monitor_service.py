import time
import asyncio
from typing import Dict, List, Any, Optional, Callable
from fastapi import BackgroundTasks
from app.core.logging import logger
import tiktoken

class PipelineMonitorService:
    """
    Service to monitor the RAG pipeline execution and report progress via Server-Sent Events (SSE).
    This class tracks timing metrics and emits events for each stage of the pipeline.
    """

    def __init__(self, callback: Callable[[str, Dict[str, Any]], None]):
        """
        Initialize the pipeline monitor service.
        
        Args:
            callback: Function to call with event name and data for each pipeline stage
        """
        self.callback = callback
        self.start_time = None
        self.stage_times = {}
        self.active = False
        self.pipeline_type = None
        self.encoding = tiktoken.get_encoding("cl100k_base")  # OpenAI's encoding for token counting

    async def start_pipeline(self, query: str, pipeline_type: str):
        """Start monitoring a new pipeline execution."""
        self.active = True
        self.start_time = time.time()
        self.stage_times = {
            "embedding": {"start": None, "end": None},
            "search": {"start": None, "end": None},
            "context": {"start": None, "end": None},
            "llm": {"start": None, "end": None}
        }
        self.pipeline_type = pipeline_type
        
        # Emit start event
        await self._emit_event("start", {
            "query": query,
            "pipeline_type": pipeline_type,
            "timestamp": self.start_time
        })

    async def start_embedding(self):
        """Track start of embedding generation."""
        if not self.active:
            return
            
        self.stage_times["embedding"]["start"] = time.time()
        await self._emit_event("embedding_start", {
            "timestamp": self.stage_times["embedding"]["start"]
        })

    async def complete_embedding(self, vector_size: int):
        """Track completion of embedding generation."""
        if not self.active or self.stage_times["embedding"]["start"] is None:
            return
            
        self.stage_times["embedding"]["end"] = time.time()
        time_ms = (self.stage_times["embedding"]["end"] - self.stage_times["embedding"]["start"]) * 1000
        
        await self._emit_event("embedding_complete", {
            "timestamp": self.stage_times["embedding"]["end"],
            "time_ms": time_ms,
            "vector_size": vector_size
        })

    async def start_search(self):
        """Track start of vector search."""
        if not self.active:
            return
            
        self.stage_times["search"]["start"] = time.time()
        await self._emit_event("search_start", {
            "timestamp": self.stage_times["search"]["start"]
        })

    async def complete_search(self, results_count: int):
        """Track completion of vector search."""
        if not self.active or self.stage_times["search"]["start"] is None:
            return
            
        self.stage_times["search"]["end"] = time.time()
        time_ms = (self.stage_times["search"]["end"] - self.stage_times["search"]["start"]) * 1000
        
        await self._emit_event("search_complete", {
            "timestamp": self.stage_times["search"]["end"],
            "time_ms": time_ms,
            "results_count": results_count
        })

    async def start_context_building(self):
        """Track start of context building."""
        if not self.active:
            return
            
        self.stage_times["context"]["start"] = time.time()
        await self._emit_event("context_start", {
            "timestamp": self.stage_times["context"]["start"]
        })

    async def complete_context_building(self, context_text: str):
        """Track completion of context building."""
        if not self.active or self.stage_times["context"]["start"] is None:
            return
            
        self.stage_times["context"]["end"] = time.time()
        time_ms = (self.stage_times["context"]["end"] - self.stage_times["context"]["start"]) * 1000
        
        # Count tokens in context
        token_count = len(self.encoding.encode(context_text))
        
        await self._emit_event("context_complete", {
            "timestamp": self.stage_times["context"]["end"],
            "time_ms": time_ms,
            "token_count": token_count,
            "character_count": len(context_text)
        })

    async def start_llm_generation(self):
        """Track start of LLM generation."""
        if not self.active:
            return
            
        self.stage_times["llm"]["start"] = time.time()
        await self._emit_event("llm_start", {
            "timestamp": self.stage_times["llm"]["start"]
        })

    async def complete_llm_generation(self, answer: str):
        """Track completion of LLM generation."""
        if not self.active or self.stage_times["llm"]["start"] is None:
            return
            
        self.stage_times["llm"]["end"] = time.time()
        time_ms = (self.stage_times["llm"]["end"] - self.stage_times["llm"]["start"]) * 1000
        
        # Count tokens in answer
        token_count = len(self.encoding.encode(answer))
        
        await self._emit_event("llm_complete", {
            "timestamp": self.stage_times["llm"]["end"],
            "time_ms": time_ms,
            "token_count": token_count,
            "character_count": len(answer)
        })

    async def complete_pipeline(self, answer: str):
        """Track overall pipeline completion."""
        if not self.active:
            return
            
        end_time = time.time()
        total_time_ms = (end_time - self.start_time) * 1000
        
        # Calculate metrics
        metrics = {
            "total_time_ms": total_time_ms,
            "answer": answer
        }
        
        for stage, times in self.stage_times.items():
            if times["start"] and times["end"]:
                metrics[f"{stage}_time_ms"] = (times["end"] - times["start"]) * 1000
        
        await self._emit_event("complete", metrics)
        self.active = False

    async def report_error(self, error_message: str):
        """Report an error in the pipeline."""
        await self._emit_event("error_occurred", {
            "timestamp": time.time(),
            "error": error_message
        })
        self.active = False

    async def _emit_event(self, event_name: str, data: Dict[str, Any]):
        """Emit an event with the given name and data."""
        if self.callback:
            await self.callback(event_name, data)