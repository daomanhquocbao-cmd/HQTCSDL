import 'package:flutter/material.dart';

import '../api.dart';
import '../format.dart';
import '../widgets.dart';
import 'room_screen.dart';

class ExploreScreen extends StatefulWidget {
  const ExploreScreen({super.key});
  @override
  State<ExploreScreen> createState() => _ExploreScreenState();
}

class _ExploreScreenState extends State<ExploreScreen> {
  final _q = TextEditingController();
  String? _type;
  String _sort = 'rating';
  late Future<List<dynamic>> _f = _load();

  Future<List<dynamic>> _load() async =>
      (await api.get('/api/customer/rooms', query: {'q': _q.text.trim(), 'room_type': _type, 'sort': _sort, 'limit': 40})) as List;

  void _reload() => setState(() => _f = _load());

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('Khám phá phòng')),
        body: Column(children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(12, 8, 12, 0),
            child: TextField(
              controller: _q,
              textInputAction: TextInputAction.search,
              onSubmitted: (_) => _reload(),
              decoration: InputDecoration(
                hintText: 'Tìm theo tên, phong cách, khu vực…',
                prefixIcon: const Icon(Icons.search),
                suffixIcon: IconButton(icon: const Icon(Icons.arrow_forward), onPressed: _reload),
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
              ),
            ),
          ),
          SizedBox(
            height: 52,
            child: ListView(scrollDirection: Axis.horizontal, padding: const EdgeInsets.symmetric(horizontal: 12), children: [
              for (final t in [null, 'STUDIO', 'DARKROOM'])
                Padding(
                  padding: const EdgeInsets.only(right: 8, top: 8, bottom: 8),
                  child: ChoiceChip(
                    label: Text(t == null ? 'Tất cả' : roomTypeLabels[t]!),
                    selected: _type == t,
                    onSelected: (_) {
                      _type = t;
                      _reload();
                    },
                  ),
                ),
              Padding(
                padding: const EdgeInsets.only(top: 8, bottom: 8),
                child: DropdownButton<String>(
                  value: _sort,
                  underline: const SizedBox(),
                  items: const [
                    DropdownMenuItem(value: 'rating', child: Text('Đánh giá cao')),
                    DropdownMenuItem(value: 'price_asc', child: Text('Giá tăng')),
                    DropdownMenuItem(value: 'price_desc', child: Text('Giá giảm')),
                    DropdownMenuItem(value: 'newest', child: Text('Mới nhất')),
                  ],
                  onChanged: (v) {
                    _sort = v ?? 'rating';
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
              builder: (rooms) => rooms.isEmpty
                  ? const Center(child: Text('Không có phòng phù hợp'))
                  : RefreshIndicator(
                      onRefresh: () async => _reload(),
                      child: ListView.builder(
                        padding: const EdgeInsets.all(12),
                        itemCount: rooms.length,
                        itemBuilder: (c, i) {
                          final r = rooms[i] as Map;
                          return Card(
                            child: ListTile(
                              onTap: () => Navigator.push(c, MaterialPageRoute(builder: (_) => RoomScreen(roomId: r['room_id']))),
                              title: Text('${r['room_name']}', style: const TextStyle(fontWeight: FontWeight.w600)),
                              subtitle: Text('${r['studio_name']} · ${r['city']}\n'
                                  '${roomTypeLabels[r['room_type']] ?? ''} · ${r['capacity']} người · ★ ${(r['avg_rating'] as num).toStringAsFixed(1)}'),
                              isThreeLine: true,
                              trailing: Text('${money(r['price_per_hour'])}\n/giờ', textAlign: TextAlign.right, style: const TextStyle(color: kBrand, fontWeight: FontWeight.w600)),
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
