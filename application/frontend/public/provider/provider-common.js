/* =====================================================================
 * provider-common.js  —  lớp dùng chung cho giao diện Provider (mobile + PC)
 *
 *  - Gọi API FastAPI (TV2): đăng nhập JWT, studios, rooms, bookings, stats
 *  - Tự chuyển sang DỮ LIỆU DEMO khi chưa đăng nhập / backend chưa chạy,
 *    để giao diện vẫn xem và thao tác thử được
 *  - Dark mode (dùng chung key localStorage "provider_theme")
 *  - Toast, định dạng tiền / ngày, dựng sidebar + topbar cho bản PC
 *
 *  Đổi địa chỉ backend: sửa DEFAULT_API_BASE bên dưới, hoặc chạy trong console:
 *     localStorage.setItem('provider_api_base', 'http://192.168.1.10:8000')
 * ===================================================================== */
(function (global) {
    'use strict';

    const DEFAULT_API_BASE = 'http://127.0.0.1:8000';
    const KEY = {
        token: 'provider_token',
        user: 'provider_user',
        theme: 'provider_theme',
        api: 'provider_api_base',
        hidden: 'provider_hidden_rooms'
    };

    /* ---------- localStorage an toàn ---------- */
    const store = {
        get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
        set(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* bỏ qua */ } },
        del(k) { try { localStorage.removeItem(k); } catch (e) { /* bỏ qua */ } }
    };
    const readJSON = (k, fallback) => {
        try { return JSON.parse(store.get(k)) ?? fallback; } catch (e) { return fallback; }
    };

    /* ---------- Hằng số hiển thị ---------- */
    const ROOM_TYPES = { STUDIO: 'Studio chụp ảnh', DARKROOM: 'Phòng tối (Darkroom)' };
    const BOOKING_STATUS = {
        PENDING: { label: 'Chờ duyệt', cls: 'warn' },
        CONFIRMED: { label: 'Đã duyệt', cls: 'ok' },
        COMPLETED: { label: 'Hoàn thành', cls: 'info' },
        CANCELLED: { label: 'Đã hủy', cls: 'bad' }
    };
    const ROOM_STATUS = {
        AVAILABLE: { label: 'Hoạt động', cls: 'ok' },
        MAINTENANCE: { label: 'Bảo trì', cls: 'warn' },
        INACTIVE: { label: 'Đã ẩn', cls: 'muted' }
    };

    /* ---------- Dữ liệu DEMO (khi chưa có backend) ---------- */
    const iso = (dayOffset, h, m) => {
        const d = new Date(); d.setDate(d.getDate() + dayOffset); d.setHours(h, m || 0, 0, 0);
        const p = n => String(n).padStart(2, '0');
        return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}:00`;
    };
    const DEMO = {
        user: { user_id: 1, username: 'gia_an', email: 'provider.manager@filmpic.vn', phone: '0900000000', role: 'PROVIDER' },
        studios: [
            { studio_id: 1, provider_id: 1, name: 'Saigon Darkroom', address: '12 Lê Lợi, Quận 1', phone: '0900000001', avg_rating: 4.8, review_count: 38 },
            { studio_id: 2, provider_id: 1, name: 'Thảo Điền Studio', address: '45 Xuân Thủy, TP. Thủ Đức', phone: '0900000002', avg_rating: 4.7, review_count: 21 }
        ],
        rooms: [
            { room_id: 1, studio_id: 1, name: 'DARKROOM Q1', room_type: 'DARKROOM', capacity: 4, price_per_hour: 150000, description: 'Phòng tối tiêu chuẩn tráng/rọi ảnh đen trắng và màu.', status: 'AVAILABLE' },
            { room_id: 2, studio_id: 2, name: 'VINTAGE STUDIO THẢO ĐIỀN', room_type: 'STUDIO', capacity: 8, price_per_hour: 250000, description: 'Studio phông nền vintage, đèn Godox.', status: 'AVAILABLE' },
            { room_id: 3, studio_id: 1, name: 'AN PHÚ LAB Q2', room_type: 'DARKROOM', capacity: 3, price_per_hour: 180000, description: 'Lab tráng phim màu C41 và scan.', status: 'AVAILABLE' }
        ],
        bookings: [
            { reservation_id: 101, room_id: 1, customer_id: 11, customer_name: 'Bạch Dương', start_time: iso(0, 8), end_time: iso(0, 12), total_amount: 600000, customer_note: 'Hóa chất C41, máy rọi Kaiser, tank Paterson', status: 'PENDING' },
            { reservation_id: 102, room_id: 2, customer_id: 12, customer_name: 'Nguyễn Văn A', start_time: iso(1, 13, 30), end_time: iso(1, 16, 30), total_amount: 750000, customer_note: 'Thuê thêm 2 đèn Godox, phông nền trắng', status: 'PENDING' },
            { reservation_id: 103, room_id: 3, customer_id: 13, customer_name: 'Lê Minh', start_time: iso(2, 9), end_time: iso(2, 11), total_amount: 360000, customer_note: '', status: 'CONFIRMED' },
            { reservation_id: 104, room_id: 1, customer_id: 11, customer_name: 'Bạch Dương', start_time: iso(-3, 14), end_time: iso(-3, 17), total_amount: 450000, customer_note: '', status: 'COMPLETED' },
            { reservation_id: 105, room_id: 2, customer_id: 14, customer_name: 'Phạm Thu', start_time: iso(-5, 10), end_time: iso(-5, 12), total_amount: 500000, customer_note: 'Chụp lookbook', status: 'COMPLETED' },
            { reservation_id: 106, room_id: 3, customer_id: 15, customer_name: 'Hoàng Nam', start_time: iso(-7, 8), end_time: iso(-7, 10), total_amount: 360000, customer_note: '', status: 'CANCELLED' }
        ],
        revenueByMonth: [
            { label: 'T6', value: 7100000 }, { label: 'T7', value: 8200000 }, { label: 'T8', value: 9800000 },
            { label: 'T9', value: 10550000 }, { label: 'T10', value: 12450000 }
        ]
    };

    /* ---------- Trạng thái chế độ dữ liệu ---------- */
    // 'live' = đang dùng API thật; còn lại = demo (kèm lý do)
    const state = { mode: 'demo-nologin' };
    const isLive = () => state.mode === 'live';
    const MODE_TEXT = {
        'live': { cls: 'live', text: 'Đã kết nối Backend' },
        'demo-nologin': { cls: 'demo', text: 'Chế độ demo — chưa đăng nhập' },
        'demo-offline': { cls: 'demo', text: 'Chế độ demo — không kết nối được Backend' },
        'demo-expired': { cls: 'demo', text: 'Chế độ demo — phiên đăng nhập đã hết hạn' }
    };

    /* ---------- Định dạng ---------- */
    const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
    const money = n => (Number(n) || 0).toLocaleString('vi-VN') + ' đ';
    const moneyShort = n => {
        n = Number(n) || 0;
        return n >= 1e6 ? (n / 1e6).toFixed(1).replace('.0', '') + 'tr' : n >= 1e3 ? Math.round(n / 1e3) + 'k' : String(n);
    };
    const parseDate = s => new Date(s);
    const p2 = n => String(n).padStart(2, '0');
    const fmtDate = s => { const d = parseDate(s); return `${p2(d.getDate())}/${p2(d.getMonth() + 1)}/${d.getFullYear()}`; };
    const fmtTime = s => { const d = parseDate(s); return `${p2(d.getHours())}:${p2(d.getMinutes())}`; };
    const fmtRange = (a, b) => `${fmtDate(a)} • ${fmtTime(a)} - ${fmtTime(b)}`;
    const hoursBetween = (a, b) => Math.max(0, (parseDate(b) - parseDate(a)) / 36e5);
    const initials = name => {
        const parts = String(name || '?').trim().split(/\s+/);
        return ((parts[0][0] || '') + (parts.length > 1 ? parts[parts.length - 1][0] : '')).toUpperCase();
    };

    /* ---------- Toast ---------- */
    function toast(message, type) {
        let box = document.getElementById('pvToastBox');
        if (!box) {
            box = document.createElement('div');
            box.id = 'pvToastBox';
            box.style.cssText = 'position:fixed;top:16px;right:16px;z-index:9999;display:flex;flex-direction:column;gap:8px;max-width:340px;pointer-events:none;';
            document.body.appendChild(box);
        }
        const colors = { ok: '#16a34a', bad: '#dc2626', warn: '#d97706', info: '#0284c7' };
        const el = document.createElement('div');
        el.setAttribute('role', 'status');
        el.style.cssText = `background:${colors[type] || colors.info};color:#fff;padding:10px 14px;border-radius:10px;font:600 13px/1.4 -apple-system,'Segoe UI',Roboto,sans-serif;box-shadow:0 8px 20px rgba(0,0,0,.25);opacity:0;transform:translateY(-6px);transition:all .2s;`;
        el.textContent = message;
        box.appendChild(el);
        requestAnimationFrame(() => { el.style.opacity = '1'; el.style.transform = 'none'; });
        setTimeout(() => { el.style.opacity = '0'; setTimeout(() => el.remove(), 250); }, 3600);
    }

    /* ---------- Theme ---------- */
    function applyTheme() {
        document.body.classList.toggle('dark-mode', store.get(KEY.theme) === 'dark');
    }
    function toggleTheme() {
        const dark = !document.body.classList.contains('dark-mode');
        store.set(KEY.theme, dark ? 'dark' : 'light');
        applyTheme();
        document.dispatchEvent(new CustomEvent('provider:theme', { detail: { dark } }));
        return dark;
    }

    /* ---------- Auth ---------- */
    const apiBase = () => (store.get(KEY.api) || DEFAULT_API_BASE).replace(/\/+$/, '');
    const token = () => store.get(KEY.token);
    const currentUser = () => readJSON(KEY.user, null);
    function clearSession() { store.del(KEY.token); store.del(KEY.user); }
    function logout(goTo) { clearSession(); location.href = goTo || 'provider-login.html'; }
    function loginUrl() { return 'provider-login.html?next=' + encodeURIComponent(location.pathname.split('/').pop() + location.search); }
    function requireLogin() {
        if (token()) return true;
        toast('Bạn cần đăng nhập để thực hiện thao tác này', 'warn');
        setTimeout(() => { location.href = loginUrl(); }, 900);
        return false;
    }

    class ApiError extends Error {
        constructor(message, status, network) { super(message); this.status = status; this.network = !!network; }
    }

    // Gom thông báo lỗi của FastAPI (detail có thể là chuỗi hoặc mảng lỗi 422)
    function errorMessage(body, status) {
        const d = body && body.detail;
        if (typeof d === 'string') return d;
        if (Array.isArray(d)) return d.map(x => (x.loc ? x.loc.slice(1).join('.') + ': ' : '') + (x.msg || '')).join('; ');
        return `Lỗi máy chủ (HTTP ${status})`;
    }

    async function api(path, opts) {
        opts = opts || {};
        const headers = { 'Accept': 'application/json' };
        if (opts.body !== undefined) headers['Content-Type'] = 'application/json';
        if (opts.auth !== false && token()) headers['Authorization'] = 'Bearer ' + token();
        let res;
        try {
            res = await fetch(apiBase() + path, {
                method: opts.method || 'GET',
                headers,
                body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined
            });
        } catch (e) {
            throw new ApiError('Không thể kết nối tới Backend (' + apiBase() + ')', 0, true);
        }
        if (res.status === 204) return null;
        let body = null;
        try { body = await res.json(); } catch (e) { /* không có JSON */ }
        if (!res.ok) {
            // HTTPBearer của FastAPI trả 403 "Not authenticated" khi thiếu header
            throw new ApiError(errorMessage(body, res.status), res.status, false);
        }
        return body;
    }

    async function login(username, password) {
        const t = await api('/api/users/login', { method: 'POST', body: { username, password }, auth: false });
        store.set(KEY.token, t.access_token);
        let me;
        try { me = await api('/api/users/me'); } catch (e) { clearSession(); throw e; }
        const role = String(me.role || '').toUpperCase();
        if (role !== 'PROVIDER' && role !== 'ADMIN') {
            clearSession();
            throw new ApiError('Tài khoản này có vai trò ' + role + ', không phải PROVIDER hoặc ADMIN.', 403, false);
        }
        store.set(KEY.user, JSON.stringify(me));
        state.mode = 'live';
        return me;
    }

    /* Chạy gọi API thật; không đăng nhập / mất kết nối thì trả về demo. */
    async function withFallback(real, demo) {
        if (!token()) { state.mode = 'demo-nologin'; return demo(); }
        try {
            const r = await real();
            state.mode = 'live';
            return r;
        } catch (e) {
            if (e.status === 401) { clearSession(); state.mode = 'demo-expired'; return demo(); }
            if (e.network) { state.mode = 'demo-offline'; return demo(); }
            throw e;
        }
    }

    /* ---------- Lớp dữ liệu ---------- */
    const data = {
        async me() {
            return withFallback(async () => {
                const u = await api('/api/users/me'); store.set(KEY.user, JSON.stringify(u)); return u;
            }, () => DEMO.user);
        },

        // Studio của provider (ADMIN thấy tất cả)
        async studios() {
            return withFallback(async () => {
                const all = await api('/api/studios?limit=100');
                const u = currentUser();
                return u && String(u.role).toUpperCase() === 'PROVIDER'
                    ? all.filter(s => s.provider_id === u.user_id) : all;
            }, () => DEMO.studios);
        },
        async createStudio(payload) {
            if (!isLive()) {
                const s = Object.assign({ studio_id: Date.now() % 1e6, provider_id: DEMO.user.user_id, avg_rating: null, review_count: 0 }, payload);
                DEMO.studios.push(s); return s;
            }
            return api('/api/studios', { method: 'POST', body: payload });
        },

        // Phòng: API chỉ trả phòng AVAILABLE, nên phòng đã ẩn được ghi nhớ ở localStorage để còn "Hiện lại"
        async rooms(studios) {
            const list = await withFallback(async () => {
                const parts = await Promise.all((studios || []).map(s => api(`/api/rooms?studio_id=${s.studio_id}&limit=100`)));
                return [].concat(...parts);
            }, () => DEMO.rooms);
            if (!isLive()) return list;
            const ids = new Set(list.map(r => r.room_id));
            const mine = new Set((studios || []).map(s => s.studio_id));
            const hidden = readJSON(KEY.hidden, []).filter(r => !ids.has(r.room_id) && mine.has(r.studio_id));
            return list.concat(hidden);
        },
        async saveRoom(id, payload) {
            if (!isLive()) {
                if (id) { const r = DEMO.rooms.find(x => x.room_id === Number(id)); Object.assign(r, payload); return r; }
                const r = Object.assign({ room_id: Date.now() % 1e6, status: 'AVAILABLE' }, payload);
                DEMO.rooms.push(r); return r;
            }
            if (id) {
                const { studio_id, ...patch } = payload; // PATCH không nhận studio_id
                return api('/api/rooms/' + id, { method: 'PATCH', body: patch });
            }
            return api('/api/rooms', { method: 'POST', body: payload });
        },
        async setRoomStatus(room, status) {
            if (!isLive()) { const r = DEMO.rooms.find(x => x.room_id === room.room_id); if (r) r.status = status; return r; }
            const updated = await api('/api/rooms/' + room.room_id, { method: 'PATCH', body: { status } });
            let hidden = readJSON(KEY.hidden, []).filter(r => r.room_id !== room.room_id);
            if (status === 'INACTIVE') hidden.push(Object.assign({}, room, { status: 'INACTIVE' }));
            store.set(KEY.hidden, JSON.stringify(hidden));
            return updated;
        },

        // Lưu ý: GET /api/bookings của backend hiện chỉ trả đơn do CHÍNH tài khoản đó đặt
        async bookings(status) {
            return withFallback(
                () => api('/api/bookings?limit=100' + (status ? '&status=' + status : '')),
                () => DEMO.bookings.filter(b => !status || b.status === status)
            );
        },
        async setBookingStatus(id, status) {
            if (!isLive()) { const b = DEMO.bookings.find(x => x.reservation_id === id); if (b) b.status = status; return b; }
            return api(`/api/bookings/${id}/status`, { method: 'PATCH', body: { status } });
        },

        // Thống kê tổng (chỉ ADMIN). PROVIDER sẽ nhận 403 -> trả null để trang tự tính từ dữ liệu có sẵn
        async stats() {
            if (!isLive()) return null;
            try { return await api('/api/stats/summary'); } catch (e) { return null; }
        },
        revenueByMonth() { return DEMO.revenueByMonth; }
    };

    /* ---------- Giao diện PC: sidebar + topbar ---------- */
    const PC_NAV = [
        { key: 'dashboard', icon: '📊', label: 'Tổng quan', href: 'provider-pc-dashboard.html' },
        { key: 'bookings', icon: '📅', label: 'Lịch đặt', href: 'provider-pc-bookings.html' },
        { key: 'rooms', icon: '🧪', label: 'Phòng & Studio', href: 'provider-pc-rooms.html' },
        { key: 'profile', icon: '👤', label: 'Hồ sơ & Bảo mật', href: 'provider-pc-profile.html' }
    ];

    async function mountPC(activeKey, title) {
        applyTheme();
        const side = document.getElementById('pcSidebar');
        const top = document.getElementById('pcTopbar');
        if (side) {
            side.innerHTML = `
                <div class="pc-brand"><span class="pc-brand-logo">🎞️</span><div><strong>Provider Hub</strong><small>Film Photography</small></div></div>
                <nav class="pc-nav" aria-label="Điều hướng chính">
                    ${PC_NAV.map(n => `<a href="${n.href}" class="pc-nav-item${n.key === activeKey ? ' active' : ''}"${n.key === activeKey ? ' aria-current="page"' : ''}><span>${n.icon}</span>${n.label}</a>`).join('')}
                </nav>
                <div class="pc-side-foot">
                    <a href="provider-index.html" class="pc-nav-item"><span>📱</span>Bản mobile</a>
                </div>`;
        }
        if (top) {
            top.innerHTML = `
                <h1 class="pc-title">${esc(title)}</h1>
                <div class="pc-top-right">
                    <span class="mode-badge" id="modeBadge"></span>
                    <button class="icon-btn" id="themeBtn" title="Đổi giao diện sáng / tối" aria-label="Đổi giao diện sáng hoặc tối">🌓</button>
                    <div class="pc-user" id="pcUser"><div class="avatar">--</div><div><strong>...</strong><small>...</small></div></div>
                    <a class="btn btn-ghost" id="authBtn" href="#">Đăng nhập</a>
                </div>`;
            document.getElementById('themeBtn').onclick = toggleTheme;
        }
        const me = await data.me().catch(() => DEMO.user);
        refreshChrome(me);
        return me;
    }

    // Cập nhật badge chế độ + thông tin user + nút đăng nhập/xuất
    function refreshChrome(me) {
        const badge = document.getElementById('modeBadge');
        if (badge) { const m = MODE_TEXT[state.mode]; badge.className = 'mode-badge ' + m.cls; badge.textContent = '● ' + m.text; }
        const u = document.getElementById('pcUser');
        if (u && me) u.innerHTML = `<div class="avatar">${esc(initials(me.username))}</div><div><strong>${esc(me.username)}</strong><small>${esc(me.role)}</small></div>`;
        const btn = document.getElementById('authBtn');
        if (btn) {
            if (token()) { btn.textContent = 'Đăng xuất'; btn.href = '#'; btn.onclick = e => { e.preventDefault(); logout(); }; }
            else { btn.textContent = 'Đăng nhập'; btn.href = loginUrl(); btn.onclick = null; }
        }
    }

    /* ---------- Nút chuyển sang bản PC trên các trang mobile ---------- */
    function addPcShortcut(pcHref) {
        if (!pcHref || document.getElementById('pvPcShortcut')) return;
        const a = document.createElement('a');
        a.id = 'pvPcShortcut'; a.href = pcHref; a.textContent = '🖥️ Mở bản PC';
        a.style.cssText = 'position:fixed;top:14px;right:14px;z-index:50;background:#0284c7;color:#fff;padding:8px 14px;border-radius:999px;font:700 12px -apple-system,Segoe UI,sans-serif;text-decoration:none;box-shadow:0 6px 16px rgba(2,132,199,.35);';
        const mq = window.matchMedia('(min-width: 1000px)');
        const sync = () => { a.style.display = mq.matches ? 'block' : 'none'; };
        sync(); (mq.addEventListener ? mq.addEventListener('change', sync) : mq.addListener(sync));
        document.body.appendChild(a);
    }

    global.Provider = {
        KEY, DEMO, ROOM_TYPES, BOOKING_STATUS, ROOM_STATUS, state, isLive,
        store, esc, money, moneyShort, fmtDate, fmtTime, fmtRange, hoursBetween, initials,
        toast, applyTheme, toggleTheme,
        apiBase, token, currentUser, login, logout, loginUrl, requireLogin, api, ApiError,
        data, mountPC, refreshChrome, addPcShortcut
    };
})(window);
