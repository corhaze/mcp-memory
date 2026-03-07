from mcp_memory.db import create_project, create_task, update_task
p = create_project("Test Bug Project", "Testing")
t = create_task(p.id, "Test Bug Task")
try:
    update_task(t.id, status="done")
    print("Success")
except Exception as e:
    import traceback
    traceback.print_exc()
