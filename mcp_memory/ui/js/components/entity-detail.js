/* components/entity-detail.js — Generic expand-in-place entity viewer/editor */

import { esc } from '../utils.js';

export function renderEntityDetail(config) {
    const { entityId, entity, fields, showDelete = true } = config;

    // View mode HTML
    const viewHtml = fields.map(f => {
        let valHtml = '';
        const rawVal = entity[f.name] || '';
        if (f.type === 'textarea') {
            valHtml = `<div class="field-value markdown-body">${marked.parse(rawVal)}</div>`;
        } else {
            valHtml = `<div class="field-value">${esc(rawVal)}</div>`;
        }
        return `
            <div class="field-row">
                <div class="field-label">${esc(f.label)}</div>
                ${valHtml}
            </div>
        `;
    }).join('');

    // Form mode HTML
    const formHtml = fields.map(f => {
        const rawVal = entity[f.name] || '';
        let inputHtml = '';
        if (f.type === 'textarea') {
            inputHtml = `<textarea name="${f.name}" class="form-control" ${f.required ? 'required' : ''}>${esc(rawVal)}</textarea>`;
        } else if (f.type === 'select') {
            const optionsHtml = f.options.map(o =>
                `<option value="${o.value}" ${rawVal === o.value ? 'selected' : ''}>${esc(o.label)}</option>`
            ).join('');
            inputHtml = `<select name="${f.name}" class="form-control">${optionsHtml}</select>`;
        } else {
            inputHtml = `<input type="text" name="${f.name}" class="form-control" value="${esc(rawVal)}" ${f.required ? 'required' : ''}>`;
        }
        return `
            <div class="form-group">
                <label>${esc(f.label)}</label>
                ${inputHtml}
            </div>
        `;
    }).join('');

    return `
        <div class="entity-detail" id="entity-detail-${entityId}" data-entity-id="${entityId}">
            <!-- View Mode -->
            <div class="entity-detail-view" id="entity-view-${entityId}">
                ${viewHtml}
                <div class="entity-detail-actions">
                    <button class="btn-secondary btn-edit-entity" data-id="${entityId}">Edit</button>
                    ${showDelete ? `<button class="btn-secondary danger btn-delete-entity" data-id="${entityId}">Delete</button>` : ''}
                </div>
            </div>

            <!-- Edit Mode -->
            <form class="entity-detail-form hidden" id="entity-form-${entityId}">
                ${formHtml}
                <div class="entity-detail-actions">
                    <button type="button" class="btn-secondary btn-cancel-edit" data-id="${entityId}">Cancel</button>
                    <button type="submit" class="btn-primary btn-save-entity" data-id="${entityId}">Save</button>
                </div>
            </form>
        </div>
    `;
}

export function bindEntityDetailEvents(container, config) {
    const { entityId, onSave, onDelete, onCollapse } = config;

    const viewEl = container.querySelector(`#entity-view-${entityId}`);
    const formEl = container.querySelector(`#entity-form-${entityId}`);

    if (!viewEl || !formEl) return;

    const editBtn = viewEl.querySelector('.btn-edit-entity');
    const deleteBtn = viewEl.querySelector('.btn-delete-entity');

    const cancelBtn = formEl.querySelector('.btn-cancel-edit');

    editBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        viewEl.classList.add('hidden');
        formEl.classList.remove('hidden');
    });

    if (deleteBtn) {
        deleteBtn.addEventListener('click', async (e) => {
            e.stopPropagation();
            if (confirm('Are you sure you want to delete this?')) {
                if (onDelete) await onDelete(entityId);
            }
        });
    }

    cancelBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        formEl.reset(); // Reset to original values
        formEl.classList.add('hidden');
        viewEl.classList.remove('hidden');
    });

    formEl.addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = new FormData(formEl);
        const data = {};
        formData.forEach((value, key) => data[key] = value);

        // Disable form while saving if desired
        const submitBtn = formEl.querySelector('button[type="submit"]');
        const origText = submitBtn.textContent;
        submitBtn.textContent = 'Saving...';
        submitBtn.disabled = true;

        try {
            if (onSave) await onSave(entityId, data);
            // Re-render handled by caller (e.g. reload())
        } catch (err) {
            alert('Failed to save: ' + err.message);
            submitBtn.textContent = origText;
            submitBtn.disabled = false;
        }
    });
}
