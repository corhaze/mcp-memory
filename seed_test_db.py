
import os
import sys
from pathlib import Path

# Ensure we can import mcp_memory
sys.path.append(str(Path(__file__).parent))

test_db = "/tmp/ui_test.db"
if os.path.exists(test_db):
    os.remove(test_db)
    if os.path.exists(test_db + "-wal"): os.remove(test_db + "-wal")
    if os.path.exists(test_db + "-shm"): os.remove(test_db + "-shm")

os.environ["MCP_MEMORY_DB_PATH"] = test_db

from mcp_memory.db import (
    create_project, create_task, create_decision, create_note, 
    create_global_note, add_summary, create_link, create_task_note
)

def seed():
    print(f"Creating test database at {test_db}...")
    
    # ── Project 1: Galactic Explorer ──
    p1 = create_project("galactic-explorer", "A project for exploring the final frontier.")
    add_summary(p1.id, "# Galactic Explorer\n\nCurrent mission: Map the Andromeda nebula.\n\n- Phase 1: Engine upgrades\n- Phase 2: Crew selection\n- Phase 3: Launch")
    
    t1 = create_task(p1.id, "Upgrade Warp Core", description="Increase stable warp factor to 9.9", status="in_progress", urgent=True)
    t2 = create_task(p1.id, "Select Navigator", description="Need someone with 10+ years of deep space experience.", status="open")
    t3 = create_task(p1.id, "Buy Snacks", description="Critical for long-running ops.", status="done")
    
    # Subtasks
    t1_1 = create_task(p1.id, "Cooling System", parent_task_id=t1.id, status="done")
    t1_2 = create_task(p1.id, "Dilithium Alignment", parent_task_id=t1.id, status="in_progress")
    
    # Complex task
    t_complex = create_task(p1.id, "Reconstruct Neural Network Interface", description="Extremely high complexity task involving bio-electronic integration.", complex=True)
    
    # Decision
    d1 = create_decision(p1.id, "Use HSL for UI colors", decision_text="We will use HSL to ensure accessibility.", rationale="Better contrast control.")
    
    # Note
    create_note(p1.id, "Nebula Findings", "Observed purple gases in sector 7.", "investigation")
    
    # ── Project 2: Medieval Sim ──
    p2 = create_project("medieval-sim", "Simulating 14th century life.")
    create_task(p2.id, "Build Castle", status="blocked", complex=True)
    
    # ── Global Notes ──
    create_global_note("Coding Standards", "Use PascalCase for classes.", "implementation")
    create_global_note("Security", "Always sanitize SQL inputs.", "implementation")

    print("Database seeded successfully.")

if __name__ == "__main__":
    seed()
