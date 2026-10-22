/* Plan graph (Tasks -> Graph). Alpine component used by partials/_plan_graph.html.
 *
 * Data comes from /api/plans/graph: one Mermaid source per repo group, built server-side
 * (dashboard_app/app/utils/plan_graph.py). Each group renders as its own SVG inside a panel the
 * viewer can drag as a block; edges between groups are drawn here, on an overlay layer that
 * follows the panels. Mermaid is pinned and loaded on first use, so no other page pays for it.
 *
 * No animation anywhere in this view: a status change only repaints color and glyph.
 * Panel positions are a per-viewer convenience kept in localStorage (per plan).
 */
(function () {
    const MERMAID_SRC = 'https://cdn.jsdelivr.net/npm/mermaid@11.4.1/dist/mermaid.min.js';
    const GLYPHS = { sinpr: '○', conpr: '◐', prbloq: '⚠', fusionada: '✓', cerrada: '✔', descartada: '⊘', pendiente: '…' };
    const CROSS_KEY = 'vision_plan_show_cross';
    const LAYOUT_PREFIX = 'vision_plan_layout:';
    const PANEL_GAP = 40;
    const KEY_STEP = 20;
    const SVG_NS = 'http://www.w3.org/2000/svg';
    let mermaidPromise = null;
    let renderSeq = 0;

    function loadMermaid() {
        if (window.mermaid) return Promise.resolve(window.mermaid);
        if (!mermaidPromise) {
            mermaidPromise = new Promise((resolve, reject) => {
                const script = document.createElement('script');
                script.src = MERMAID_SRC;
                script.onload = () => {
                    window.mermaid.initialize({
                        startOnLoad: false,
                        securityLevel: 'strict',
                        theme: 'base',
                        fontFamily: getComputedStyle(document.body).fontFamily,
                        themeVariables: {
                            fontSize: '13px',
                            lineColor: '#7f8ba3',
                            textColor: '#e2e8f0',
                            primaryTextColor: '#e2e8f0',
                            edgeLabelBackground: '#0b1233',
                        },
                        flowchart: { htmlLabels: true, curve: 'basis', nodeSpacing: 22, rankSpacing: 46, padding: 10 },
                    });
                    resolve(window.mermaid);
                };
                script.onerror = () => { mermaidPromise = null; reject(new Error('Mermaid failed to load')); };
                document.head.appendChild(script);
            });
        }
        return mermaidPromise;
    }

    // Browser storage can throw (private windows, blocked site data): always optional.
    function storageGet(key) {
        try { return localStorage.getItem(key); } catch (e) { return null; }
    }
    function storageSet(key, value) {
        try { localStorage.setItem(key, value); } catch (e) { /* per-viewer convenience only */ }
    }
    function storageRemove(key) {
        try { localStorage.removeItem(key); } catch (e) { /* per-viewer convenience only */ }
    }

    function svgEl(name, attrs) {
        const el = document.createElementNS(SVG_NS, name);
        Object.entries(attrs || {}).forEach(([k, v]) => el.setAttribute(k, v));
        return el;
    }

    window.planGraph = function (config) {
        return {
            apiUrl: config.apiUrl,
            state: 'loading',
            plans: [],
            planId: null,
            plan: null,
            nodes: [],
            edges: [],
            crossEdges: [],
            byKey: {},
            byMid: {},
            selectedKey: null,
            focusGroup: null,
            showCross: storageGet(CROSS_KEY) === 'true',
            positions: {},
            view: { x: 0, y: 0, k: 1 },
            fitted: false,
            panning: false,
            panStart: null,
            drag: null,
            pending: false,
            queued: false,
            isFullscreen: false,
            pseudoFullscreen: false,

            get selected() { return this.selectedKey ? this.byKey[this.selectedKey] : null; },

            init() {
                this.refresh();
                this._resize = () => { if (!this.fitted) this.fit(); this.drawCross(); };
                window.addEventListener('resize', this._resize);
                this._fsChange = () => this.onFullscreenChange();
                document.addEventListener('fullscreenchange', this._fsChange);
                document.addEventListener('webkitfullscreenchange', this._fsChange);
                // Web fonts can resize node labels after the first draw; anchor edges again.
                if (document.fonts && document.fonts.ready) document.fonts.ready.then(() => this.drawCross());
            },

            destroy() {
                window.removeEventListener('resize', this._resize);
                document.removeEventListener('fullscreenchange', this._fsChange);
                document.removeEventListener('webkitfullscreenchange', this._fsChange);
                // Leaving the view (boosted navigation) must not strand the browser in full screen.
                if (this.nativeFullscreenElement()) this.exitNative();
                if (this.pseudoFullscreen) document.documentElement.classList.remove('plan-pseudo-fullscreen-open');
            },

            // --- full screen: the legend/controls bar plus the canvas ($refs.focusArea) ---
            // Native Fullscreen API where available; otherwise a fixed overlay class (e.g. iPhone
            // Safari, which has no element full screen).
            nativeFullscreenElement() {
                return document.fullscreenElement || document.webkitFullscreenElement || null;
            },

            canUseNative() {
                const el = this.$refs.focusArea;
                return Boolean((document.fullscreenEnabled || document.webkitFullscreenEnabled)
                    && el && (el.requestFullscreen || el.webkitRequestFullscreen));
            },

            exitNative() {
                const exit = document.exitFullscreen || document.webkitExitFullscreen;
                if (exit) Promise.resolve(exit.call(document)).catch(() => {});
            },

            async toggleFullscreen() {
                if (this.isFullscreen) {
                    if (this.pseudoFullscreen) this.setPseudo(false);
                    else this.exitNative();
                    return;
                }
                const el = this.$refs.focusArea;
                if (this.canUseNative()) {
                    try {
                        await (el.requestFullscreen ? el.requestFullscreen() : el.webkitRequestFullscreen());
                        return;
                    } catch (err) {
                        console.warn('[PlanGraph] Native full screen refused, using overlay', err);
                    }
                }
                this.setPseudo(true);
            },

            setPseudo(on) {
                this.pseudoFullscreen = on;
                document.documentElement.classList.toggle('plan-pseudo-fullscreen-open', on);
                this.onFullscreenChange();
            },

            onFullscreenChange() {
                this.isFullscreen = this.pseudoFullscreen || this.nativeFullscreenElement() === this.$refs.focusArea;
                // The canvas changed size: refit after layout settles. Saved positions are untouched.
                requestAnimationFrame(() => requestAnimationFrame(() => { this.fit(); this.drawCross(); }));
            },

            onKey(event) {
                if (event.key === 'Escape') {
                    if (this.selectedKey) { this.selectedKey = null; this.select(null); return; }
                    if (this.pseudoFullscreen) this.setPseudo(false);
                    return;
                }
                const target = event.target;
                const typing = target && (target.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(target.tagName));
                if (typing || event.ctrlKey || event.metaKey || event.altKey) return;
                if ((event.key === 'f' || event.key === 'F') && this.plan) {
                    event.preventDefault();
                    this.toggleFullscreen();
                }
            },

            async refresh(resetView) {
                // SSE can burst (one datachanged per write); coalesce into at most one follow-up.
                if (this.pending) { this.queued = true; return; }
                this.pending = true;
                try {
                    const params = new URLSearchParams();
                    if (this.planId) params.set('plan_id', this.planId);
                    const response = await fetch(this.apiUrl + '?' + params.toString(), { headers: { Accept: 'application/json' } });
                    if (!response.ok) throw new Error('HTTP ' + response.status);
                    const data = await response.json();
                    this.plans = data.plans || [];
                    if (!data.plan) {
                        this.plan = null;
                        this.state = 'empty';
                        return;
                    }
                    if (resetView || data.plan.id !== this.planId) {
                        this.fitted = false;
                        this.selectedKey = null;
                        this.focusGroup = null;
                        this.positions = this.loadLayout(data.plan.id);
                        this.clearPanels();
                    }
                    this.planId = data.plan.id;
                    await this.render(data);
                    this.state = 'ready';
                } catch (err) {
                    console.error('[PlanGraph]', err);
                    this.state = this.plan ? 'ready' : 'error';
                } finally {
                    this.pending = false;
                    if (this.queued) { this.queued = false; this.refresh(); }
                }
            },

            async render(data) {
                const mermaid = await loadMermaid();
                this.plan = data.plan;
                this.nodes = data.nodes;
                this.edges = data.edges;
                this.crossEdges = data.cross_edges || [];
                this.byKey = Object.fromEntries(data.nodes.map((n) => [n.key, n]));
                this.byMid = Object.fromEntries(data.nodes.map((n) => [n.mid, n]));
                await this.$nextTick();

                // Sequential on purpose: mermaid.render shares a scratch element between calls.
                const rendered = [];
                for (const group of data.plan.groups) {
                    const { svg } = await mermaid.render('plan-mmd-' + (++renderSeq), group.mermaid);
                    rendered.push({ group, svg });
                }
                const keep = new Set(rendered.map((r) => r.group.key));
                this.panels().forEach((panel) => { if (!keep.has(panel.dataset.group)) panel.remove(); });
                rendered.forEach(({ group, svg }) => this.fillPanel(this.ensurePanel(group), group, svg));

                this.decorate();
                this.placeNewPanels();
                if (!this.fitted) this.fit(); else this.applyView();
                this.drawCross();
            },

            // --- panels: one per repo group, absolutely positioned in viewport space ---
            panels() {
                return Array.from(this.$refs.viewport.querySelectorAll('.plan-group-panel'));
            },

            panelFor(key) {
                return this.panels().find((p) => p.dataset.group === key) || null;
            },

            clearPanels() {
                this.panels().forEach((p) => p.remove());
            },

            ensurePanel(group) {
                let panel = this.panelFor(group.key);
                if (panel) return panel;
                panel = document.createElement('section');
                panel.className = 'plan-group-panel';
                panel.dataset.group = group.key;

                const handle = document.createElement('div');
                handle.className = 'plan-group-handle';
                handle.tabIndex = 0;
                handle.setAttribute('role', 'button');
                handle.innerHTML = '<i class="bi bi-grip-vertical" aria-hidden="true"></i>'
                    + '<span class="plan-group-name"></span><span class="plan-group-count"></span>';
                handle.addEventListener('pointerdown', (e) => this.startDrag(e, panel));
                handle.addEventListener('pointermove', (e) => this.moveDrag(e));
                handle.addEventListener('pointerup', (e) => this.endDrag(e));
                handle.addEventListener('pointercancel', (e) => this.endDrag(e));
                handle.addEventListener('keydown', (e) => this.keyMove(e, panel));

                const body = document.createElement('div');
                body.className = 'plan-group-body';
                panel.append(handle, body);
                this.$refs.viewport.appendChild(panel);
                return panel;
            },

            fillPanel(panel, group, svg) {
                const handle = panel.querySelector('.plan-group-handle');
                handle.querySelector('.plan-group-name').textContent = group.label;
                handle.querySelector('.plan-group-count').textContent = group.done + '/' + group.total;
                handle.setAttribute('aria-label', 'Move ' + group.label + ' graph. Use the arrow keys, or drag.');

                const body = panel.querySelector('.plan-group-body');
                body.innerHTML = svg;
                const svgNode = body.querySelector('svg');
                if (svgNode) {
                    // Mermaid sizes its SVG to the container with max-width; measure the drawing
                    // itself and pin that natural size, so panels have a stable box to drag.
                    svgNode.removeAttribute('style');
                    const root = svgNode.querySelector(':scope > g');
                    const pad = 12;
                    const bb = root ? root.getBBox() : svgNode.viewBox.baseVal;
                    svgNode.setAttribute('viewBox', [bb.x - pad, bb.y - pad, bb.width + 2 * pad, bb.height + 2 * pad].join(' '));
                    svgNode.setAttribute('width', bb.width + 2 * pad);
                    svgNode.setAttribute('height', bb.height + 2 * pad);
                }
            },

            placePanel(panel) {
                const pos = this.positions[panel.dataset.group];
                panel.style.left = pos.x + 'px';
                panel.style.top = pos.y + 'px';
            },

            // Groups without a saved position are stacked under everything else, in plan order.
            placeNewPanels() {
                let bottom = 0;
                const panels = this.panels();
                panels.forEach((panel) => {
                    const pos = this.positions[panel.dataset.group];
                    if (pos) bottom = Math.max(bottom, pos.y + panel.offsetHeight + PANEL_GAP);
                });
                panels.forEach((panel) => {
                    if (!this.positions[panel.dataset.group]) {
                        this.positions[panel.dataset.group] = { x: 0, y: bottom };
                        bottom += panel.offsetHeight + PANEL_GAP;
                    }
                    this.placePanel(panel);
                });
            },

            loadLayout(planId) {
                try {
                    const saved = JSON.parse(storageGet(LAYOUT_PREFIX + planId) || '{}');
                    return saved && typeof saved === 'object' ? saved : {};
                } catch (e) {
                    return {};
                }
            },

            saveLayout() {
                storageSet(LAYOUT_PREFIX + this.planId, JSON.stringify(this.positions));
            },

            resetLayout() {
                storageRemove(LAYOUT_PREFIX + this.planId);
                this.positions = {};
                this.placeNewPanels();
                this.fit();
                this.drawCross();
            },

            // --- dragging a group: pointer on its header, or arrow keys when it has focus ---
            startDrag(event, panel) {
                if (event.button !== 0) return;
                event.stopPropagation();
                const pos = this.positions[panel.dataset.group];
                this.drag = { panel, pointerId: event.pointerId, cx: event.clientX, cy: event.clientY, x: pos.x, y: pos.y };
                panel.classList.add('is-dragging');
                event.currentTarget.setPointerCapture(event.pointerId);
            },

            moveDrag(event) {
                if (!this.drag || event.pointerId !== this.drag.pointerId) return;
                const { panel, cx, cy, x, y } = this.drag;
                this.positions[panel.dataset.group] = {
                    x: Math.round(x + (event.clientX - cx) / this.view.k),
                    y: Math.round(y + (event.clientY - cy) / this.view.k),
                };
                this.placePanel(panel);
                this.drawCross();
            },

            endDrag(event) {
                if (!this.drag || event.pointerId !== this.drag.pointerId) return;
                this.drag.panel.classList.remove('is-dragging');
                try { event.currentTarget.releasePointerCapture(event.pointerId); } catch (e) { /* already released */ }
                this.drag = null;
                this.saveLayout();
            },

            keyMove(event, panel) {
                const step = event.shiftKey ? KEY_STEP * 4 : KEY_STEP;
                const delta = { ArrowLeft: [-step, 0], ArrowRight: [step, 0], ArrowUp: [0, -step], ArrowDown: [0, step] }[event.key];
                if (!delta) return;
                event.preventDefault();
                const pos = this.positions[panel.dataset.group];
                this.positions[panel.dataset.group] = { x: pos.x + delta[0], y: pos.y + delta[1] };
                this.placePanel(panel);
                this.drawCross();
                this.saveLayout();
            },

            // --- nodes: click/keyboard to open details ---
            nodeElements() {
                return Array.from(this.$refs.viewport.querySelectorAll('.plan-group-body g.node'));
            },

            midOf(el) {
                if (el.dataset && el.dataset.id) return el.dataset.id;
                const match = (el.id || '').match(/(n\d+)-\d+$/);
                return match ? match[1] : null;
            },

            decorate() {
                this.nodeElements().forEach((el) => {
                    const node = this.byMid[this.midOf(el)];
                    if (!node) return;
                    el.dataset.key = node.key;
                    if (node.kind !== 'issue') { el.classList.add('plan-node-base'); return; }
                    el.classList.add('plan-node');
                    el.setAttribute('tabindex', '0');
                    el.setAttribute('role', 'button');
                    el.setAttribute('aria-label', (node.display_key || node.key) + ' issue ' + node.issue + ': ' + node.status_name + '. Show details');
                    el.classList.toggle('is-selected', node.key === this.selectedKey);
                    el.addEventListener('click', (event) => { event.stopPropagation(); this.select(node.key); });
                    el.addEventListener('keydown', (event) => {
                        if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); this.select(node.key); }
                    });
                });
                this.applyFocusGroup();
            },

            select(key) {
                this.selectedKey = this.selectedKey === key ? null : key;
                this.nodeElements().forEach((el) => el.classList.toggle('is-selected', el.dataset.key === this.selectedKey));
            },

            toggleGroup(key) {
                this.focusGroup = this.focusGroup === key ? null : key;
                this.applyFocusGroup();
                this.drawCross();
            },

            applyFocusGroup() {
                this.panels().forEach((panel) => {
                    panel.classList.toggle('is-dimmed', Boolean(this.focusGroup) && panel.dataset.group !== this.focusGroup);
                });
            },

            // --- cross-repo edges: overlay layer in viewport space, redrawn as panels move ---
            // Node box in viewport space: its offset inside its own panel, measured at the scale
            // the browser actually rendered (panel rect / panel layout width), plus the panel's
            // saved position. Never trusts view.k, which can lead the painted transform.
            nodeBox(key) {
                const node = this.byKey[key];
                if (!node) return null;
                const el = this.nodeElements().find((n) => n.dataset.key === key);
                const panel = el ? el.closest('.plan-group-panel') : null;
                const pos = panel ? this.positions[panel.dataset.group] : null;
                if (!el || !pos || !panel.offsetWidth) return null;
                const pr = panel.getBoundingClientRect();
                const r = el.getBoundingClientRect();
                const scale = pr.width / panel.offsetWidth || 1;
                const left = pos.x + (r.left - pr.left) / scale;
                const top = pos.y + (r.top - pr.top) / scale;
                return { left, right: left + r.width / scale, cy: top + r.height / scale / 2 };
            },

            drawCross() {
                const layer = this.$refs.crossLayer;
                if (!layer) return;
                layer.querySelectorAll('.plan-cross-edge').forEach((g) => g.remove());
                layer.style.display = this.showCross ? '' : 'none';
                if (!this.showCross) return;
                this.crossEdges.forEach((edge) => {
                    const a = this.nodeBox(edge.from);
                    const b = this.nodeBox(edge.to);
                    if (!a || !b) return;
                    // Leave from the side facing the target, so a panel moved left still reads.
                    const forward = b.left >= a.right;
                    const x1 = forward ? a.right : a.left;
                    const x2 = forward ? b.left : b.right;
                    const bend = Math.max(40, Math.abs(x2 - x1) / 2) * (forward ? 1 : -1);
                    const d = `M ${x1} ${a.cy} C ${x1 + bend} ${a.cy}, ${x2 - bend} ${b.cy}, ${x2} ${b.cy}`;
                    const g = svgEl('g', { class: 'plan-cross-edge' });
                    const fromGroup = this.byKey[edge.from].group;
                    const toGroup = this.byKey[edge.to].group;
                    if (this.focusGroup && fromGroup !== this.focusGroup && toGroup !== this.focusGroup) g.classList.add('is-dimmed');
                    g.appendChild(svgEl('path', { d, 'marker-end': 'url(#plan-cross-arrow)' }));
                    if (edge.label) {
                        const label = svgEl('text', { x: (x1 + x2) / 2, y: (a.cy + b.cy) / 2 - 6, 'text-anchor': 'middle' });
                        label.textContent = edge.label;
                        g.appendChild(label);
                    }
                    layer.appendChild(g);
                });
            },

            setCross() {
                storageSet(CROSS_KEY, String(this.showCross));
                this.drawCross();
            },

            dependencies(key, direction) {
                return this.edges
                    .filter((e) => (direction === 'in' ? e.to === key : e.from === key))
                    .map((e) => {
                        const other = this.byKey[direction === 'in' ? e.from : e.to];
                        if (!other || other.kind !== 'issue') return null;
                        const how = { stacked: 'stacked', after_merge: 'after merge', cross: e.label || 'condition' }[e.kind] || '';
                        return { key: other.key, kind: e.kind, text: (other.display_key || other.key) + ' #' + other.issue + (how ? ' (' + how + ')' : '') };
                    })
                    .filter(Boolean);
            },

            glyph(status) { return GLYPHS[status || 'pendiente']; },

            prSummary(node) {
                const parts = [];
                if (node.pr_state === 'MERGED') parts.push('merged');
                else if (node.pr_is_draft) parts.push('draft');
                else if (node.pr_state === 'OPEN') parts.push('open');
                if (node.ci === 'FAILURE' || node.ci === 'ERROR') parts.push('CI failing');
                else if (node.ci === 'SUCCESS') parts.push('CI passing');
                else if (node.ci === 'PENDING' || node.ci === 'EXPECTED') parts.push('CI running');
                if (node.review === 'CHANGES_REQUESTED') parts.push('changes requested');
                else if (node.review === 'APPROVED') parts.push('approved');
                else if (node.review === 'REVIEW_REQUIRED') parts.push('review required');
                return parts.length ? ': ' + parts.join(', ') : '';
            },

            // --- pan & zoom: one transform on the viewport ---
            applyView() {
                this.$refs.viewport.style.transform = `translate(${this.view.x}px, ${this.view.y}px) scale(${this.view.k})`;
            },

            contentBounds() {
                let right = 0, bottom = 0, left = Infinity, top = Infinity;
                this.panels().forEach((panel) => {
                    const pos = this.positions[panel.dataset.group] || { x: 0, y: 0 };
                    left = Math.min(left, pos.x);
                    top = Math.min(top, pos.y);
                    right = Math.max(right, pos.x + panel.offsetWidth);
                    bottom = Math.max(bottom, pos.y + panel.offsetHeight);
                });
                if (left === Infinity) return null;
                return { left, top, w: right - left, h: bottom - top };
            },

            fit() {
                const canvas = this.$refs.canvas;
                const box = this.contentBounds();
                if (!box || !canvas.clientWidth) return;
                const margin = 24;
                const availW = canvas.clientWidth - 2 * margin;
                const availH = canvas.clientHeight - 2 * margin;
                // Fit the width; only shrink further for height down to a readable floor, then
                // let the viewer pan. A 60-node plan fitted whole would be unreadable.
                let k = Math.min(availW / box.w, 1);
                if (box.h * k > availH) k = Math.max(availH / box.h, Math.min(k, 0.72));
                this.view = {
                    k,
                    x: margin + Math.max((availW - box.w * k) / 2, 0) - box.left * k,
                    y: margin + Math.max((availH - box.h * k) / 2, 0) - box.top * k,
                };
                this.fitted = true;
                this.applyView();
            },

            zoomBy(factor, cx, cy) {
                const canvas = this.$refs.canvas;
                const px = cx === undefined ? canvas.clientWidth / 2 : cx;
                const py = cy === undefined ? canvas.clientHeight / 2 : cy;
                const k = Math.min(Math.max(this.view.k * factor, 0.15), 3);
                const ratio = k / this.view.k;
                this.view = { k, x: px - (px - this.view.x) * ratio, y: py - (py - this.view.y) * ratio };
                this.applyView();
            },

            onWheel(event) {
                const rect = this.$refs.canvas.getBoundingClientRect();
                this.zoomBy(event.deltaY < 0 ? 1.1 : 1 / 1.1, event.clientX - rect.left, event.clientY - rect.top);
            },

            startPan(event) {
                if (event.button !== 0 || event.target.closest('g.node, .plan-group-handle')) return;
                this.panning = true;
                this.panStart = { x: event.clientX - this.view.x, y: event.clientY - this.view.y };
                this.$refs.canvas.setPointerCapture(event.pointerId);
            },

            movePan(event) {
                if (!this.panning) return;
                this.view = { ...this.view, x: event.clientX - this.panStart.x, y: event.clientY - this.panStart.y };
                this.applyView();
            },

            endPan(event) {
                if (!this.panning) return;
                this.panning = false;
                try { this.$refs.canvas.releasePointerCapture(event.pointerId); } catch (e) { /* already released */ }
            },

            // --- formatting (viewer's locale; timestamps arrive as UTC ISO strings) ---
            formatDate(iso) {
                return new Date(iso + 'T00:00:00').toLocaleDateString(undefined, { weekday: 'short', day: 'numeric', month: 'short' });
            },

            formatDateTime(iso) {
                return new Date(iso).toLocaleString(undefined, { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
            },

            relativeTime(iso) {
                const seconds = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 1000));
                if (seconds < 60) return 'just now';
                const minutes = Math.round(seconds / 60);
                if (minutes < 60) return minutes + ' min ago';
                return this.formatDateTime(iso);
            },
        };
    };
})();
