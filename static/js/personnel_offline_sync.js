(function () {
    var DB_NAME = 'gso_personnel_offline_db';
    var STORE_NAME = 'queue';
    var DB_VERSION = 1;
    var SYNC_INTERVAL_MS = 30000;
    var RETRY_BASE_MS = 5000;
    var RETRY_MAX_MS = 5 * 60 * 1000;
    var STATUS_ACTION_RE = /\/staff\/request-management\/\d+\/status\/?$/;
    var MESSAGE_ACTION_RE = /\/staff\/request-management\/\d+\/message\/?$/;

    function nowIso() {
        return new Date().toISOString();
    }

    function sleep(ms) {
        return new Promise(function (resolve) { setTimeout(resolve, ms); });
    }

    function randomId() {
        if (window.crypto && window.crypto.randomUUID) return window.crypto.randomUUID();
        return 'q_' + Date.now() + '_' + Math.random().toString(16).slice(2);
    }

    function normalizeActionUrl(actionUrl) {
        try {
            return new URL(actionUrl, window.location.origin).toString();
        } catch (e) {
            return actionUrl;
        }
    }

    function computeBackoffMs(retryCount) {
        var ms = RETRY_BASE_MS * Math.pow(2, Math.max(0, retryCount || 0));
        return Math.min(ms, RETRY_MAX_MS);
    }

    function toPayloadObject(formData) {
        var payload = {};
        formData.forEach(function (value, key) {
            payload[key] = value;
        });
        return payload;
    }

    function buildFormData(payload) {
        var fd = new FormData();
        Object.keys(payload || {}).forEach(function (key) {
            fd.append(key, payload[key]);
        });
        return fd;
    }

    function isPersonnelAction(actionUrl) {
        try {
            var pathname = new URL(actionUrl, window.location.origin).pathname;
            return STATUS_ACTION_RE.test(pathname) || MESSAGE_ACTION_RE.test(pathname);
        } catch (e) {
            return false;
        }
    }

    function inferTypeFromAction(actionUrl) {
        var pathname = new URL(actionUrl, window.location.origin).pathname;
        if (STATUS_ACTION_RE.test(pathname)) return 'status_update';
        if (MESSAGE_ACTION_RE.test(pathname)) return 'request_message';
        return 'unknown';
    }

    function getRequestId(actionUrl) {
        var pathname = new URL(actionUrl, window.location.origin).pathname;
        var match = pathname.match(/\/staff\/request-management\/(\d+)\//);
        return match ? match[1] : '';
    }

    function openDb() {
        return new Promise(function (resolve, reject) {
            var req = indexedDB.open(DB_NAME, DB_VERSION);
            req.onupgradeneeded = function (event) {
                var db = event.target.result;
                if (!db.objectStoreNames.contains(STORE_NAME)) {
                    var store = db.createObjectStore(STORE_NAME, { keyPath: 'id' });
                    store.createIndex('status', 'status', { unique: false });
                    store.createIndex('next_retry_at', 'next_retry_at', { unique: false });
                    store.createIndex('created_at', 'created_at', { unique: false });
                }
            };
            req.onsuccess = function () { resolve(req.result); };
            req.onerror = function () { reject(req.error); };
        });
    }

    function withStore(mode, fn) {
        return openDb().then(function (db) {
            return new Promise(function (resolve, reject) {
                var tx = db.transaction(STORE_NAME, mode);
                var store = tx.objectStore(STORE_NAME);
                var result = fn(store);
                tx.oncomplete = function () { resolve(result); db.close(); };
                tx.onerror = function () { reject(tx.error); db.close(); };
                tx.onabort = function () { reject(tx.error); db.close(); };
            });
        });
    }

    function putItem(item) {
        return withStore('readwrite', function (store) {
            store.put(item);
        });
    }

    function deleteItem(id) {
        return withStore('readwrite', function (store) {
            store.delete(id);
        });
    }

    function getAllItems() {
        return openDb().then(function (db) {
            return new Promise(function (resolve, reject) {
                var tx = db.transaction(STORE_NAME, 'readonly');
                var store = tx.objectStore(STORE_NAME);
                var req = store.getAll();
                req.onsuccess = function () { resolve(req.result || []); };
                req.onerror = function () { reject(req.error); };
                tx.oncomplete = function () { db.close(); };
            });
        });
    }

    function toast(message, tone) {
        var id = 'gso-offline-toast';
        var existing = document.getElementById(id);
        if (existing) existing.remove();
        var el = document.createElement('div');
        el.id = id;
        el.className = 'fixed bottom-4 left-4 z-[200] rounded-lg px-4 py-3 text-sm font-medium shadow-lg border';
        if (tone === 'error') {
            el.className += ' bg-red-50 text-red-700 border-red-200';
        } else {
            el.className += ' bg-blue-50 text-blue-700 border-blue-200';
        }
        el.textContent = message;
        document.body.appendChild(el);
        setTimeout(function () { if (el.parentNode) el.remove(); }, 2800);
    }

    function ensureStatusBadge() {
        var badge = document.getElementById('gso-network-badge');
        if (!badge) {
            badge = document.createElement('div');
            badge.id = 'gso-network-badge';
            badge.className = 'fixed bottom-4 right-4 z-[200] rounded-lg px-3 py-2 text-xs font-semibold shadow border';
            document.body.appendChild(badge);
        }
        var pendingCount = 0;
        return getAllItems().then(function (items) {
            pendingCount = (items || []).filter(function (i) {
                return i.status === 'pending' || i.status === 'syncing';
            }).length;
            if (navigator.onLine) {
                badge.className = 'fixed bottom-4 right-4 z-[200] rounded-lg px-3 py-2 text-xs font-semibold shadow border bg-emerald-50 text-emerald-700 border-emerald-200';
                badge.textContent = pendingCount > 0 ? ('Online • ' + pendingCount + ' pending sync') : 'Online';
            } else {
                badge.className = 'fixed bottom-4 right-4 z-[200] rounded-lg px-3 py-2 text-xs font-semibold shadow border bg-amber-50 text-amber-700 border-amber-200';
                badge.textContent = pendingCount > 0 ? ('Offline • ' + pendingCount + ' queued') : 'Offline';
            }
        });
    }

    function isOfflineAllowedPersonnelHref(href) {
        try {
            var pathname = new URL(href, window.location.origin).pathname;
            return pathname.startsWith('/accounts/staff/task-management/')
                || pathname.startsWith('/accounts/staff/task-history/')
                || /\/accounts\/staff\/request-management\/\d+\/$/.test(pathname);
        } catch (e) {
            return false;
        }
    }

    function updateOfflineTaskModeUi() {
        var wrapper = document.getElementById('staff-wrapper');
        if (!wrapper || wrapper.getAttribute('data-is-personnel') !== '1') return;
        var sidebar = document.getElementById('staff-sidebar');
        if (!sidebar) return;
        var links = sidebar.querySelectorAll('a[href]');
        links.forEach(function (link) {
            var allow = isOfflineAllowedPersonnelHref(link.href);
            if (!navigator.onLine && !allow) {
                link.classList.add('opacity-60');
                link.setAttribute('data-offline-blocked', '1');
                link.setAttribute('title', 'Offline mode: Task pages only');
            } else {
                link.classList.remove('opacity-60');
                link.removeAttribute('data-offline-blocked');
            }
        });
    }

    function initOfflineTaskMode() {
        var wrapper = document.getElementById('staff-wrapper');
        if (!wrapper || wrapper.getAttribute('data-is-personnel') !== '1') return;
        document.addEventListener('click', function (event) {
            var link = event.target.closest('#staff-sidebar a[href]');
            if (!link) return;
            if (navigator.onLine) return;
            if (isOfflineAllowedPersonnelHref(link.href)) return;
            event.preventDefault();
            toast('Offline Task Mode: only Task Management is available offline.', 'info');
        }, true);
        updateOfflineTaskModeUi();
    }

    function dedupePendingStatus(item, allItems) {
        if (item.type !== 'status_update') return Promise.resolve();
        var duplicates = (allItems || []).filter(function (q) {
            return q.id !== item.id
                && q.type === 'status_update'
                && q.request_id === item.request_id
                && (q.status === 'pending' || q.status === 'syncing');
        });
        return Promise.all(duplicates.map(function (dup) { return deleteItem(dup.id); }));
    }

    function enqueue(actionUrl, method, formData) {
        var normalized = normalizeActionUrl(actionUrl);
        var payload = toPayloadObject(formData);
        var item = {
            id: randomId(),
            type: inferTypeFromAction(normalized),
            request_id: getRequestId(normalized),
            url: normalized,
            method: (method || 'POST').toUpperCase(),
            payload: payload,
            created_at: nowIso(),
            updated_at: nowIso(),
            next_retry_at: Date.now(),
            retry_count: 0,
            status: 'pending',
            error_message: '',
            idempotency_key: randomId()
        };
        return getAllItems()
            .then(function (items) { return dedupePendingStatus(item, items); })
            .then(function () { return putItem(item); })
            .then(function () { return ensureStatusBadge(); })
            .then(function () { return item; });
    }

    function updateItem(item, patch) {
        var merged = Object.assign({}, item, patch, { updated_at: nowIso() });
        return putItem(merged).then(function () { return merged; });
    }

    function postQueuedItem(item) {
        var formData = buildFormData(item.payload);
        return fetch(item.url, {
            method: item.method,
            body: formData,
            credentials: 'same-origin',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-Offline-Sync': '1',
                'X-Idempotency-Key': item.idempotency_key,
                'Accept': 'application/json'
            }
        }).then(function (response) {
            return response.json().catch(function () { return {}; }).then(function (data) {
                return { response: response, data: data };
            });
        });
    }

    var syncInProgress = false;
    function syncQueue() {
        if (syncInProgress || !navigator.onLine) return Promise.resolve();
        syncInProgress = true;
        return getAllItems()
            .then(function (items) {
                var now = Date.now();
                var pending = (items || [])
                    .filter(function (i) { return i.status === 'pending' && (i.next_retry_at || 0) <= now; })
                    .sort(function (a, b) { return (a.created_at || '').localeCompare(b.created_at || ''); });
                if (!pending.length) return;
                return pending.reduce(function (chain, item) {
                    return chain.then(function () {
                        return updateItem(item, { status: 'syncing' })
                            .then(function (syncingItem) {
                                return postQueuedItem(syncingItem).then(function (result) {
                                    if (result.response.ok && result.data && result.data.ok) {
                                        return deleteItem(syncingItem.id);
                                    }
                                    var permanentFailure = result.response.status >= 400 && result.response.status < 500;
                                    if (permanentFailure) {
                                        return updateItem(syncingItem, {
                                            status: 'failed',
                                            error_message: (result.data && result.data.error) || 'Sync failed'
                                        });
                                    }
                                    var retries = (syncingItem.retry_count || 0) + 1;
                                    return updateItem(syncingItem, {
                                        status: 'pending',
                                        retry_count: retries,
                                        next_retry_at: Date.now() + computeBackoffMs(retries),
                                        error_message: (result.data && result.data.error) || 'Temporary sync issue'
                                    });
                                }).catch(function () {
                                    var retries = (syncingItem.retry_count || 0) + 1;
                                    return updateItem(syncingItem, {
                                        status: 'pending',
                                        retry_count: retries,
                                        next_retry_at: Date.now() + computeBackoffMs(retries),
                                        error_message: 'Network error while syncing'
                                    });
                                });
                            })
                            .then(function () { return sleep(50); });
                    });
                }, Promise.resolve());
            })
            .finally(function () {
                syncInProgress = false;
                ensureStatusBadge();
            });
    }

    function submitOrQueue(opts) {
        var action = normalizeActionUrl(opts.action || '');
        var method = (opts.method || 'POST').toUpperCase();
        var formData = opts.formData;
        var renderHtml = opts.onHtml;
        var onQueue = opts.onQueue;
        if (!isPersonnelAction(action)) return Promise.resolve(false);
        if (!navigator.onLine) {
            return enqueue(action, method, formData).then(function () {
                if (typeof onQueue === 'function') onQueue();
                toast('Saved offline. Will sync when online.', 'info');
                return true;
            });
        }
        return fetch(action, {
            method: method,
            headers: { 'X-Requested-With': 'XMLHttpRequest' },
            body: formData,
            credentials: 'same-origin'
        }).then(function (r) { return r.text(); })
            .then(function (html) {
                if (typeof renderHtml === 'function') renderHtml(html);
                return true;
            })
            .catch(function () {
                return enqueue(action, method, formData).then(function () {
                    if (typeof onQueue === 'function') onQueue();
                    toast('No internet. Action queued for sync.', 'info');
                    return true;
                });
            });
    }

    function init() {
        ensureStatusBadge();
        initOfflineTaskMode();
        window.addEventListener('online', function () {
            ensureStatusBadge();
            updateOfflineTaskModeUi();
            syncQueue();
            toast('Back online. Syncing queued actions...', 'info');
        });
        window.addEventListener('offline', function () {
            ensureStatusBadge();
            updateOfflineTaskModeUi();
            toast('Offline Task Mode enabled for personnel.', 'info');
        });
        setInterval(function () {
            syncQueue();
            ensureStatusBadge();
        }, SYNC_INTERVAL_MS);
        syncQueue();
    }

    window.GSOPersonnelOffline = {
        init: init,
        enqueue: enqueue,
        syncQueue: syncQueue,
        submitOrQueue: submitOrQueue,
        isPersonnelAction: isPersonnelAction
    };
})();
