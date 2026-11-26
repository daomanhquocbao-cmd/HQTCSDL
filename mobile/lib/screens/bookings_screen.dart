import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../api.dart';
import '../format.dart';
import '../widgets.dart';

class BookingsScreen extends StatefulWidget {
  const BookingsScreen({super.key});
  @override
  State<BookingsScreen> createState() => _BookingsScreenState();
}

class _BookingsScreenState extends State<BookingsScreen> with WidgetsBindingObserver {
  late Future<List<dynamic>> _f = _load();

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  // Quay lại từ trình duyệt VNPay thì tải lại danh sách để thấy khoản đã thanh toán
  @override
  void didChangeAppLifecycleState(AppLifecycleState s) {
    if (s == AppLifecycleState.resumed) _reload();
  }

  Future<List<dynamic>> _load() async => (await api.get('/api/customer/bookings', query: {'limit': 50})) as List;
  void _reload() => setState(() => _f = _load());

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('Đơn của tôi')),
        body: AsyncList<List<dynamic>>(
          future: _f,
          onRetry: _reload,
          builder: (list) => list.isEmpty
              ? const Center(child: Text('Bạn chưa có đơn đặt nào'))
              : RefreshIndicator(
                  onRefresh: () async => _reload(),
                  child: ListView.builder(
                    padding: const EdgeInsets.all(12),
                    itemCount: list.length,
                    itemBuilder: (c, i) {
                      final b = list[i] as Map;
                      return Card(
                        child: ListTile(
                          onTap: () async {
                            await Navigator.push(c, MaterialPageRoute(builder: (_) => BookingDetailScreen(id: b['reservation_id'])));
                            _reload();
                          },
                          title: Text('${b['room_name']} · ${b['studio_name']}'),
                          subtitle: Text('${fmtDateTime(b['start_time'])} → ${fmtDateTime(b['end_time']).substring(11)}\nTổng ${money(b['total_amount'])}'
                              '${(b['balance_due'] as num) > 0 && b['status'] != 'CANCELLED' ? ' · còn nợ ${money(b['balance_due'])}' : ''}'),
                          isThreeLine: true,
                          trailing: Chip2(statusLabel(b['status']), color: statusColor(b['status'])),
                        ),
                      );
                    },
                  ),
                ),
        ),
      );
}

class BookingDetailScreen extends StatefulWidget {
  final int id;
  const BookingDetailScreen({super.key, required this.id});
  @override
  State<BookingDetailScreen> createState() => _BookingDetailScreenState();
}

class _BookingDetailScreenState extends State<BookingDetailScreen> {
  late Future<Map> _f = _load();
  Future<Map> _load() async => Map.from(await api.get('/api/customer/bookings/${widget.id}'));
  void _reload() => setState(() => _f = _load());

  Future<void> _vnpay() async {
    final r = await guard(context, () => api.post('/api/payments/vnpay/create', {'reservation_id': widget.id}));
    if (r != null) await launchUrl(Uri.parse(r['payment_url']), mode: LaunchMode.externalApplication);
  }

