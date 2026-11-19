/* =====================================================================
 * provider-common.js  —  lớp dùng chung cho giao diện Provider (mobile + PC)
 *
 *  - Gọi API FastAPI (/api/users, /api/provider/...): đăng nhập JWT, studio, phòng, đơn đặt, thiết bị, thống kê
 *  - Tự chuyển sang DỮ LIỆU DEMO khi chưa đăng nhập / backend chưa chạy,
 *    để giao diện vẫn xem và thao tác thử được
 *  - Dark mode (dùng chung key localStorage "provider_theme")
 *  - Toast, định dạng tiền / ngày, dựng sidebar + topbar cho bản PC
 *
 *  Địa chỉ backend: mở trang qua backend (http://localhost:8000/web/provider/...) thì tự dùng cùng origin.
 *  Mở file trực tiếp / dùng server khác thì nhập địa chỉ ở trang đăng nhập, hoặc chạy trong console:
 *     localStorage.setItem('provider_api_base', 'http://192.168.1.10:8000')
 * ===================================================================== */
(function (global) {
    'use strict';

    // Phục vụ bởi chính backend (/web/...) -> gọi cùng origin; ngược lại mặc định cổng 8000
    const SAME_ORIGIN = /^https?:$/.test(location.protocol) && location.pathname.indexOf('/web/') === 0;
    const DEFAULT_API_BASE = SAME_ORIGIN ? '' : 'http://127.0.0.1:8000';
    // Toàn bộ đường dẫn API gom một chỗ: Backend đổi route chỉ cần sửa ở đây.
    // Đăng nhập dùng /api/users/* (backend hiện có); phần còn lại là /api/provider/* (xem docs/PROVIDER_API.md).
    const EP = {
        login: '/api/users/login', me: '/api/users/me', changePassword: '/api/users/change-password',
        overview: '/api/provider/overview', studios: '/api/provider/studios', rooms: '/api/provider/rooms',
        bookings: '/api/provider/bookings', checkin: '/api/provider/bookings/checkin',
        equipment: '/api/provider/equipment', packages: '/api/provider/packages', reviews: '/api/provider/reviews',
        disputes: '/api/provider/disputes', workshops: '/api/provider/workshops'
    };

    const KEY = {
        token: 'provider_token',
        user: 'provider_user',
        theme: 'provider_theme',
        api: 'provider_api_base',
        avatar: 'provider_avatar_', // + user_id: ảnh đại diện (data URL) lưu theo từng tài khoản trên trình duyệt này
        hidden: 'provider_hidden_rooms' // không còn dùng (API trả cả phòng đã ẩn)
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
        IN_USE: { label: 'Đang sử dụng', cls: 'info' },
        COMPLETED: { label: 'Hoàn thành', cls: 'info' },
        CANCELLED: { label: 'Đã hủy', cls: 'bad' }
    };
    const ROOM_STATUS = {
        AVAILABLE: { label: 'Hoạt động', cls: 'ok' },
        MAINTENANCE: { label: 'Bảo trì', cls: 'warn' },
        INACTIVE: { label: 'Đã ẩn', cls: 'muted' }
    };

    const PAYMENT_STATUS = {
        SUCCESS: { label: 'Thành công', cls: 'ok' }, PENDING: { label: 'Chờ thanh toán', cls: 'warn' },
        FAILED: { label: 'Thất bại', cls: 'bad' }, REFUNDED: { label: 'Đã hoàn tiền', cls: 'info' }
    };
    const PAYMENT_METHOD = { CASH: 'Tiền mặt', BANK_TRANSFER: 'Chuyển khoản', VNPAY: 'VNPay', MOMO: 'MoMo', STRIPE: 'Thẻ (Stripe)' };

    const EQUIPMENT_CATEGORY = {
        CAMERA: 'Máy ảnh', LENS: 'Ống kính', LIGHTING: 'Đèn', TRIPOD: 'Chân máy', ENLARGER: 'Máy phóng',
        SCANNER: 'Máy scan', CHEMICAL: 'Hóa chất', PAPER: 'Giấy ảnh', OTHER: 'Khác'
    };
    const EQUIPMENT_STATUS = {
        GOOD: { label: 'Tốt', cls: 'ok' },
        NEEDS_MAINTENANCE: { label: 'Cần bảo trì', cls: 'warn' },
        UNDER_MAINTENANCE: { label: 'Đang bảo trì', cls: 'warn' },
        BROKEN: { label: 'Hỏng', cls: 'bad' },
        RETIRED: { label: 'Đã thanh lý', cls: 'muted' }
    };
    const DISPUTE_STATUS = {
        OPEN: { label: 'Mới', cls: 'warn' }, IN_REVIEW: { label: 'Đang xem xét', cls: 'info' },
        RESOLVED: { label: 'Đã giải quyết', cls: 'ok' }, REJECTED: { label: 'Bị bác bỏ', cls: 'muted' }
    };
    const WORKSHOP_STATUS = {
        OPEN: { label: 'Đang mở đăng ký', cls: 'ok' }, CLOSED: { label: 'Đã đóng đăng ký', cls: 'warn' },
        CANCELLED: { label: 'Đã hủy', cls: 'bad' }, COMPLETED: { label: 'Đã diễn ra', cls: 'muted' }
    };
    const STUDIO_STATUS = {
        PENDING: { label: 'Chờ duyệt', cls: 'warn' },
        APPROVED: { label: 'Đã duyệt', cls: 'ok' },
        REJECTED: { label: 'Bị từ chối', cls: 'bad' },
        SUSPENDED: { label: 'Tạm khóa', cls: 'bad' }
    };

    /* ---------- Dữ liệu DEMO (khi chưa có backend) ---------- */
    const iso = (dayOffset, h, m) => {
        const d = new Date(); d.setDate(d.getDate() + dayOffset); d.setHours(h, m || 0, 0, 0);
        const p = n => String(n).padStart(2, '0');
        return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}:00`;
    };
    // Dữ liệu demo lấy theo database/02_seed_data.sql (nhà cung cấp provider1 = Phạm Gia Huy, studio "Silver Grain Studio").
    const dayISO = n => new Date(Date.now() + n * 864e5).toISOString().slice(0, 10);
    const SG = { studio_id: 1, studio_name: 'Silver Grain Studio' };
    const DEMO = {
        user: { user_id: 5, username: 'provider1', full_name: 'Phạm Gia Huy', email: 'provider1@filmplatform.vn', phone: '0900000005', role: 'PROVIDER', status: 'ACTIVE' },
        studios: [
            { studio_id: 1, provider_id: 5, name: 'Silver Grain Studio', address: '12 Nguyễn Huệ, Quận 1', city: 'TP.HCM', phone: '0281111111', description: 'Studio chụp phim phong cách vintage, ánh sáng tự nhiên.', open_time: '08:00:00', close_time: '21:00:00', status: 'APPROVED', avg_rating: 4.4, review_count: 8, room_count: 3 }
        ],
        // Giá phòng = giá gốc + (studio_id % 3) * 20.000 (đúng công thức trong seed)
        rooms: [
            { room_id: 1, ...SG, city: 'TP.HCM', name: 'Phòng chụp Vintage', room_type: 'STUDIO', capacity: 6, area_sqm: 35, art_style: 'Vintage', lighting: 'Softbox + cửa sổ ánh sáng tự nhiên', amenities: 'Phông nền, ghế, bàn trang điểm', price_per_hour: 270000, description: 'Không gian hoài cổ, hợp chụp chân dung phim.', status: 'AVAILABLE' },
            { room_id: 2, ...SG, city: 'TP.HCM', name: 'Phòng chụp Minimal', room_type: 'STUDIO', capacity: 4, area_sqm: 25, art_style: 'Minimal', lighting: 'Đèn LED liên tục', amenities: 'Phông trắng, hộp sáng', price_per_hour: 240000, description: 'Phòng tối giản, phù hợp chụp sản phẩm.', status: 'AVAILABLE' },
            { room_id: 3, ...SG, city: 'TP.HCM', name: 'Phòng tối B&W', room_type: 'DARKROOM', capacity: 3, area_sqm: 15, art_style: 'Truyền thống', lighting: 'Đèn an toàn màu đỏ', amenities: 'Bồn rửa, kẹp phơi, máy phóng ảnh', price_per_hour: 200000, description: 'Phòng tối tráng phim và in ảnh đen trắng.', status: 'AVAILABLE' }
        ],
        bookings: [],   // dựng ở seedDemo() bên dưới
        // 8 loại thiết bị mỗi studio; thiết bị REUSABLE có lịch bảo trì 20-110 ngày tới
        equipment: [
            { equipment_id: 1, ...SG, name: 'Máy ảnh phim Pentax K1000', equipment_type: 'REUSABLE', category: 'CAMERA', quantity: 6, rental_price: 120000, next_maintenance_date: dayISO(28), status: 'GOOD' },
            { equipment_id: 2, ...SG, name: 'Ống kính 50mm f/1.4', equipment_type: 'REUSABLE', category: 'LENS', quantity: 6, rental_price: 80000, next_maintenance_date: dayISO(39), status: 'GOOD' },
            { equipment_id: 3, ...SG, name: 'Đèn flash Godox', equipment_type: 'REUSABLE', category: 'LIGHTING', quantity: 6, rental_price: 60000, next_maintenance_date: dayISO(50), status: 'GOOD' },
            { equipment_id: 4, ...SG, name: 'Chân máy Manfrotto', equipment_type: 'REUSABLE', category: 'TRIPOD', quantity: 6, rental_price: 40000, next_maintenance_date: dayISO(61), status: 'GOOD' },
            { equipment_id: 5, ...SG, name: 'Máy phóng ảnh (enlarger)', equipment_type: 'REUSABLE', category: 'ENLARGER', quantity: 3, rental_price: 150000, next_maintenance_date: dayISO(72), status: 'GOOD' },
            { equipment_id: 6, ...SG, name: 'Máy scan phim Epson V600', equipment_type: 'REUSABLE', category: 'SCANNER', quantity: 3, rental_price: 100000, next_maintenance_date: dayISO(83), status: 'GOOD' },
            { equipment_id: 7, ...SG, name: 'Hóa chất tráng phim B&W', equipment_type: 'CONSUMABLE', category: 'CHEMICAL', quantity: 6, rental_price: 50000, next_maintenance_date: null, status: 'GOOD' },
            { equipment_id: 8, ...SG, name: 'Giấy in ảnh 8x10', equipment_type: 'CONSUMABLE', category: 'PAPER', quantity: 200, rental_price: 8000, next_maintenance_date: null, status: 'GOOD' }
        ],
        packages: [
            { package_id: 1, ...SG, name: 'Gói Chân dung', price: 650000, duration_hours: 3, room_type: 'STUDIO', instructor_name: 'Nguyễn Minh Khoa', description: 'Chụp chân dung phim kèm máy ảnh, ống kính, đèn.', is_active: true,
              equipment: [{ equipment_id: 1, name: 'Máy ảnh phim Pentax K1000', quantity_included: 1 }, { equipment_id: 2, name: 'Ống kính 50mm f/1.4', quantity_included: 1 }, { equipment_id: 3, name: 'Đèn flash Godox', quantity_included: 2 }, { equipment_id: 4, name: 'Chân máy Manfrotto', quantity_included: 1 }] },
            { package_id: 2, ...SG, name: 'Gói Sản phẩm', price: 550000, duration_hours: 2, room_type: 'STUDIO', instructor_name: 'Trần Thu Hà', description: 'Chụp sản phẩm với bộ đèn và chân máy.', is_active: true,
              equipment: [{ equipment_id: 1, name: 'Máy ảnh phim Pentax K1000', quantity_included: 1 }, { equipment_id: 3, name: 'Đèn flash Godox', quantity_included: 2 }, { equipment_id: 4, name: 'Chân máy Manfrotto', quantity_included: 1 }] },
            { package_id: 3, ...SG, name: 'Gói Tráng phim & In ảnh', price: 450000, duration_hours: 3, room_type: 'DARKROOM', instructor_name: 'Lê Quốc Bảo', description: 'Hướng dẫn tráng phim, in ảnh đen trắng trong phòng tối.', is_active: true,
              equipment: [{ equipment_id: 5, name: 'Máy phóng ảnh (enlarger)', quantity_included: 1 }, { equipment_id: 7, name: 'Hóa chất tráng phim B&W', quantity_included: 2 }, { equipment_id: 8, name: 'Giấy in ảnh 8x10', quantity_included: 10 }] }
        ],
        reviews: [
            { review_id: 1, reservation_id: 105, studio_id: 1, studio_name: 'Silver Grain Studio', customer_id: 29, customer_name: 'Khách hàng số 9', rating: 5, comment: 'Phòng sạch, ánh sáng đẹp, chủ studio hỗ trợ nhiệt tình. Sẽ quay lại!', created_at: iso(-4, 9) },
            { review_id: 2, reservation_id: 90, studio_id: 1, studio_name: 'Silver Grain Studio', customer_id: 24, customer_name: 'Khách hàng số 4', rating: 4, comment: 'Thiết bị đầy đủ, chỉ hơi chật khi đi nhóm 6 người.', created_at: iso(-12, 15) },
            { review_id: 3, reservation_id: 84, studio_id: 1, studio_name: 'Silver Grain Studio', customer_id: 31, customer_name: 'Khách hàng số 11', rating: 3, comment: 'Đèn flash bị yếu, mong studio kiểm tra lại.', created_at: iso(-20, 11) },
            { review_id: 4, reservation_id: 77, studio_id: 1, studio_name: 'Silver Grain Studio', customer_id: 27, customer_name: 'Khách hàng số 7', rating: 5, comment: null, created_at: iso(-31, 18) }
        ],
        // Khiếu nại gắn với đơn đặt (bảng Disputes); provider tiếp nhận / phản hồi
        disputes: [
            { dispute_id: 1, reservation_id: 106, raised_by: 36, raised_by_name: 'Khách hàng số 16', reason: 'Đơn bị hủy sát giờ nhưng tôi chưa nhận được tiền hoàn.', status: 'OPEN', resolution: null, created_at: iso(-6, 10), resolved_at: null, room_name: 'Phòng tối B&W', studio_id: 1, studio_name: 'Silver Grain Studio' },
            { dispute_id: 2, reservation_id: 105, raised_by: 29, raised_by_name: 'Khách hàng số 9', reason: 'Tôi bị tính thêm 1 giờ dù check-out đúng giờ.', status: 'IN_REVIEW', resolution: null, created_at: iso(-3, 14), resolved_at: null, room_name: 'Phòng chụp Minimal', studio_id: 1, studio_name: 'Silver Grain Studio' }
        ],
        // Workshop do chuyên gia tổ chức tại cơ sở của provider (chỉ xem)
        workshops: [
            { workshop_id: 1, title: 'In ảnh phòng tối cho người mới', description: 'Học tráng phim và in ảnh đen trắng từ đầu.', expert_id: 3, expert_name: 'Lê Quốc Bảo', studio_id: 1, studio_name: 'Silver Grain Studio', capacity: 12, registered: 8, fee: 250000, start_time: iso(4, 14), end_time: iso(4, 17), status: 'OPEN' },
            { workshop_id: 2, title: 'Chân dung ánh sáng tự nhiên với phim', description: null, expert_id: 4, expert_name: 'Nguyễn Minh Khoa', studio_id: 1, studio_name: 'Silver Grain Studio', capacity: 10, registered: 10, fee: 300000, start_time: iso(11, 9), end_time: iso(11, 12), status: 'CLOSED' },
            { workshop_id: 3, title: 'Review máy ảnh phim cũ', description: null, expert_id: 3, expert_name: 'Lê Quốc Bảo', studio_id: 1, studio_name: 'Silver Grain Studio', capacity: 15, registered: 15, fee: 0, start_time: iso(-9, 15), end_time: iso(-9, 17), status: 'COMPLETED' }
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
    // Tên hiển thị: ưu tiên họ tên, chưa có thì dùng username
    const displayName = me => String((me && (me.full_name || me.username)) || '').trim() || 'Người dùng';
    // Chữ cái trên avatar: "An" -> "A", "Phạm Gia Huy" -> "PH"
    const initials = name => {
        const parts = String(name || '?').trim().split(/\s+/).filter(Boolean);
        if (!parts.length) return '?';
        return Array.from((parts[0][0] || '') + (parts.length > 1 ? parts[parts.length - 1][0] : '')).join('').toUpperCase();
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
        const t = await api(EP.login, { method: 'POST', body: { username, password }, auth: false });
        store.set(KEY.token, t.access_token);                       // cần token để gọi /me
        let me = t.user;
        try { if (!me) me = await api(EP.me); } catch (e) { clearSession(); throw e; }
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
    const demoId = () => Date.now() % 1e6;

    // Dựng dữ liệu demo cho đơn đặt (mô phỏng view vw_ReservationDetail + các bảng liên quan)
    const isoNow = min => { const d = new Date(Date.now() + min * 60000); return iso(0, d.getHours(), d.getMinutes()); };
    function demoCalc(b) {
        const room = DEMO.rooms.find(r => r.room_id === b.room_id);
        b.total_amount = hoursBetween(b.start_time, b.end_time) * (room ? room.price_per_hour : 0)
            + b.equipment.reduce((s, e) => s + e.quantity * e.unit_price, 0) + b.packages.reduce((s, p) => s + p.price, 0);
        b.paid_amount = b.payments.filter(p => p.status === 'SUCCESS').reduce((s, p) => s + p.amount, 0);
        b.balance_due = b.total_amount - b.paid_amount;
        return b;
    }
    function demoHist(b, to) { b.history.push({ old_status: b.status, new_status: to, changed_at: new Date().toISOString(), changed_by_name: DEMO.user.username }); }
    const demoCopy = b => JSON.parse(JSON.stringify(demoCalc(b)));
    const demoFind = id => { const b = DEMO.bookings.find(x => x.reservation_id === Number(id)); if (!b) throw new ApiError('Không tìm thấy đơn.', 404); return b; };
    (function seedDemo() {
        const room = id => DEMO.rooms.find(r => r.room_id === id);
        const eq = (id, quantity) => { const e = DEMO.equipment.find(x => x.equipment_id === id); return { equipment_id: id, name: e.name, quantity, unit_price: e.rental_price }; };
        const pk = id => { const p = DEMO.packages.find(x => x.package_id === id); return { package_id: id, name: p.name, price: p.price, notes: null }; };
        const mk = (id, room_id, n, start, end, status, extra) => {
            const r = room(room_id), name = 'Khách hàng số ' + n;
            return demoCalc(Object.assign({
                reservation_id: id, room_id, room_name: r.name, studio_id: r.studio_id, studio_name: r.studio_name,
                customer_id: 20 + n, customer_name: name, customer: 'customer' + String(n).padStart(3, '0'),
                customer_phone: '0912' + String(n * 1234).padStart(6, '0'), start_time: start, end_time: end,
                customer_note: '', qr_code: null, status, equipment: [], packages: [], payments: [], history: [], session: null
            }, extra));
        };
        const pay = (amount, method, status, code) => ({ payment_id: demoId() + amount % 997, amount, payment_method: method, transaction_code: code || null, status: status || 'SUCCESS', paid_at: status === 'PENDING' ? null : new Date().toISOString() });
        DEMO.bookings = [
            // PENDING: khách chưa thanh toán xong (giao dịch MOMO đang chờ)
            mk(101, 1, 7, iso(1, 9), iso(1, 12), 'PENDING', { customer_note: 'Nhờ chuẩn bị sẵn phông nền và ghế.', payments: [pay(810000, 'MOMO', 'PENDING', 'TXN00101D')] }),
            mk(102, 2, 14, iso(2, 12), iso(2, 14), 'PENDING', { equipment: [eq(1, 1)] }),
            // CONFIRMED sắp đến giờ (10 phút nữa) để thử check-in bằng QR; khách mới đặt cọc 50%
            mk(103, 3, 3, isoNow(10), isoNow(130), 'CONFIRMED', { qr_code: 'QR-00103-482915', packages: [pk(3)], payments: [pay(425000, 'VNPAY', 'SUCCESS', 'TXN00103B')] }),
            // CONFIRMED để xa (thử check-in sớm bị từ chối)
            mk(107, 1, 11, iso(3, 9), iso(3, 11), 'CONFIRMED', { qr_code: 'QR-00107-660318', payments: [pay(540000, 'BANK_TRANSFER', 'SUCCESS', 'TXN00107B')] }),
            // IN_USE: đã check-in, trả đủ
            mk(104, 1, 5, isoNow(-85), isoNow(95), 'IN_USE', { qr_code: 'QR-00104-771204', packages: [pk(1)], payments: [pay(1460000, 'STRIPE', 'SUCCESS', 'TXN00104A')], session: { checkin_time: new Date(Date.now() - 90 * 60000).toISOString(), checkout_time: null, actual_minutes: null } }),
            // COMPLETED
            mk(105, 2, 9, iso(-5, 10), iso(-5, 12), 'COMPLETED', { equipment: [eq(1, 1)], qr_code: 'QR-00105-120331', payments: [pay(600000, 'BANK_TRANSFER', 'SUCCESS', 'TXN00105A')], session: { checkin_time: iso(-5, 9, 55), checkout_time: iso(-5, 12, 10), actual_minutes: 135 } }),
            // CANCELLED: đã hoàn tiền
            mk(106, 3, 16, iso(-7, 9), iso(-7, 11), 'CANCELLED', { payments: [pay(400000, 'VNPAY', 'REFUNDED', 'TXN00106C')] })
        ];
        DEMO.bookings.forEach(b => {
            const created = iso(-9, 9), confirmed = iso(-9, 11);
            b.history.push({ old_status: null, new_status: 'PENDING', changed_at: created, changed_by_name: b.customer });
            if (['CONFIRMED', 'IN_USE', 'COMPLETED'].includes(b.status)) b.history.push({ old_status: 'PENDING', new_status: 'CONFIRMED', changed_at: confirmed, changed_by_name: DEMO.user.username });
            if (['IN_USE', 'COMPLETED'].includes(b.status)) b.history.push({ old_status: 'CONFIRMED', new_status: 'IN_USE', changed_at: b.session.checkin_time, changed_by_name: b.customer });
            if (b.status === 'COMPLETED') b.history.push({ old_status: 'IN_USE', new_status: 'COMPLETED', changed_at: b.session.checkout_time, changed_by_name: b.customer });
            if (b.status === 'CANCELLED') b.history.push({ old_status: 'PENDING', new_status: 'CANCELLED', changed_at: confirmed, changed_by_name: b.customer });
            demoCalc(b);
        });
    })();

    const qs = o => {
        const p = Object.entries(o || {}).filter(([, v]) => v !== undefined && v !== null && v !== '')
            .map(([k, v]) => encodeURIComponent(k) + '=' + encodeURIComponent(v));
        return p.length ? '?' + p.join('&') : '';
    };
    const demoOverview = () => {
        const done = DEMO.bookings.filter(b => ['CONFIRMED', 'IN_USE', 'COMPLETED'].includes(b.status));
        const byRoom = {};
        done.forEach(b => { const r = byRoom[b.room_id] || (byRoom[b.room_id] = { room_id: b.room_id, room_name: b.room_name, studio_name: b.studio_name, bookings: 0, revenue: 0 }); r.bookings++; r.revenue += b.total_amount; });
        const now = new Date(), vals = [3150000, 4020000, 4870000, 5390000, 6240000];
        const months = vals.map((v, i) => { const d = new Date(now.getFullYear(), now.getMonth() - (vals.length - i), 1); return { month: d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0'), revenue: v, bookings: 7 + i }; });
        const paid = DEMO.bookings.reduce((s, b) => s + (b.paid_amount || 0), 0);
        months.push({ month: now.getFullYear() + '-' + String(now.getMonth() + 1).padStart(2, '0'), revenue: paid, bookings: DEMO.bookings.length });
        const st = DEMO.studios[0];
        return {
            studio_count: DEMO.studios.length,
            room_count: DEMO.rooms.filter(r => r.status !== 'INACTIVE').length,
            equipment_count: DEMO.equipment.filter(e => e.status !== 'RETIRED').length,
            total_bookings: DEMO.bookings.length,
            pending_bookings: DEMO.bookings.filter(b => b.status === 'PENDING').length,
            upcoming_bookings: DEMO.bookings.filter(b => ['PENDING', 'CONFIRMED'].includes(b.status) && new Date(b.start_time) >= now).length,
            revenue_total: paid + vals.reduce((a, c) => a + c, 0),
            revenue_this_month: paid,
            avg_rating: st.avg_rating, review_count: st.review_count,
            revenue_by_month: months,
            top_rooms: Object.values(byRoom).sort((a, b) => b.revenue - a.revenue).slice(0, 5)
        };
    };

    const data = {
        async me() {
            return withFallback(async () => {
                const u = await api(EP.me); store.set(KEY.user, JSON.stringify(u)); return u;
            }, () => DEMO.user);
        },
        async updateProfile(payload) {
            if (!isLive()) { Object.assign(DEMO.user, payload); announceUser(DEMO.user); return DEMO.user; }
            const u = await api(EP.me, { method: 'PATCH', body: payload });
            store.set(KEY.user, JSON.stringify(u)); announceUser(u); return u;
        },
        async changePassword(current_password, new_password) {
            if (!isLive()) return null;
            return api(EP.changePassword, { method: 'POST', body: { current_password, new_password } });
        },

        // Studio của tôi (ADMIN thấy tất cả), kể cả studio đang chờ duyệt
        async studios() {
            return withFallback(() => api(EP.studios), () => DEMO.studios);
        },
        async saveStudio(id, payload) {
            if (!isLive()) {
                if (id) { const s = DEMO.studios.find(x => x.studio_id === Number(id)); Object.assign(s, payload); return s; }
                const s = Object.assign({ studio_id: demoId(), provider_id: DEMO.user.user_id, status: 'PENDING', avg_rating: null, review_count: 0, room_count: 0 }, payload);
                DEMO.studios.push(s); return s;
            }
            return id ? api(EP.studios + '/' + id, { method: 'PATCH', body: payload })
                      : api(EP.studios, { method: 'POST', body: payload });
        },
        createStudio(payload) { return data.saveStudio(null, payload); },
        // Xóa cơ sở: backend từ chối (409) nếu đã có đơn đặt phòng / workshop
        async deleteStudio(id) {
            if (!isLive()) {
                id = Number(id);
                const roomIds = DEMO.rooms.filter(r => r.studio_id === id).map(r => r.room_id);
                if (DEMO.bookings.some(b => roomIds.includes(b.room_id)))
                    throw new ApiError('Cơ sở đã có đơn đặt phòng nên không thể xóa. Hãy ẩn các phòng của cơ sở này thay vì xóa.', 409);
                DEMO.rooms = DEMO.rooms.filter(r => r.studio_id !== id);
                DEMO.equipment = DEMO.equipment.filter(e => e.studio_id !== id);
                DEMO.packages = DEMO.packages.filter(p => p.studio_id !== id);
                DEMO.studios = DEMO.studios.filter(s => s.studio_id !== id);
                return null;
            }
            return api(EP.studios + '/' + id, { method: 'DELETE' });
        },

        // Phòng: API provider trả mọi trạng thái (AVAILABLE / MAINTENANCE / INACTIVE)
        async rooms() {
            return withFallback(() => api(EP.rooms), () => DEMO.rooms);
        },
        async saveRoom(id, payload) {
            if (!isLive()) {
                if (id) { const r = DEMO.rooms.find(x => x.room_id === Number(id)); Object.assign(r, payload); return r; }
                const st = DEMO.studios.find(x => x.studio_id === Number(payload.studio_id));
                const r = Object.assign({ room_id: demoId(), status: 'AVAILABLE', studio_name: st && st.name, city: st && st.city }, payload);
                DEMO.rooms.push(r); return r;
            }
            if (id) {
                const { studio_id, ...patch } = payload; // PATCH không nhận studio_id
                return api(EP.rooms + '/' + id, { method: 'PATCH', body: patch });
            }
            return api(EP.rooms, { method: 'POST', body: payload });
        },
        async setRoomStatus(room, status) {
            if (!isLive()) { const r = DEMO.rooms.find(x => x.room_id === room.room_id); if (r) r.status = status; return r; }
            return api(EP.rooms + '/' + room.room_id, { method: 'PATCH', body: { status } });
        },

        // ---- Đơn đặt vào phòng của tôi (luồng theo stored procedure của CSDL) ----
        async bookings(status, extra) {
            return withFallback(
                () => api(EP.bookings + qs(Object.assign({ limit: 100, status }, extra))),
                () => DEMO.bookings.filter(b => !status || b.status === status).map(demoCopy)
            );
        },
        // Chi tiết: thiết bị, gói, thanh toán, lịch sử trạng thái (trigger), phiên sử dụng (check-in/out)
        async booking(id) {
            if (!isLive()) return demoCopy(demoFind(id));
            return api(`${EP.bookings}/${id}`);
        },
        // sp_ConfirmReservation: PENDING -> CONFIRMED, sinh qr_code
        async confirmBooking(id) {
            if (!isLive()) {
                const b = demoFind(id);
                if (b.status !== 'PENDING') throw new ApiError('Chỉ xác nhận được đơn đang PENDING.', 409);
                demoHist(b, 'CONFIRMED'); b.status = 'CONFIRMED';
                b.qr_code = 'QR-' + String(b.reservation_id).padStart(5, '0') + '-' + (100000 + Math.floor(Math.random() * 899999));
                return demoCopy(b);
            }
            return api(`${EP.bookings}/${id}/confirm`, { method: 'POST' });
        },
        // sp_CancelReservation: chủ studio hủy thì luôn hoàn tiền các khoản đã thanh toán
        async cancelBooking(id, reason) {
            reason = String(reason || '').trim() || null;
            if (!isLive()) {
                const b = demoFind(id);
                if (!['PENDING', 'CONFIRMED'].includes(b.status)) throw new ApiError('Chỉ hủy được đơn PENDING hoặc CONFIRMED.', 409);
                demoHist(b, 'CANCELLED'); b.status = 'CANCELLED'; b.cancel_reason = reason;
                b.payments.forEach(p => { if (p.status === 'SUCCESS') p.status = 'REFUNDED'; else if (p.status === 'PENDING') p.status = 'FAILED'; });
                return demoCopy(b);
            }
            return api(`${EP.bookings}/${id}/cancel`, { method: 'POST', body: reason ? { reason } : undefined });
        },
        // sp_CheckIn: quét/nhập mã QR; cho vào sớm tối đa 30 phút, không quá giờ kết thúc
        async checkIn(qr_code) {
            if (!isLive()) {
                const b = DEMO.bookings.find(x => x.qr_code === String(qr_code).trim());
                if (!b) throw new ApiError('Mã QR không hợp lệ.', 404);
                if (b.status !== 'CONFIRMED') throw new ApiError('Đơn chưa được xác nhận hoặc đã sử dụng.', 409);
                const now = Date.now();
                if (now < new Date(b.start_time).getTime() - 30 * 60000 || now > new Date(b.end_time).getTime())
                    throw new ApiError('Chưa đến giờ check-in (sớm nhất 30 phút) hoặc đã quá giờ.', 409);
                demoHist(b, 'IN_USE'); b.status = 'IN_USE';
                b.session = { checkin_time: new Date().toISOString(), checkout_time: null, actual_minutes: null };
                return demoCopy(b);
            }
            return api(EP.checkin, { method: 'POST', body: { qr_code: String(qr_code).trim() } });
        },
        // sp_CheckOut: IN_USE -> COMPLETED, trừ kho vật tư tiêu hao (CONSUMABLE)
        async checkOut(id) {
            if (!isLive()) {
                const b = demoFind(id);
                if (b.status !== 'IN_USE') throw new ApiError('Đơn chưa check-in hoặc đã kết thúc.', 409);
                const out = new Date();
                b.session = Object.assign(b.session || {}, { checkout_time: out.toISOString(), actual_minutes: Math.max(0, Math.round((out - new Date(b.session.checkin_time)) / 60000)) });
                demoHist(b, 'COMPLETED'); b.status = 'COMPLETED';
                const use = {};
                b.equipment.forEach(e => { use[e.equipment_id] = (use[e.equipment_id] || 0) + e.quantity; });
                b.packages.forEach(pk => ((DEMO.packages.find(x => x.package_id === pk.package_id) || {}).equipment || []).forEach(e => { use[e.equipment_id] = (use[e.equipment_id] || 0) + e.quantity_included; }));
                DEMO.equipment.forEach(e => { if (e.equipment_type === 'CONSUMABLE' && use[e.equipment_id]) e.quantity = Math.max(0, e.quantity - use[e.equipment_id]); });
                return demoCopy(b);
            }
            return api(`${EP.bookings}/${id}/checkout`, { method: 'POST' });
        },
        // sp_ProcessPayment: không được thu vượt tổng tiền; đơn đã hủy/hoàn tất không nhận thanh toán
        async payBooking(id, payload) {
            if (!isLive()) {
                const b = demoFind(id), amount = Number(payload.amount);
                if (!(amount > 0)) throw new ApiError('Số tiền phải lớn hơn 0.', 422);
                if (!['PENDING', 'CONFIRMED', 'IN_USE'].includes(b.status)) throw new ApiError('Đơn đã hủy hoặc đã hoàn tất, không nhận thanh toán.', 409);
                if (b.paid_amount + amount > b.total_amount) throw new ApiError('Số tiền thanh toán vượt quá tổng tiền của đơn.', 409);
                b.payments.push({ payment_id: demoId(), amount, payment_method: payload.payment_method, transaction_code: payload.transaction_code || null, status: 'SUCCESS', paid_at: new Date().toISOString() });
                return demoCopy(demoCalc(b));
            }
            return api(`${EP.bookings}/${id}/payments`, { method: 'POST', body: payload });
        },
        // sp_AddReservationEquipment: kiểm tra tồn kho theo khung giờ
        async addBookingEquipment(id, payload) {
            if (!isLive()) {
                const b = demoFind(id), eq = DEMO.equipment.find(e => e.equipment_id === Number(payload.equipment_id)), q = Number(payload.quantity);
                if (!(q > 0)) throw new ApiError('Số lượng phải lớn hơn 0.', 422);
                if (!['PENDING', 'CONFIRMED'].includes(b.status)) throw new ApiError('Chỉ thêm thiết bị khi đơn đang PENDING hoặc CONFIRMED.', 409);
                if (!eq) throw new ApiError('Không tìm thấy thiết bị.', 404);
                if (eq.studio_id !== b.studio_id) throw new ApiError('Thiết bị không thuộc studio của phòng đã đặt.', 409);
                const have = (b.equipment.find(e => e.equipment_id === eq.equipment_id) || { quantity: 0 }).quantity;
                if (['BROKEN', 'RETIRED', 'UNDER_MAINTENANCE'].includes(eq.status) || have + q > eq.quantity) throw new ApiError('Thiết bị không đủ số lượng trong khung giờ này.', 409);
                const row = b.equipment.find(e => e.equipment_id === eq.equipment_id);
                if (row) row.quantity += q; else b.equipment.push({ equipment_id: eq.equipment_id, name: eq.name, quantity: q, unit_price: eq.rental_price });
                return demoCopy(demoCalc(b));
            }
            return api(`${EP.bookings}/${id}/equipment`, { method: 'POST', body: payload });
        },
        // sp_AddReservationPackage: gói phải cùng studio, đang bán, hợp loại phòng, chưa chọn
        async addBookingPackage(id, payload) {
            if (!isLive()) {
                const b = demoFind(id), pk = DEMO.packages.find(p => p.package_id === Number(payload.package_id));
                if (!['PENDING', 'CONFIRMED'].includes(b.status)) throw new ApiError('Chỉ thêm gói khi đơn đang PENDING hoặc CONFIRMED.', 409);
                if (!pk) throw new ApiError('Không tìm thấy gói dịch vụ.', 404);
                if (!pk.is_active) throw new ApiError('Gói dịch vụ đã ngừng cung cấp.', 409);
                if (pk.studio_id !== b.studio_id) throw new ApiError('Gói không thuộc studio của phòng đã đặt.', 409);
                const room = DEMO.rooms.find(r => r.room_id === b.room_id);
                if (pk.room_type && room && pk.room_type !== room.room_type) throw new ApiError('Gói không phù hợp loại phòng đã đặt.', 409);
                if (b.packages.some(p => p.package_id === pk.package_id)) throw new ApiError('Đơn đã chọn gói này rồi.', 409);
                b.packages.push({ package_id: pk.package_id, name: pk.name, price: pk.price, notes: payload.notes || null });
                return demoCopy(demoCalc(b));
            }
            return api(`${EP.bookings}/${id}/packages`, { method: 'POST', body: payload });
        },
        async packages(studioId) {
            return withFallback(() => api(EP.packages + qs({ studio_id: studioId })),
                () => DEMO.packages.filter(p => !studioId || p.studio_id === Number(studioId)));
        },

        // Tổng quan cho dashboard
        async overview() {
            return withFallback(() => api(EP.overview), demoOverview);
        },

        // Thiết bị
        async equipment(studioId) {
            return withFallback(() => api(EP.equipment + qs({ studio_id: studioId })),
                () => DEMO.equipment.filter(e => !studioId || e.studio_id === Number(studioId)));
        },
        async saveEquipment(id, payload) {
            if (!isLive()) {
                if (id) { const e = DEMO.equipment.find(x => x.equipment_id === Number(id)); Object.assign(e, payload); return e; }
                const st = DEMO.studios.find(x => x.studio_id === Number(payload.studio_id));
                const e = Object.assign({ equipment_id: demoId(), studio_name: st && st.name }, payload);
                DEMO.equipment.push(e); return e;
            }
            if (id) { const { studio_id, ...patch } = payload; return api(EP.equipment + '/' + id, { method: 'PATCH', body: patch }); }
            return api(EP.equipment, { method: 'POST', body: payload });
        },
        async retireEquipment(id) {
            if (!isLive()) { const e = DEMO.equipment.find(x => x.equipment_id === Number(id)); if (e) e.status = 'RETIRED'; return null; }
            return api(EP.equipment + '/' + id, { method: 'DELETE' });
        },
        async addMaintenance(id, payload) {
            if (!isLive()) {
                const e = DEMO.equipment.find(x => x.equipment_id === Number(id));
                if (e && payload.status === 'DONE') e.status = 'GOOD';
                return Object.assign({ maintenance_id: demoId(), equipment_id: id, maintenance_date: new Date().toISOString() }, payload);
            }
            return api(`${EP.equipment}/${id}/maintenance`, { method: 'POST', body: payload });
        },

        async reviews(studioId) {
            return withFallback(() => api(EP.reviews + qs({ studio_id: studioId, limit: 50 })), () => DEMO.reviews);
        },
        async disputes(status) {
            return withFallback(() => api(EP.disputes + qs({ status, limit: 100 })),
                () => DEMO.disputes.filter(d => !status || d.status === status).map(d => Object.assign({}, d)));
        },
        // Provider: IN_REVIEW (tiếp nhận) hoặc RESOLVED kèm nội dung phản hồi
        async updateDispute(id, status, resolution) {
            resolution = String(resolution || '').trim() || null;
            if (!isLive()) {
                const d = DEMO.disputes.find(x => x.dispute_id === Number(id));
                if (!d) throw new ApiError('Không tìm thấy khiếu nại', 404);
                if (['RESOLVED', 'REJECTED'].includes(d.status)) throw new ApiError('Khiếu nại đã được xử lý xong, không thể thay đổi.', 409);
                if (status !== 'IN_REVIEW' && (!resolution || resolution.length < 3)) throw new ApiError('Cần nhập nội dung phản hồi / hướng giải quyết.', 400);
                d.status = status;
                if (status !== 'IN_REVIEW') { d.resolution = resolution; d.resolved_at = new Date().toISOString(); }
                return Object.assign({}, d);
            }
            return api(`${EP.disputes}/${id}`, { method: 'PATCH', body: { status, resolution } });
        },
        async workshops(status) {
            return withFallback(() => api(EP.workshops + qs({ status, limit: 100 })),
                () => DEMO.workshops.filter(w => !status || w.status === status).map(w => Object.assign({}, w)));
        },

        // Giữ lại cho các trang cũ: dữ liệu biểu đồ doanh thu theo tháng
        revenueByMonth() { return demoOverview().revenue_by_month.map(m => ({ label: 'T' + Number(m.month.slice(-2)), value: m.revenue })); }
    };

    /* ---------- Avatar: chữ cái theo tên + ảnh tự tải lên (cắt kiểu Facebook) ---------- */
    // Ảnh lưu ở localStorage của trình duyệt (theo user_id), chưa lưu lên server vì bảng Users chưa có cột ảnh.
    let uiUser = null;                                   // người dùng đang hiển thị trên giao diện
    const avatarKey = me => KEY.avatar + (me && me.user_id != null ? me.user_id : 'demo');
    const Avatar = {
        get: me => me ? store.get(avatarKey(me)) : null,
        set(me, url) { store.set(avatarKey(me), url); announceUser(me); },
        remove(me) { store.del(avatarKey(me)); announceUser(me); }
    };
    // Vẽ lại mọi thành phần hiển thị người dùng trên trang: [data-avatar], [data-user-name], [data-user-role]
    function paintUser(me) {
        if (!me) return;
        injectCropCss();                                  // chứa cả kiểu .avatar.has-img
        uiUser = me;
        const img = Avatar.get(me), letters = initials(displayName(me));
        document.querySelectorAll('[data-avatar]').forEach(el => {
            el.classList.toggle('has-img', !!img);
            el.style.backgroundImage = img ? `url("${img}")` : '';
            el.textContent = img ? '' : letters;
            el.setAttribute('aria-label', 'Ảnh đại diện của ' + displayName(me));
        });
        document.querySelectorAll('[data-user-name]').forEach(el => { el.textContent = displayName(me); });
        document.querySelectorAll('[data-user-role]').forEach(el => { el.textContent = me.role || ''; });
    }
    // Báo cho mọi nơi trên trang biết tên / ảnh vừa đổi
    function announceUser(me) {
        paintUser(me);
        document.dispatchEvent(new CustomEvent('provider:user', { detail: { user: me } }));
    }
    const avatarHTML = (extra, cls) => `<div class="avatar ${cls || ''}" data-avatar${extra ? ' style="' + extra + '"' : ''}>--</div>`;

    /* Hộp thoại cắt ảnh: kéo để chọn vùng, thanh trượt / lăn chuột để phóng to, xem trước khung tròn */
    const CROP_VIEW = 280, CROP_OUT = 320, CROP_MAX_BYTES = 10 * 1024 * 1024;
    function injectCropCss() {
        if (document.getElementById('pvCropCss')) return;
        const st = document.createElement('style'); st.id = 'pvCropCss';
        st.textContent = `
.avatar.has-img{background-size:cover;background-position:center;background-repeat:no-repeat;color:transparent}
.pv-crop-ov{position:fixed;inset:0;z-index:10000;background:rgba(15,23,42,.65);display:flex;align-items:center;justify-content:center;padding:16px;font-family:-apple-system,'Segoe UI',Roboto,sans-serif}
.pv-crop{background:var(--bg-card,#fff);color:var(--text-main,#0f172a);border-radius:18px;width:100%;max-width:380px;padding:20px;display:flex;flex-direction:column;gap:14px;box-shadow:0 20px 40px rgba(0,0,0,.35)}
.pv-crop h3{font-size:1rem;font-weight:800}
.pv-crop p{font-size:.75rem;color:var(--text-muted,#475569)}
.pv-crop-stage{position:relative;width:${CROP_VIEW}px;height:${CROP_VIEW}px;max-width:100%;margin:0 auto;overflow:hidden;border-radius:12px;background:#0f172a;touch-action:none;cursor:grab;user-select:none}
.pv-crop-stage.drag{cursor:grabbing}
.pv-crop-stage canvas{display:block;width:100%;height:100%}
.pv-crop-mask{position:absolute;inset:0;border-radius:50%;box-shadow:0 0 0 400px rgba(15,23,42,.58);border:2px solid rgba(255,255,255,.9);pointer-events:none}
.pv-crop-zoom{display:flex;align-items:center;gap:10px;font-size:.9rem}
.pv-crop-zoom input{flex:1;accent-color:var(--primary-color,#0284c7)}
.pv-crop-btns{display:flex;gap:10px;justify-content:flex-end}
.pv-crop-btns button{border:1px solid var(--border-color,#e2e8f0);background:transparent;color:inherit;border-radius:10px;padding:9px 16px;font-weight:700;font-size:.8rem;cursor:pointer}
.pv-crop-btns button.pv-ok{background:var(--primary-color,#0284c7);border-color:transparent;color:#fff}
.pv-crop-btns button:disabled{opacity:.5;cursor:not-allowed}`;
        document.head.appendChild(st);
    }

    function openCropper(file, onSave) {
        injectCropCss();
        const ov = document.createElement('div');
        ov.className = 'pv-crop-ov'; ov.setAttribute('role', 'dialog'); ov.setAttribute('aria-modal', 'true'); ov.setAttribute('aria-label', 'Cắt ảnh đại diện');
        ov.innerHTML = `<div class="pv-crop">
            <h3>Cắt ảnh đại diện</h3>
            <p>Kéo ảnh để chọn vùng hiển thị, dùng thanh trượt (hoặc lăn chuột) để phóng to / thu nhỏ.</p>
            <div class="pv-crop-stage" id="pvCropStage"><canvas width="${CROP_VIEW}" height="${CROP_VIEW}"></canvas><div class="pv-crop-mask"></div></div>
            <div class="pv-crop-zoom"><span aria-hidden="true">🖼️</span><input type="range" min="1" max="4" step="0.01" value="1" aria-label="Phóng to"><span aria-hidden="true" style="font-size:1.25rem">🖼️</span></div>
            <div class="pv-crop-btns"><button type="button" data-cancel>Hủy</button><button type="button" class="pv-ok" data-ok disabled>Dùng ảnh này</button></div>
        </div>`;
        document.body.appendChild(ov);
        const stage = ov.querySelector('#pvCropStage'), canvas = ov.querySelector('canvas'), ctx = canvas.getContext('2d');
        const slider = ov.querySelector('input[type=range]'), okBtn = ov.querySelector('[data-ok]');
        const V = CROP_VIEW;
        let img = null, minScale = 1, zoom = 1, ox = 0, oy = 0;

        const scale = () => minScale * zoom;
        const clamp = () => {                       // ảnh luôn phải phủ kín khung tròn
            const w = img.width * scale(), h = img.height * scale();
            ox = Math.min(0, Math.max(V - w, ox)); oy = Math.min(0, Math.max(V - h, oy));
        };
        const draw = () => {
            ctx.clearRect(0, 0, V, V);
            if (img) ctx.drawImage(img, ox, oy, img.width * scale(), img.height * scale());
        };
        const setZoom = z => {                       // phóng to quanh tâm khung
            const cx = (V / 2 - ox) / scale(), cy = (V / 2 - oy) / scale();
            zoom = Math.min(4, Math.max(1, z));
            ox = V / 2 - cx * scale(); oy = V / 2 - cy * scale();
            clamp(); draw(); slider.value = zoom;
        };

        const close = () => { document.removeEventListener('keydown', onKey); ov.remove(); };
        const onKey = e => { if (e.key === 'Escape') close(); };
        document.addEventListener('keydown', onKey);
        ov.querySelector('[data-cancel]').onclick = close;
        ov.addEventListener('mousedown', e => { if (e.target === ov) close(); });

        // Kéo bằng chuột / cảm ứng (Pointer Events)
        let drag = null;
        stage.addEventListener('pointerdown', e => {
            if (!img) return;
            drag = { x: e.clientX, y: e.clientY, ox, oy };
            stage.setPointerCapture(e.pointerId); stage.classList.add('drag');
        });
        stage.addEventListener('pointermove', e => {
            if (!drag) return;
            const k = V / stage.getBoundingClientRect().width;     // khung có thể bị co trên màn hình hẹp
            ox = drag.ox + (e.clientX - drag.x) * k; oy = drag.oy + (e.clientY - drag.y) * k;
            clamp(); draw();
        });
        const endDrag = () => { drag = null; stage.classList.remove('drag'); };
        stage.addEventListener('pointerup', endDrag); stage.addEventListener('pointercancel', endDrag);
        stage.addEventListener('wheel', e => { e.preventDefault(); setZoom(zoom * (e.deltaY < 0 ? 1.08 : 1 / 1.08)); }, { passive: false });
        slider.addEventListener('input', () => setZoom(Number(slider.value)));

        okBtn.onclick = () => {
            const out = document.createElement('canvas'); out.width = out.height = CROP_OUT;
            const k = CROP_OUT / V, o = out.getContext('2d');
            o.fillStyle = '#fff'; o.fillRect(0, 0, CROP_OUT, CROP_OUT);
            o.drawImage(img, ox * k, oy * k, img.width * scale() * k, img.height * scale() * k);
            onSave(out.toDataURL('image/jpeg', 0.88)); close();
        };

        // Đọc ảnh
        const reader = new FileReader();
        reader.onerror = () => { toast('Không đọc được tệp ảnh.', 'bad'); close(); };
        reader.onload = () => {
            const im = new Image();
            im.onerror = () => { toast('Tệp này không phải ảnh hợp lệ.', 'bad'); close(); };
            im.onload = () => {
                img = im; minScale = Math.max(V / im.width, V / im.height);
                zoom = 1; ox = (V - im.width * minScale) / 2; oy = (V - im.height * minScale) / 2;
                clamp(); draw(); okBtn.disabled = false;
            };
            im.src = reader.result;
        };
        reader.readAsDataURL(file);
        return { close };
    }

    // Mở hộp chọn tệp -> cắt -> lưu cho người dùng hiện tại
    function pickAvatar(me) {
        me = me || uiUser || currentUser() || DEMO.user;
        const inp = document.createElement('input');
        inp.type = 'file'; inp.accept = 'image/png,image/jpeg,image/webp,image/gif'; inp.style.display = 'none';
        inp.onchange = () => {
            const f = inp.files && inp.files[0]; inp.remove();
            if (!f) return;
            if (!/^image\//.test(f.type)) return toast('Vui lòng chọn một tệp ảnh.', 'warn');
            if (f.size > CROP_MAX_BYTES) return toast('Ảnh quá lớn (tối đa 10 MB).', 'warn');
            openCropper(f, url => { Avatar.set(me, url); toast('Đã cập nhật ảnh đại diện.', 'ok'); });
        };
        document.body.appendChild(inp); inp.click();
    }

    /* ---------- Giao diện PC: sidebar + topbar ---------- */
    const PC_NAV = [
        { key: 'dashboard', icon: '📊', label: 'Tổng quan', href: 'provider-pc-dashboard.html' },
        { key: 'bookings', icon: '📅', label: 'Lịch đặt', href: 'provider-pc-bookings.html' },
        { key: 'rooms', icon: '🧪', label: 'Phòng & Studio', href: 'provider-pc-rooms.html' },
        { key: 'equipment', icon: '🎛️', label: 'Thiết bị', href: 'provider-pc-equipment.html' },
        { key: 'feedback', icon: '💬', label: 'Đánh giá & Khiếu nại', href: 'provider-pc-feedback.html' },
        { key: 'workshops', icon: '🎓', label: 'Workshop', href: 'provider-pc-workshops.html' },
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
                </nav>`;
        }
        if (top) {
            top.innerHTML = `
                <h1 class="pc-title">${esc(title)}</h1>
                <div class="pc-top-right">
                    <span class="mode-badge" id="modeBadge"></span>
                    <button class="icon-btn" id="themeBtn" title="Đổi giao diện sáng / tối" aria-label="Đổi giao diện sáng hoặc tối">🌓</button>
                    <div class="pc-user" id="pcUser"><div class="avatar" data-avatar>--</div><div><strong data-user-name>...</strong><small data-user-role>...</small></div></div>
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
        paintUser(me || uiUser || currentUser());
        const btn = document.getElementById('authBtn');
        if (btn) {
            if (token()) { btn.textContent = 'Đăng xuất'; btn.href = '#'; btn.onclick = e => { e.preventDefault(); logout(); }; }
            else { btn.textContent = 'Đăng nhập'; btn.href = loginUrl(); btn.onclick = null; }
        }
    }

    /* ---------- Giao diện mobile: thanh trên + thanh điều hướng dưới ---------- */
    const M_NAV = [
        { key: 'dashboard', icon: '📊', label: 'Tổng quan', href: 'provider-index.html' },
        { key: 'bookings', icon: '📅', label: 'Lịch đặt', href: 'provider-bookings.html' },
        { key: 'rooms', icon: '🧪', label: 'Phòng', href: 'provider-rooms.html' },
        { key: 'equipment', icon: '🎛️', label: 'Thiết bị', href: 'provider-equipment.html' },
        { key: 'profile', icon: '👤', label: 'Hồ sơ', href: 'provider-profile.html' }
    ];

    async function mountMobile(activeKey, title) {
        applyTheme();
        document.body.classList.add('m');
        const top = document.getElementById('mTop'), nav = document.getElementById('mNav');
        if (top) {
            top.innerHTML = `
                <div class="m-top-row">
                    <h1 class="m-title">${esc(title)}</h1>
                    <button class="icon-btn" id="themeBtn" title="Đổi giao diện sáng / tối" aria-label="Đổi giao diện sáng hoặc tối">🌓</button>
                    <a class="m-avatar-link" href="provider-profile.html" aria-label="Hồ sơ cá nhân"><div class="avatar" data-avatar>--</div></a>
                </div>
                <span class="mode-badge" id="modeBadge"></span>`;
            document.getElementById('themeBtn').onclick = toggleTheme;
        }
        if (nav) {
            nav.innerHTML = '<div class="m-nav-inner">' + M_NAV.map(n =>
                `<a href="${n.href}" class="${n.key === activeKey ? 'active' : ''}"${n.key === activeKey ? ' aria-current="page"' : ''}><span>${n.icon}</span>${n.label}</a>`).join('') + '</div>';
        }
        const me = await data.me().catch(() => DEMO.user);
        refreshChrome(me);
        paintPendingDot();
        return me;
    }

    // Chấm đỏ số đơn chờ duyệt trên thẻ "Lịch đặt" (gọi lại sau khi duyệt/hủy đơn để cập nhật)
    async function paintPendingDot() {
        const a = document.querySelector('.m-nav a[href="provider-bookings.html"]');
        if (!a) return;
        let n = 0;
        try { n = Number((await data.overview()).pending_bookings) || 0; } catch (e) { n = 0; }
        let d = a.querySelector('.dot');
        if (!n) { if (d) d.remove(); return; }
        if (!d) { d = document.createElement('i'); d.className = 'dot'; d.style.fontStyle = 'normal'; a.appendChild(d); }
        d.textContent = n > 9 ? '9+' : n;
        a.setAttribute('aria-label', 'Lịch đặt, ' + n + ' đơn chờ duyệt');
    }

    // Bottom sheet: bấm nền tối, nút [data-close] hoặc phím Esc để đóng. Trả về { open(id), close(el) }.
    function bindSheets(onClose) {
        let lastFocus = null;
        const open = id => { lastFocus = document.activeElement; document.getElementById(id).classList.add('open'); };
        const close = el => { el.classList.remove('open'); if (onClose) onClose(el); if (lastFocus && lastFocus.focus) lastFocus.focus(); };
        document.querySelectorAll('.modal-overlay').forEach(ov => ov.addEventListener('click', e => { if (e.target === ov || e.target.closest('[data-close]')) close(ov); }));
        document.addEventListener('keydown', e => { if (e.key === 'Escape') document.querySelectorAll('.modal-overlay.open').forEach(close); });
        return { open, close };
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
        KEY, DEMO, ROOM_TYPES, BOOKING_STATUS, ROOM_STATUS, EQUIPMENT_CATEGORY, EQUIPMENT_STATUS, STUDIO_STATUS, DISPUTE_STATUS, WORKSHOP_STATUS, PAYMENT_STATUS, PAYMENT_METHOD, EP, state, isLive,
        store, esc, money, moneyShort, fmtDate, fmtTime, fmtRange, hoursBetween, initials,
        toast, applyTheme, toggleTheme,
        apiBase, token, currentUser, login, logout, loginUrl, requireLogin, api, ApiError,
        displayName, Avatar, avatarHTML, paintUser, pickAvatar,
        data, mountPC, mountMobile, paintPendingDot, bindSheets, refreshChrome, addPcShortcut
    };
})(window);
