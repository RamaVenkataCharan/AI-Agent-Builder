import asyncio
import json
import logging
import uuid
from typing import Dict, List, Optional
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from fastapi.responses import StreamingResponse
from app.api.sse import sse_manager
from app.config import settings
from app.core.orchestrator import AgentOrchestrator
from app.llm.factory import get_llm_provider
from app.models.run_state import AgentRun, GoalSubmissionRequest, RunStatus
from app.tools.registry import default_tool_registry

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1")

# In-memory store for active and completed runs
RUNS_STORE: Dict[str, AgentRun] = {}


def _run_agent_sync(goal_req: GoalSubmissionRequest, run_id: str) -> AgentRun:
    """Synchronously executes the agent loop."""
    llm = get_llm_provider(
        provider_name=goal_req.llm_provider,
        model=goal_req.llm_model,
    )

    loop = None
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        pass

    def event_callback(event_type: str, run_state: AgentRun):
        RUNS_STORE[run_id] = run_state
        if loop and loop.is_running():
            asyncio.run_coroutine_threadsafe(
                sse_manager.broadcast(event_type, run_state),
                loop
            )

    orchestrator = AgentOrchestrator(
        llm_provider=llm,
        tool_registry=default_tool_registry,
        event_callback=event_callback,
    )

    run = orchestrator.run(
        goal=goal_req.goal,
        run_id=run_id,
        max_iterations=goal_req.max_iterations,
    )
    RUNS_STORE[run_id] = run
    return run


@router.post("/goals", response_model=AgentRun)
async def submit_goal(
    request: GoalSubmissionRequest,
    background_tasks: BackgroundTasks,
    run_async: bool = Query(False, description="Run in background asynchronously or wait for completion"),
):
    """
    Submit a natural language goal. If run_async=True, returns immediately with INITIALIZED status.
    """
    run_id = f"run_{uuid.uuid4().hex[:8]}"
    initial_run = AgentRun(
        run_id=run_id,
        goal=request.goal,
        status=RunStatus.INITIALIZED,
        max_iterations=request.max_iterations or settings.MAX_ITERATIONS,
    )
    RUNS_STORE[run_id] = initial_run

    if run_async:
        background_tasks.add_task(_run_agent_sync, request, run_id)
        return initial_run
    else:
        # Run synchronously in thread pool to avoid blocking event loop
        completed_run = await asyncio.to_thread(_run_agent_sync, request, run_id)
        return completed_run


@router.get("/runs", response_model=List[AgentRun])
async def list_runs():
    """List all agent runs."""
    return list(RUNS_STORE.values())


@router.get("/runs/{run_id}", response_model=AgentRun)
async def get_run(run_id: str):
    """Retrieve detailed state, plan, steps, and logs for a run."""
    run = RUNS_STORE.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found.")
    return run


@router.get("/runs/{run_id}/events")
async def stream_run_events(run_id: str):
    """Server-Sent Events stream for live execution updates."""
    if run_id not in RUNS_STORE:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found.")

    queue = sse_manager.subscribe(run_id)

    async def event_generator():
        try:
            # Yield initial state
            yield f"data: {json.dumps({'event': 'init', 'data': RUNS_STORE[run_id].model_dump()})}\n\n"
            while True:
                msg = await queue.get()
                yield f"data: {json.dumps(msg)}\n\n"
                if msg.get("event") == "complete" or RUNS_STORE[run_id].status in (RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.STOPPED):
                    break
        finally:
            sse_manager.unsubscribe(run_id, queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@router.get("/tools")
async def get_available_tools():
    """List all registered tools."""
    return default_tool_registry.list_tools()


@router.get("/config")
async def get_system_config():
    """Get active system configuration."""
    return {
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "llm_provider": settings.LLM_PROVIDER,
        "llm_model": settings.LLM_MODEL,
        "workspace_dir": str(settings.workspace_path),
        "max_iterations": settings.MAX_ITERATIONS,
        "max_step_retries": settings.MAX_STEP_RETRIES,
        "memory_backend": settings.MEMORY_BACKEND,
    }


@router.get("/workspace/files")
async def list_workspace_files():
    """List generated files in workspace."""
    workspace = settings.workspace_path
    files = []
    for p in workspace.rglob("*"):
        if p.is_file():
            rel_path = p.relative_to(workspace)
            files.append({
                "path": str(rel_path),
                "size_bytes": p.stat().st_size,
                "modified": p.stat().st_mtime,
            })
    return files
