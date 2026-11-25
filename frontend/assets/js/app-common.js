/* app-common.js - phần dùng chung của trang Khách hàng / Chuyên gia / Quản trị.
 * - Gọi API thật (không có dữ liệu giả): chưa đăng nhập thì chuyển tới trang đăng nhập.
 * - Dùng chung phiên đăng nhập với trang đăng nhập khách (access_token) và trang Provider (provider_token).
 * - Đổi địa chỉ backend:  localStorage.setItem('provider_api_base', 'http://192.168.1.10:8000')
 */
(function (global) {
    'use strict';
    const SCRIPT = document.currentScript && document.currentScript.src;
    const SAME_ORIGIN = /^https?:$/.test(location.protocol) && location.pathname.indexOf('/web/') === 0;
    const store = {
        get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
        set(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* bỏ qua */ } },
        del(k) { try { localStorage.removeItem(k); } catch (e) { /* bỏ qua */ } }
    };
    const TOKEN_KEYS = ['access_token', 'token', 'provider_token'];
    const USER_KEYS = ['user', 'provider_user'];
    const apiBase = () => (store.get('provider_api_base') || (SAME_ORIGIN ? '' : 'http://127.0.0.1:8000')).replace(/\/+$/, '');
    const token = () => TOKEN_KEYS.map(store.get).find(Boolean) || null;
    function me() {
        for (const k of USER_KEYS) { try { const u = JSON.parse(store.get(k) || 'null'); if (u) return u; } catch (e) { /* bỏ qua */ } }
        return null;
    }
    function clearSession() { TOKEN_KEYS.concat(USER_KEYS).forEach(store.del); }
    const loginUrl = () => SCRIPT ? new URL('../../customer/auth.html', SCRIPT).href : '../customer/auth.html';
    function goLogin() {
        const m = location.pathname.match(/\/((?:customer|expert|admin)\/[\w-]+\.html)$/);
        location.href = loginUrl() + (m ? '?next=' + encodeURIComponent(m[1] + location.search) : '');
    }
    function logout() { clearSession(); goLogin(); }

    class ApiError extends Error { constructor(m, status) { super(m); this.status = status; } }
    function messageOf(body, status) {
        if (body && typeof body.detail === 'string') return body.detail;
        if (body && Array.isArray(body.detail)) return body.detail.map(e => (e.loc ? e.loc.slice(1).join('.') + ': ' : '') + e.msg).join('; ');
        if (status === 401) return 'Phiên đăng nhập đã hết hạn, hãy đăng nhập lại.';
        if (status === 403) return 'Bạn không có quyền thực hiện thao tác này.';
        if (status === 503) return 'Dịch vụ chưa sẵn sàng (có thể cần chạy thêm file SQL).';
        return 'Lỗi máy chủ (HTTP ' + status + ')';
    }
    async function api(path, opts) {
        opts = opts || {};
        const headers = { Accept: 'application/json' };
        if (opts.body !== undefined) headers['Content-Type'] = 'application/json';
        if (opts.auth !== false && token()) headers.Authorization = 'Bearer ' + token();
        let res;
        try {
            res = await fetch(apiBase() + path, { method: opts.method || 'GET', headers, body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined });
        } catch (e) { throw new ApiError('Không kết nối được Backend (' + (apiBase() || location.origin) + '). Hãy chạy uvicorn.', 0); }
        if (res.status === 204) return null;
        let body = null;
        try { body = await res.json(); } catch (e) { /* không có JSON */ }
        if (res.status === 401 && opts.auth !== false && token()) { clearSession(); goLogin(); throw new ApiError(messageOf(body, 401), 401); }
        if (!res.ok) throw new ApiError(messageOf(body, res.status), res.status);
        return body;
    }
    const qs = o => { const p = Object.entries(o || {}).filter(([, v]) => v !== undefined && v !== null && v !== '').map(([k, v]) => encodeURIComponent(k) + '=' + encodeURIComponent(v)); return p.length ? '?' + p.join('&') : ''; };

    /* Bắt buộc đăng nhập đúng vai trò. Trả về user hoặc null (và đã vẽ màn chặn / chuyển trang). */
    async function requireRole(roles, label) {
        if (!token()) { goLogin(); return null; }
        let u = me();
        try { u = await api('/api/users/me'); store.set('user', JSON.stringify(u)); } catch (e) { if (e.status === 401) return null; if (!u) { gate('Không kết nối được máy chủ', e.message); return null; } }
        const role = String(u.role || '').toUpperCase();
        if (roles.indexOf(role) < 0) { gate('Sai vai trò', 'Tài khoản <b>' + esc(u.username) + '</b> có vai trò ' + role + ', không dùng được trang ' + esc(label) + '.', true); return null; }
        return u;
    }
    function gate(title, html, withLogout) {
        document.body.innerHTML = '<div class="gate"><div class="card"><h2>' + esc(title) + '</h2><p class="mute" style="margin:8px 0 18px">' + html + '</p>' +
            (withLogout ? '<button class="btn" id="gateOut">Đăng xuất</button>' : '<button class="btn" onclick="location.reload()">Thử lại</button>') + '</div></div>';
        const b = document.getElementById('gateOut'); if (b) b.onclick = logout;
    }

    /* ---------- tiện ích hiển thị ---------- */
    const esc = s => String(s === null || s === undefined ? '' : s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
    const money = n => (Number(n) || 0).toLocaleString('vi-VN') + ' đ';
    const pad = n => String(n).padStart(2, '0');
    const toDate = s => (s instanceof Date ? s : new Date(String(s).replace(' ', 'T')));
    const fd = s => { if (!s) return '—'; const d = toDate(s); return pad(d.getDate()) + '/' + pad(d.getMonth() + 1) + '/' + d.getFullYear(); };
    const ft = s => { if (!s) return '—'; const d = toDate(s); return pad(d.getHours()) + ':' + pad(d.getMinutes()); };
    const fdt = s => s ? fd(s) + ' ' + ft(s) : '—';
    const iso = (d, h, m) => d + 'T' + pad(h) + ':' + pad(m || 0) + ':00';          // "2026-12-01T09:00:00" (giờ địa phương)
    const todayStr = () => { const d = new Date(); return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()); };
    const initials = n => String(n || '?').trim().split(/\s+/).slice(-2).map(w => w[0]).join('').toUpperCase() || '?';
    const STATUS = {
        PENDING: ['Chờ duyệt', 'pend'], CONFIRMED: ['Đã duyệt', 'ok'], IN_USE: ['Đang dùng', 'ok'], COMPLETED: ['Hoàn thành', ''], CANCELLED: ['Đã hủy', 'bad'],
        ACTIVE: ['Hoạt động', 'ok'], SUSPENDED: ['Bị khóa', 'bad'], APPROVED: ['Đã duyệt', 'ok'], REJECTED: ['Từ chối', 'bad'],
        SUCCESS: ['Thành công', 'ok'], FAILED: ['Thất bại', 'bad'], REFUNDED: ['Đã hoàn', 'gray'],
        OPEN: ['Mở', 'pend'], IN_REVIEW: ['Đang xử lý', 'pend'], RESOLVED: ['Đã giải quyết', 'ok'], CLOSED: ['Đã đóng', 'gray'], CANCELLED_WS: ['Đã hủy', 'bad']
    };
    const chip = s => { const x = STATUS[s] || [s, '']; return '<span class="chip ' + x[1] + '">' + esc(x[0]) + '</span>'; };
    const ROLE = { CUSTOMER: 'Khách hàng', PROVIDER: 'Nhà cung cấp', EXPERT: 'Chuyên gia', ADMIN: 'Quản trị viên' };
    const POST_TYPE = { ARTICLE: 'Bài viết', TUTORIAL: 'Hướng dẫn', EQUIPMENT_REVIEW: 'Đánh giá thiết bị', DISCUSSION: 'Thảo luận', WORKSHOP_ANNOUNCEMENT: 'Thông báo workshop', WORKSHOP: 'Workshop' };
    const PAY = { VNPAY: 'VNPay', MOMO: 'MoMo', STRIPE: 'Stripe', CASH: 'Tiền mặt', BANK_TRANSFER: 'Chuyển khoản' };

    function toast(msg, bad) {
        const t = document.createElement('div'); t.className = 'toast'; t.textContent = msg; if (bad) t.style.background = '#b9341f', t.style.color = '#fff';
        document.body.append(t); setTimeout(() => t.remove(), bad ? 4200 : 2400);
    }
    function sheet(html, wide) {
        closeSheet(); const o = document.createElement('div'); o.className = 'ov'; o.id = 'ov';
        o.innerHTML = '<div class="sheet' + (wide ? ' wide' : '') + '">' + html + '</div>'; o.onclick = e => { if (e.target === o) closeSheet(); };
        document.body.append(o); return o.firstChild;
    }
    function closeSheet() { const o = document.getElementById('ov'); if (o) o.remove(); }
    /* Chạy thao tác async: khóa nút, báo lỗi bằng toast, trả về kết quả hoặc undefined khi lỗi. */
    async function run(fn, btn, okMsg) {
        if (btn) btn.disabled = true;
        try { const r = await fn(); if (okMsg) toast(okMsg); return r == null ? true : r; }
        catch (e) { toast(e.message || String(e), true); return undefined; }
        finally { if (btn) btn.disabled = false; }
    }
    function applyTheme() { const t = store.get('provider_theme'); if (t) document.documentElement.dataset.theme = t; }
    function toggleTheme() {
        const d = document.documentElement, dark = d.dataset.theme === 'dark' || (!d.dataset.theme && matchMedia('(prefers-color-scheme:dark)').matches);
        d.dataset.theme = dark ? 'light' : 'dark'; store.set('provider_theme', d.dataset.theme);
    }
    function debounce(fn, ms) { let t; return function () { const a = arguments, c = this; clearTimeout(t); t = setTimeout(() => fn.apply(c, a), ms); }; }
    const fileToBase64 = f => new Promise((ok, no) => { const r = new FileReader(); r.onload = () => ok(String(r.result).split(',')[1]); r.onerror = () => no(new Error('Không đọc được file')); r.readAsDataURL(f); });

    applyTheme();
    global.App = { store, api, qs, apiBase, token, me, logout, requireRole, ApiError, esc, money, fd, ft, fdt, iso, todayStr, initials, chip, STATUS, ROLE, POST_TYPE, PAY,
        toast, sheet, closeSheet, run, toggleTheme, debounce, fileToBase64, goLogin };
})(window);
