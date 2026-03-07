---
description: common development tasks for mcp-memory
---

1. **Environment Setup**
   - Ensure you are using the project's virtual environment: `./.venv/bin/python`.
   - Install local editable version: `./.venv/bin/pip install -e .`.

2. **Core Discovery**
   - Always call `get_context(project="mcp-memory", category="orientation", key="GET_STARTED")` first.
   - Use `semantic_search_insights` to find related patterns and architecture decisions.

3. **Database Changes**
   - When modifying the schema, update `_init_schema` in `mcp_memory/db.py`.
   - If adding new content tables, remember to add corresponding `*_fts` and `*_embeddings` tables.

4. **Testing**
   - Run all tests: `./.venv/bin/python -m pytest tests/`.
   - Add new tests for any logic changes in `tests/`.

5. **Semantic Search Maintenance**
   - Any tool that updates `contexts`, `insights`, or `todos` MUST also update the corresponding embedding table using `_emb.generate_embedding()`.