  Future<void> _cancel() async {
    final yes = await showDialog<bool>(
      context: context,
      builder: (d) => AlertDialog(
        title: const Text('Hủy đơn này?'),
        actions: [TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Không')), FilledButton(onPressed: () => Navigator.pop(d, true), child: const Text('Hủy đơn'))],
      ),
    );
    if (yes == true && await guard(context, () => api.post('/api/customer/bookings/${widget.id}/cancel'), ok: 'Đã hủy đơn') != null) _reload();
  }

  Future<void> _text(String title, Future<dynamic> Function(String) send, String ok) async {
    final c = TextEditingController();
    final v = await showDialog<String>(
      context: context,
      builder: (d) => AlertDialog(
        title: Text(title),
        content: TextField(controller: c, maxLines: 3, autofocus: true),
        actions: [TextButton(onPressed: () => Navigator.pop(d), child: const Text('Đóng')), FilledButton(onPressed: () => Navigator.pop(d, c.text), child: const Text('Gửi'))],
      ),
    );
    if (v != null && v.trim().isNotEmpty && await guard(context, () => send(v.trim()), ok: ok) != null) _reload();
  }

  Future<void> _review() async {
    int stars = 5;
    final c = TextEditingController();
    final yes = await showDialog<bool>(
      context: context,
      builder: (d) => StatefulBuilder(
        builder: (d, set) => AlertDialog(
          title: const Text('Đánh giá studio'),
          content: Column(mainAxisSize: MainAxisSize.min, children: [
            Row(mainAxisAlignment: MainAxisAlignment.center, children: [
              for (var i = 1; i <= 5; i++) IconButton(onPressed: () => set(() => stars = i), icon: Icon(i <= stars ? Icons.star : Icons.star_border, color: Colors.amber)),
            ]),
            TextField(controller: c, maxLines: 3, decoration: const InputDecoration(hintText: 'Nhận xét (tùy chọn)')),
          ]),
          actions: [TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Đóng')), FilledButton(onPressed: () => Navigator.pop(d, true), child: const Text('Gửi'))],
        ),
      ),
    );
    if (yes == true &&
        await guard(context, () => api.post('/api/customer/bookings/${widget.id}/review', {'rating': stars, 'comment': c.text.trim().isEmpty ? null : c.text.trim()}), ok: 'Cảm ơn bạn đã đánh giá') != null) {
      _reload();
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: Text('Đơn #${widget.id}')),
        body: AsyncList<Map>(
          future: _f,
          onRetry: _reload,
          builder: (b) {
            final st = b['status'] as String;
            final live = ['PENDING', 'CONFIRMED', 'IN_USE'].contains(st);
            final due = (b['balance_due'] as num);
            return ListView(padding: const EdgeInsets.all(16), children: [
              Row(children: [Expanded(child: Text('${b['room_name']}', style: Theme.of(context).textTheme.titleLarge)), Chip2(statusLabel(st), color: statusColor(st))]),
              Text('${b['studio_name']}'),
              const SizedBox(height: 8),
              Text('${fmtDateTime(b['start_time'])} → ${fmtDateTime(b['end_time'])}'),
              const Divider(height: 24),
              _kv('Tổng tiền', money(b['total_amount'])),
              _kv('Đã thanh toán', money(b['paid_amount'])),
              _kv('Còn nợ', money(due)),
              if (b['promotion'] != null) _kv('Mã giảm giá', '${b['promotion']['code']}'),
              if ((b['equipment'] as List).isNotEmpty) ...[const SizedBox(height: 12), const Text('Thiết bị thuê thêm', style: TextStyle(fontWeight: FontWeight.w600)), for (final e in b['equipment']) Text('• ${e['name']} × ${e['quantity']}')],
              if ((b['packages'] as List).isNotEmpty) ...[const SizedBox(height: 12), const Text('Gói dịch vụ', style: TextStyle(fontWeight: FontWeight.w600)), for (final p in b['packages']) Text('• ${p['name']}')],
              if (b['qr_code'] != null) ...[
                const SizedBox(height: 16),
                Card(color: Colors.grey.shade100, child: Padding(padding: const EdgeInsets.all(16), child: Column(children: [const Text('Mã check-in (đưa cho nhà cung cấp)'), const SizedBox(height: 6), SelectableText('${b['qr_code']}', style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold, letterSpacing: 1.5))]))),
              ],
              const SizedBox(height: 16),
              if (live && due > 0) FilledButton.icon(onPressed: _vnpay, icon: const Icon(Icons.payment), label: Text('Thanh toán ${money(due)} qua VNPay')),
              if (live) OutlinedButton(onPressed: _cancel, child: const Text('Hủy đơn')),
              if (st == 'COMPLETED' && b['has_review'] != true) FilledButton(onPressed: _review, child: const Text('Đánh giá')),
              OutlinedButton(onPressed: () => _text('Nội dung khiếu nại', (t) => api.post('/api/customer/bookings/${widget.id}/disputes', {'reason': t}), 'Đã gửi khiếu nại'), child: const Text('Gửi khiếu nại')),
            ]);
          },
        ),
      );

  Widget _kv(String k, String v) => Padding(padding: const EdgeInsets.symmetric(vertical: 2), child: Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [Text(k), Text(v, style: const TextStyle(fontWeight: FontWeight.w600))]));
}
