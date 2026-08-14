"""
Agent service entry point. Only ever called by backend/ (see docs/ARCHITECTURE.md) —
never directly by web/mobile clients.
"""

from fastapi import FastAPI

app = FastAPI(title="personal-cognitive-os agent-service")


@app.get("/health")
def health():
    return {"status": "ok"}


# TODO: mount agent_layer.orchestrator's invoke endpoint here once the
# deepagents root orchestrator is wired in (specs/agent-layer.spec.md).
