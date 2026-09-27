import time
from datetime import datetime, timezone
from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn

from models import CtxBody, TickBody, ReplyBody, TickResponse, ReplyResponse
from config import BOT_CONFIG
from chains import AgenticOrchestrator

app = FastAPI(title="Vera Bot API")
START_TIME = time.time()
orchestrator = AgenticOrchestrator()

@app.get("/v1/healthz")
async def healthz():
    counts = {
        "category": len(orchestrator.context_store["category"]),
        "merchant": len(orchestrator.context_store["merchant"]),
        "customer": len(orchestrator.context_store["customer"]),
        "trigger": len(orchestrator.context_store["trigger"]),
    }
    return {
        "status": "ok",
        "uptime_seconds": int(time.time() - START_TIME),
        "contexts_loaded": counts
    }

@app.get("/v1/metadata")
async def metadata():
    return BOT_CONFIG

@app.post("/v1/context")
async def push_context(body: CtxBody):
    # Check for stale version (idempotency)
    current_payload = orchestrator.context_store[body.scope].get(body.context_id)
    # Note: In a real implementation we'd track the version number separately alongside the payload
    # For simplicity here we just accept it unless we added a version tracker
    
    orchestrator.ingest_context(body.scope, body.context_id, body.version, body.payload)
    
    return {
        "accepted": True,
        "ack_id": f"ack_{body.context_id}_v{body.version}",
        "stored_at": datetime.now(timezone.utc).isoformat()
    }

@app.post("/v1/tick", response_model=TickResponse)
async def tick(body: TickBody):
    actions = orchestrator.handle_tick(body.now, body.available_triggers)
    return {"actions": actions}

@app.post("/v1/reply", response_model=ReplyResponse)
async def reply(body: ReplyBody):
    response = orchestrator.handle_reply(
        body.conversation_id,
        body.merchant_id,
        body.customer_id,
        body.message,
        body.turn_number
    )
    return response

if __name__ == '__main__':
    uvicorn.run('main:app', host='0.0.0.0', port=8080, reload=True)
