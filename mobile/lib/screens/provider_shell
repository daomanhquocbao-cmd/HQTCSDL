import 'package:flutter/material.dart';

import '../api.dart';
import '../format.dart';
import '../widgets.dart';
import 'community_screen.dart';

class ProviderShell extends StatefulWidget {
  final VoidCallback onLogout;
  const ProviderShell({super.key, required this.onLogout});
  @override
  State<ProviderShell> createState() => _ProviderShellState();
}

class _ProviderShellState extends State<ProviderShell> {
  int _i = 0;
  @override
  Widget build(BuildContext context) => Scaffold(
        body: IndexedStack(index: _i, children: [
          const _ProvOverview(),
          const _ProvBookings(),
          const _ProvRooms(),
          const _ProvAnalytics(),
          _MoreTab(onLogout: widget.onLogout),
        ]),
        bottomNavigationBar: NavigationBar(
          selectedIndex: _i,
          onDestinationSelected: (v) => setState(() => _i = v),
          destinations: const [
            NavigationDestination(icon: Icon(Icons.dashboard), label: 'Tổng quan'),
            NavigationDestination(icon: Icon(Icons.event_note), label: 'Đơn đặt'),
            NavigationDestination(icon: Icon(Icons.meeting_room), label: 'Phòng'),
            NavigationDestination(icon: Icon(Icons.insights), label: 'Phân tích'),
            NavigationDestination(icon: Icon(Icons.more_horiz), label: 'Khác'),
          ],
        ),
      );
}

class _ProvOverview extends StatefulWidget {
  const _ProvOverview();
  @override
  State<_ProvOverview> createState() => _ProvOverviewState();
}

class _ProvOverviewState extends State<_ProvOverview> {
  late Future<Map> _f = _load();
  Future<Map> _load() async => Map.from(await api.get('/api/provider/overview'));
  void _reload() => setState(() => _f = _load());

  @override
  Widget build(BuildContext context) => Pane(
        title: 'Tổng quan',
        actions: [IconButton(onPressed: _reload, icon: const Icon(Icons.refresh))],
        child: AsyncList<Map>(
          future: _f,
          onRetry: _reload,
          builder: (o) => GridView.count(
            crossAxisCount: 2,
            padding: const EdgeInsets.all(12),
            childAspectRatio: 1.6,
            children: [
              KpiCard('Doanh thu tháng này', money(o['revenue_this_month'])),
              KpiCard('Tổng doanh thu', money(o['revenue_total'])),
              KpiCard('Đơn chờ duyệt', '${o['pending_bookings']}'),
              KpiCard('Đơn sắp tới', '${o['upcoming_bookings']}'),
              KpiCard('Phòng / Thiết bị', '${o['room_count']} / ${o['equipment_count']}'),
              KpiCard('Đánh giá TB', o['avg_rating'] == null ? '—' : '★ ${o['avg_rating']} (${o['review_count']})'),
            ],
          ),
        ),
      );
}

class _ProvBookings extends StatefulWidget {
  const _ProvBookings();
  @override
  State<_ProvBookings> createState() => _ProvBookingsState();
}

class _ProvBookingsState extends State<_ProvBookings> {
  String? _status = 'PENDING';
  late Future<List<dynamic>> _f = _load();
  Future<List<dynamic>> _load() async => (await api.get('/api/provider/bookings', query: {'status': _status, 'limit': 100})) as List;
  void _reload() => setState(() => _f = _load());

  Future<void> _act(String path, String ok, {Object? body}) async {
    if (await guard(context, () => api.post(path, body), ok: ok) != null) _reload();
  }

  Future<void> _scan() async {
    final code = await askText(context, 'Check-in bằng mã QR', hint: 'QR-00103-482915');
    if (code != null && code.trim().isNotEmpty) await _act('/api/provider/bookings/checkin', 'Check-in thành công', body: {'qr_code': code.trim()});
  }

