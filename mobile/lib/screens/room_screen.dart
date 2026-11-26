import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../api.dart';
import '../format.dart';
import '../widgets.dart';

class RoomScreen extends StatefulWidget {
  final int roomId;
  const RoomScreen({super.key, required this.roomId});
  @override
  State<RoomScreen> createState() => _RoomScreenState();
}

class _RoomScreenState extends State<RoomScreen> {
  late Future<Map> _f = _load();
  DateTime _day = DateTime.now().add(const Duration(days: 1));
  int _startHour = 9, _hours = 2;
  final _promo = TextEditingController();
  Map? _quote;
  List _busy = [];
  bool _busyLoading = false;

  Future<Map> _load() async {
    final r = Map.from(await api.get('/api/customer/rooms/${widget.roomId}'));
    _loadBusy();
    return r;
  }

  Future<void> _loadBusy() async {
    setState(() => _busyLoading = true);
    try {
      final d = '${_day.year}-${_day.month.toString().padLeft(2, '0')}-${_day.day.toString().padLeft(2, '0')}';
      _busy = (await api.get('/api/customer/rooms/${widget.roomId}/busy', query: {'date': d})) as List;
    } catch (_) {
      _busy = [];
    }
    if (mounted) setState(() => _busyLoading = false);
  }

  DateTime get _start => DateTime(_day.year, _day.month, _day.day, _startHour);
  DateTime get _end => _start.add(Duration(hours: _hours));

  Future<void> _getQuote() async {
    final q = await guard(context, () => api.get('/api/pricing/quote', query: {
          'room_id': widget.roomId,
          'start_time': isoLocal(_start),
          'end_time': isoLocal(_end),
          'promo_code': _promo.text.trim(),
        }));
    if (q != null) setState(() => _quote = Map.from(q));
  }

  Future<void> _book() async {
    final b = await guard(
        context,
        () => api.post('/api/bookings', {
              'room_id': widget.roomId,
              'start_time': isoLocal(_start),
              'end_time': isoLocal(_end),
              if (_promo.text.trim().isNotEmpty) 'promo_code': _promo.text.trim(),
            }),
        ok: 'Đã gửi yêu cầu đặt phòng. Chờ nhà cung cấp duyệt.');
    if (b != null && mounted) Navigator.pop(context);
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('Chi tiết phòng')),
        body: AsyncList<Map>(
          future: _f,
          onRetry: () => setState(() => _f = _load()),
          builder: (r) => ListView(padding: const EdgeInsets.all(16), children: [
            Text('${r['room_name']}', style: Theme.of(context).textTheme.titleLarge),
            Text('${r['studio_name']} · ${r['address']}, ${r['city']}'),
            const SizedBox(height: 8),
            Wrap(spacing: 8, children: [
              Chip2(roomTypeLabels[r['room_type']] ?? ''),
              Chip2('${r['capacity']} người'),
              if (r['area_sqm'] != null) Chip2('${r['area_sqm']} m²'),
              Chip2('★ ${(r['avg_rating'] as num).toStringAsFixed(1)} (${r['review_count']})'),
            ]),
            const SizedBox(height: 12),
            for (final e in {
              'Phong cách': r['art_style'],
              'Ánh sáng': r['lighting'],
              'Thông gió': r['ventilation'],
              'Âm học': r['acoustics'],
              'Tiện ích': r['amenities'],
              'Chính sách': r['usage_policy'],
              'Giờ mở cửa': '${r['open_time']} – ${r['close_time']}',
            }.entries)
              if (e.value != null && '${e.value}'.isNotEmpty)
                Padding(padding: const EdgeInsets.only(bottom: 4), child: Text.rich(TextSpan(children: [TextSpan(text: '${e.key}: ', style: const TextStyle(fontWeight: FontWeight.w600)), TextSpan(text: '${e.value}')]))),
            if (r['description'] != null) Padding(padding: const EdgeInsets.only(top: 6), child: Text('${r['description']}')),
            if (r['latitude'] != null)
              TextButton.icon(
                onPressed: () => launchUrl(Uri.parse('https://www.google.com/maps?q=${r['latitude']},${r['longitude']}'), mode: LaunchMode.externalApplication),
                icon: const Icon(Icons.place),
                label: const Text('Xem trên Google Maps'),
              ),
            const Divider(height: 32),
            Text('Đặt phòng · ${money(r['price_per_hour'])}/giờ', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 8),
            OutlinedButton.icon(
              icon: const Icon(Icons.calendar_today),
              label: Text('Ngày ${fmtDate(_day)}'),
              onPressed: () async {
                final d = await showDatePicker(context: context, initialDate: _day, firstDate: DateTime.now(), lastDate: DateTime.now().add(const Duration(days: 180)));
                if (d != null) {
                  _day = d;
                  _quote = null;
                  _loadBusy();
                }
              },
            ),
            Row(children: [
              const Text('Bắt đầu'),
              Expanded(child: Slider(value: _startHour.toDouble(), min: 6, max: 22, divisions: 16, label: '$_startHour:00', onChanged: (v) => setState(() { _startHour = v.round(); _quote = null; }))),
              Text('$_startHour:00'),
            ]),
            Row(children: [
              const Text('Số giờ'),
              IconButton(onPressed: _hours > 1 ? () => setState(() { _hours--; _quote = null; }) : null, icon: const Icon(Icons.remove_circle_outline)),
              Text('$_hours'),
              IconButton(onPressed: _hours < 12 ? () => setState(() { _hours++; _quote = null; }) : null, icon: const Icon(Icons.add_circle_outline)),
              Text('→ kết thúc ${_end.hour}:00'),
            ]),
            if (_busyLoading) const LinearProgressIndicator(),
            if (_busy.isNotEmpty)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 6),
                child: Text('Đã có người đặt: ${_busy.map((b) => '${fmtDateTime(b['start_time']).substring(11)}–${fmtDateTime(b['end_time']).substring(11)}').join(', ')}', style: TextStyle(color: Colors.red.shade700)),
              ),
            TextField(controller: _promo, decoration: const InputDecoration(labelText: 'Mã khuyến mãi (nếu có)')),
            const SizedBox(height: 8),
            Row(children: [
              Expanded(child: OutlinedButton(onPressed: _getQuote, child: const Text('Xem giá tạm tính'))),
              const SizedBox(width: 8),
              Expanded(child: FilledButton(onPressed: _book, child: const Text('Đặt phòng'))),
            ]),
            if (_quote != null)
              Card(
                margin: const EdgeInsets.only(top: 12),
                child: Padding(
                  padding: const EdgeInsets.all(12),
                  child: Text('Tạm tính: ${money(_quote!['final_amount'])}\n${_quote!['promo_message'] ?? ''}'),
                ),
              ),
          ]),
        ),
      );
}
