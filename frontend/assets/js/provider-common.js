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
        equipment: '/api/provider/equipment', packages: '/api/provider/packages', reviews: '/api/provider/reviews'
    };

    const KEY = {
        token: 'provider_token',
        user: 'provider_user',
        theme: 'provider_theme',
        api: 'provider_api_base',
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
        reviews: []
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
            if (!isLive()) { Object.assign(DEMO.user, payload); return DEMO.user; }
            const u = await api(EP.me, { method: 'PATCH', body: payload });
            store.set(KEY.user, JSON.stringify(u)); return u;
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
        async cancelBooking(id) {
            if (!isLive()) {
                const b = demoFind(id);
                if (!['PENDING', 'CONFIRMED'].includes(b.status)) throw new ApiError('Chỉ hủy được đơn PENDING hoặc CONFIRMED.', 409);
                demoHist(b, 'CANCELLED'); b.status = 'CANCELLED';
                b.payments.forEach(p => { if (p.status === 'SUCCESS') p.status = 'REFUNDED'; else if (p.status === 'PENDING') p.status = 'FAILED'; });
                return demoCopy(b);
            }
            return api(`${EP.bookings}/${id}/cancel`, { method: 'POST' });
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

        // Giữ lại cho các trang cũ: dữ liệu biểu đồ doanh thu theo tháng
        revenueByMonth() { return demoOverview().revenue_by_month.map(m => ({ label: 'T' + Number(m.month.slice(-2)), value: m.revenue })); }
    };

    /* ---------- Giao diện PC: sidebar + topbar ---------- */
    const PC_NAV = [
        { key: 'dashboard', icon: '📊', label: 'Tổng quan', href: 'provider-pc-dashboard.html' },
        { key: 'bookings', icon: '📅', label: 'Lịch đặt', href: 'provider-pc-bookings.html' },
        { key: 'rooms', icon: '🧪', label: 'Phòng & Studio', href: 'provider-pc-rooms.html' },
        { key: 'equipment', icon: '🎛️', label: 'Thiết bị', href: 'provider-pc-equipment.html' },
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
        KEY, DEMO, ROOM_TYPES, BOOKING_STATUS, ROOM_STATUS, EQUIPMENT_CATEGORY, EQUIPMENT_STATUS, STUDIO_STATUS, PAYMENT_STATUS, PAYMENT_METHOD, EP, state, isLive,
        store, esc, money, moneyShort, fmtDate, fmtTime, fmtRange, hoursBetween, initials,
        toast, applyTheme, toggleTheme,
        apiBase, token, currentUser, login, logout, loginUrl, requireLogin, api, ApiError,
        data, mountPC, refreshChrome, addPcShortcut
    };
})(window);