  @override
  Widget build(BuildContext context) => Pane(
        title: 'Đơn đặt',
        actions: [IconButton(onPressed: _scan, icon: const Icon(Icons.qr_code_scanner), tooltip: 'Check-in bằng mã')],
        child: Column(children: [
          SizedBox(
            height: 52,
            child: ListView(scrollDirection: Axis.horizontal, padding: const EdgeInsets.symmetric(horizontal: 12), children: [
              for (final s in [null, 'PENDING', 'CONFIRMED', 'IN_USE', 'COMPLETED', 'CANCELLED'])
                Padding(
                  padding: const EdgeInsets.only(right: 8, top: 8, bottom: 8),
                  child: ChoiceChip(
                    label: Text(s == null ? 'Tất cả' : statusLabel(s)),
                    selected: _status == s,
                    onSelected: (_) {
                      _status = s;
                      _reload();
                    },
                  ),
                ),
            ]),
          ),
          Expanded(
            child: AsyncList<List<dynamic>>(
              future: _f,
              onRetry: _reload,
              builder: (list) => list.isEmpty
                  ? const Center(child: Text('Không có đơn'))
                  : RefreshIndicator(
                      onRefresh: () async => _reload(),
                      child: ListView.builder(
                        padding: const EdgeInsets.all(12),
                        itemCount: list.length,
                        itemBuilder: (c, i) {
                          final b = list[i] as Map;
                          final st = '${b['status']}';
                          final id = b['reservation_id'];
                          return Card(
                            child: Padding(
                              padding: const EdgeInsets.all(12),
                              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                                Row(children: [
                                  Expanded(child: Text('#$id · ${b['room_name']}', style: const TextStyle(fontWeight: FontWeight.w600))),
                                  Chip2(statusLabel(st), color: statusColor(st)),
                                ]),
                                Text('${b['customer_name']} · ${b['studio_name']}'),
                                Text('${fmtDateTime(b['start_time'])} → ${fmtDateTime(b['end_time']).substring(11)} · ${money(b['total_amount'])}'),
                                if (b['qr_code'] != null && st == 'CONFIRMED') SelectableText('Mã: ${b['qr_code']}', style: const TextStyle(color: Colors.grey)),
                                Wrap(spacing: 8, children: [
                                  if (st == 'PENDING') FilledButton(onPressed: () => _act('/api/provider/bookings/$id/confirm', 'Đã duyệt đơn'), child: const Text('Duyệt')),
                                  if (st == 'CONFIRMED' && b['qr_code'] != null) FilledButton(onPressed: () => _act('/api/provider/bookings/checkin', 'Check-in thành công', body: {'qr_code': b['qr_code']}), child: const Text('Check-in')),
                                  if (st == 'IN_USE') FilledButton(onPressed: () => _act('/api/provider/bookings/$id/checkout', 'Đã check-out'), child: const Text('Check-out')),
                                  if (st == 'PENDING' || st == 'CONFIRMED')
                                    OutlinedButton(
                                      onPressed: () async {
                                        if (await confirmDlg(context, 'Hủy đơn #$id?')) await _act('/api/provider/bookings/$id/cancel', 'Đã hủy đơn');
                                      },
                                      child: const Text('Hủy'),
                                    ),
                                ]),
                              ]),
                            ),
                          );
                        },
                      ),
                    ),
            ),
          ),
        ]),
      );
}

class _ProvRooms extends StatefulWidget {
  const _ProvRooms();
  @override
  State<_ProvRooms> createState() => _ProvRoomsState();
}

class _ProvRoomsState extends State<_ProvRooms> {
  late Future<List<dynamic>> _f = _load();
  Future<List<dynamic>> _load() async => (await api.get('/api/provider/rooms')) as List;
  void _reload() => setState(() => _f = _load());

  static const _labels = {'AVAILABLE': 'Hoạt động', 'MAINTENANCE': 'Bảo trì', 'INACTIVE': 'Tạm ẩn'};

  @override
  Widget build(BuildContext context) => Pane(
        title: 'Phòng & Studio',
        actions: [IconButton(onPressed: _reload, icon: const Icon(Icons.refresh))],
        child: AsyncList<List<dynamic>>(
          future: _f,
          onRetry: _reload,
          builder: (rooms) => ListView(padding: const EdgeInsets.all(12), children: [
            for (final r in rooms)
              Card(
                child: ListTile(
                  title: Text('${r['name']}'),
                  subtitle: Text('${r['studio_name']} · ${r['capacity']} người · ${money(r['price_per_hour'])}/giờ'),
                  trailing: DropdownButton<String>(
                    value: _labels.containsKey(r['status']) ? r['status'] as String : 'AVAILABLE',
                    underline: const SizedBox(),
                    items: [for (final e in _labels.entries) DropdownMenuItem(value: e.key, child: Text(e.value))],
                    onChanged: (v) async {
                      if (v != null && await guard(context, () => api.patch('/api/provider/rooms/${r['room_id']}', {'status': v}), ok: 'Đã cập nhật') != null) _reload();
                    },
                  ),
                ),
              ),
            const Padding(padding: EdgeInsets.all(8), child: Text('Thêm mới / sửa chi tiết phòng: dùng giao diện web.', textAlign: TextAlign.center)),
          ]),
        ),
      );
}

