/* api.js — API interaction layer */

export const api = {
    async request(path, method = 'GET', body = null) {
        const options = { method };
        if (body) {
            options.headers = { 'Content-Type': 'application/json' };
            options.body = JSON.stringify(body);
        }
        const res = await fetch(path, options);
        if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: res.statusText }));
            throw new Error(err.detail || `API error: ${res.status}`);
        }
        return res.json();
    },
    get(path) { return this.request(path, 'GET'); },
    post(path, body) { return this.request(path, 'POST', body); },
    patch(path, body) { return this.request(path, 'PATCH', body); },
    delete(path) { return this.request(path, 'DELETE'); }
};
