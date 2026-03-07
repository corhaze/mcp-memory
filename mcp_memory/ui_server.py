from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import mcp_memory.db as db
from typing import List, Optional
import os

app = FastAPI(title="MCP Memory Explorer")

@app.get("/api/projects")
async def get_projects():
    return db.list_all_projects()

@app.get("/api/project/{project_name}/context")
async def get_project_context(project_name: str):
    entries = db.list_contexts(project_name)
    return [{"id": e.id, "category": e.category, "key": e.key, "value": e.value, "tags": e.tags, "updated": e.updated} for e in entries]

@app.get("/api/project/{project_name}/timeline")
async def get_project_timeline(project_name: str, limit: int = 50):
    events = db.get_timeline(project_name, limit)
    return [{"id": e.id, "event_type": e.event_type, "summary": e.summary, "detail": e.detail, "timestamp": e.timestamp} for e in events]

@app.get("/api/project/{project_name}/todos")
async def get_project_todos(project_name: str):
    todos = db.list_todos(project_name)
    return [{"id": t.id, "title": t.title, "description": t.description, "status": t.status, "priority": t.priority, "updated": t.updated} for t in todos]

@app.delete("/api/project/{project_name}")
async def delete_project(project_name: str):
    db.delete_project(project_name)
    return {"message": f"Project {project_name} deleted successfully."}

@app.get("/api/insights")
async def get_insights(scope: Optional[str] = "global"):
    insights = db.list_insights(scope=scope)
    return [{"id": i.id, "scope": i.scope, "title": i.title, "body": i.body, "tags": i.tags, "updated": i.updated} for i in insights]

UI_DIR = os.path.join(os.path.dirname(__file__), "ui")
if not os.path.exists(UI_DIR):
    os.makedirs(UI_DIR)

@app.get("/")
async def read_index():
    index_path = os.path.join(UI_DIR, "index.html")
    if not os.path.exists(index_path):
        return {"message": "UI not built yet."}
    return FileResponse(index_path)

if os.path.exists(UI_DIR):
    app.mount("/", StaticFiles(directory=UI_DIR), name="ui")