class _ProvAnalytics extends StatefulWidget {
  const _ProvAnalytics();
  @override
  State<_ProvAnalytics> createState() => _ProvAnalyticsState();
}

class _ProvAnalyticsState extends State<_ProvAnalytics> {
  DateTime _day = DateTime.now();
  late Future<List<dynamic>> _f = _load();

  Future<List<dynamic>> _load() async {
    final d = '${_day.year}-${_day.month.toString().padLeft(2, '0')}-${_day.day.toString().padLeft(2, '0')}';
    return await Future.wait([
      api.get('/api/provider/ai/forecast'),
      api.get('/api/provider/ai/pricing-suggestions'),
      api.get('/api/provider/ai/schedule-optimize', query: {'day': d}),
    ]);
  }

  void _reload() => setState(() => _f = _load());

  @override
  Widget build(BuildContext context) => Pane(
        title: 'Phân tích & AI',
        actions: [
          IconButton(
            icon: const Icon(Icons.calendar_today),
            onPressed: () async {
              final d = await showDatePicker(context: context, initialDate: _day, firstDate: DateTime.now().subtract(const Duration(days: 30)), lastDate: DateTime.now().add(const Duration(days: 90)));
              if (d != null) {
                _day = d;
                _reload();
              }
            },
          ),
        ],
        child: AsyncList<List<dynamic>>(
          future: _f,
          onRetry: _reload,
          builder: (r) {
            final fc = Map.from(r[0]), pr = Map.from(r[1]), sc = Map.from(r[2]);
            final conflicts = (sc['equipment_conflicts'] as List), moves = (sc['room_move_suggestions'] as List);
            return ListView(padding: const EdgeInsets.all(12), children: [
              Text('Dự báo nhu cầu', style: Theme.of(context).textTheme.titleMedium),
              if (fc['reliable'] != true) const Text('Dữ liệu còn ít, dự báo chỉ mang tính tham khảo.', style: TextStyle(color: Colors.orange)),
              for (final d in (fc['forecast'] as List)) ListTile(dense: true, title: Text('${d['weekday']} · ${d['forecast_date'] ?? ''}'), trailing: Text('${d['expected_bookings']} đơn · ${d['level']}')),
              const Divider(),
              Text('Gợi ý điều chỉnh giá', style: Theme.of(context).textTheme.titleMedium),
              if ((pr['suggestions'] as List).isEmpty) const Text('Chưa có gợi ý (thiếu dữ liệu hoặc không cần đổi).'),
              for (final s in (pr['suggestions'] as List)) ListTile(dense: true, title: Text('${s['day_type']} · ${s['band']} (${s['occupancy_pct']}%)'), subtitle: Text('${s['reason']}'), trailing: Chip2('×${s['suggested_multiplier']}')),
              const Divider(),
              Text('Tối ưu phân bổ ngày ${fmtDate(_day)}', style: Theme.of(context).textTheme.titleMedium),
              for (final room in (sc['rooms'] as List)) ListTile(dense: true, title: Text('${room['room_name']} · ${room['bookings']} đơn'), subtitle: Text(room['wasted_minutes'] > 0 ? 'Khoảng vụn ${room['wasted_minutes']} phút' : 'Không có khoảng vụn')),
              for (final c in conflicts) ListTile(dense: true, leading: const Icon(Icons.warning_amber, color: Colors.red), title: Text('Thiếu ${c['name']} (có ${c['stock']})')),
              for (final m in moves) ListTile(dense: true, leading: const Icon(Icons.swap_horiz), title: Text('Đơn #${m['reservation_id']}: ${m['from_room']} → ${m['suggest_room']}'), subtitle: Text('${m['reason']}')),
              if (conflicts.isEmpty && moves.isEmpty) const Text('Không có xung đột thiết bị và chưa cần đổi phòng.'),
            ]);
          },
        ),
      );
}

class _MoreTab extends StatelessWidget {
  final VoidCallback onLogout;
  const _MoreTab({required this.onLogout});
  @override
  Widget build(BuildContext context) => Pane(
        title: 'Khác',
        child: ListView(children: [
          ListTile(leading: const CircleAvatar(child: Icon(Icons.person)), title: Text('${api.user?['full_name'] ?? ''}'), subtitle: Text('${api.user?['email'] ?? ''}')),
          const Divider(),
          ListTile(leading: const Icon(Icons.forum), title: const Text('Cộng đồng'), onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const CommunityScreen()))),
          ListTile(leading: const Icon(Icons.logout), title: const Text('Đăng xuất'), onTap: onLogout),
        ]),
      );
}
