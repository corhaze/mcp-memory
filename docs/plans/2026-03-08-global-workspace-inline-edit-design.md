# Global Workspace + Reusable Inline Edit Pattern

## Goal

Move global notes from a sidebar list with modal editing into a dedicated top-level "Global Workspace" view with accordion-style inline expand-in-place editing. Build the inline edit as a generic reusable component (`EntityDetailPanel`) that can replace modal editing for all entity types.

## Routing

- New namespace: `/global/{tab}` alongside existing `/{project_name}/{tab}`
- `parsePath()` returns `{ namespace: 'global'|'project', ... }`
- Only tab for now: `notes`. Tab bar present for future expansion.

## Views

### Sidebar
- Replace global notes list + delete buttons with a single "Global Workspace" nav button
- Clicking navigates to `/global/notes`
- `+` button moves to the main panel toolbar

### Global Workspace (`#global-view`)
- Project-like layout: header, tab bar, panel
- Header: "Global Workspace" title, subtitle "Cross-project notes and standards"
- Tab bar: just "Notes" for now
- Panel: toolbar with type filters + add button, entity list below

### Notes list
- Each note renders as a list item with type pill and title
- Clicking toggles accordion expand/collapse (like tasks)
- Expanded: read-only detail with markdown rendering, Edit and Delete buttons
- Edit mode: inline form with Save/Cancel, rendered by `EntityDetailPanel`

## EntityDetailPanel (`entity-detail.js`)

Generic component for expand-in-place entity viewing and editing.

### API
```js
renderEntityDetail(config) -> HTML string
bindEntityDetailEvents(container, config) -> void
```

### Config
```js
{
  entityId, entity, fields, onSave, onDelete, onCollapse
}
```

### Field definition
```js
{ name, label, type: 'text'|'textarea'|'select', options?: [{value, label}], required? }
```

### Behaviour
1. Default: read-only view with markdown for textarea fields
2. Edit button swaps to form mode
3. Save calls onSave, then collapses
4. Delete confirms, calls onDelete

## State additions
- `activeView: 'empty'|'project'|'global'`
- `expandedGlobalNotes: Set`
- `globalNoteFilter: ''`

## Init safety
- Do NOT eagerly bind event listeners to elements inside `#global-view` in `init()`
- Bind lazily when `selectGlobalWorkspace()` is called, or use optional chaining
- This prevents the crash that killed the previous attempt

## Files changed
| File | Change |
|------|--------|
| `js/components/entity-detail.js` | New: generic inline edit component |
| `js/components/global-notes.js` | Rewrite: full panel renderer using entity-detail |
| `js/router.js` | Add `/global/{tab}` namespace |
| `js/state.js` | Add activeView, expandedGlobalNotes, globalNoteFilter |
| `js/dom.js` | Add globalView refs, remove sidebar global note list refs |
| `js/app.js` | Add selectGlobalWorkspace(), update init/router/events |
| `index.html` | Add #global-view, replace sidebar global notes section |
| `index.css` | Styles for global workspace, entity detail panels |

## Follow-on: Replace modals for all entities
Separate task to apply EntityDetailPanel to tasks, decisions, and project notes, eliminating modal editing. Modals kept only for creating new entities.
