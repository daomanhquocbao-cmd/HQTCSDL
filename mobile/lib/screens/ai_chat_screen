import 'package:flutter/material.dart';

import '../api.dart';
import '../format.dart';
import '../widgets.dart';
import 'room_screen.dart';

class AiChatScreen extends StatefulWidget {
  const AiChatScreen({super.key});
  @override
  State<AiChatScreen> createState() => _AiChatScreenState();
}

class _AiChatScreenState extends State<AiChatScreen> {
  final _c = TextEditingController();
  final List<Map<String, dynamic>> _msgs = [
    {'me': false, 'text': 'Xin chào! Hãy hỏi mình, ví dụ: "phòng tối cho 3 người dưới 300k ở Hà Nội" hoặc "cách tráng phim đen trắng".'}
  ];
  bool _busy = false;

  Future<void> _send() async {
    final q = _c.text.trim();
    if (q.length < 2 || _busy) return;
    _c.clear();
    setState(() {
      _msgs.add({'me': true, 'text': q});
      _busy = true;
    });
    final r = await guard(context, () => api.get('/api/ai/ask', query: {'q': q}));
    setState(() {
      _busy = false;
      if (r == null) return;
      _msgs.add({'me': false, 'text': r['understood'] == true ? 'Mình tìm được các phòng phù hợp:' : 'Mình chưa hiểu tiêu chí phòng nào, nhưng có thể có bài viết liên quan:', 'rooms': r['results'], 'knowledge': r['knowledge']});
    });
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('Trợ lý AI')),
        body: Column(children: [
          Expanded(
            child: ListView(padding: const EdgeInsets.all(12), children: [
              for (final m in _msgs) ...[
                Align(
                  alignment: m['me'] ? Alignment.centerRight : Alignment.centerLeft,
                  child: Container(
                    margin: const EdgeInsets.symmetric(vertical: 4),
                    padding: const EdgeInsets.all(10),
                    constraints: const BoxConstraints(maxWidth: 320),
                    decoration: BoxDecoration(color: m['me'] ? kBrand : Colors.grey.shade200, borderRadius: BorderRadius.circular(12)),
                    child: Text(m['text'], style: TextStyle(color: m['me'] ? Colors.white : null)),
                  ),
                ),
                for (final r in (m['rooms'] as List? ?? []))
                  Card(
                    child: ListTile(
                      dense: true,
                      title: Text('${r['room_name']}'),
                      subtitle: Text('${r['studio_name']} · ${money(r['price_per_hour'])}/giờ'),
                      onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => RoomScreen(roomId: r['room_id']))),
                    ),
                  ),
                for (final k in (m['knowledge'] as List? ?? [])) ListTile(dense: true, leading: const Icon(Icons.menu_book, size: 18), title: Text('${k['title']}'), subtitle: Text('${k['snippet'] ?? ''}', maxLines: 2, overflow: TextOverflow.ellipsis)),
              ],
              if (_busy) const Padding(padding: EdgeInsets.all(8), child: LinearProgressIndicator()),
            ]),
          ),
          SafeArea(
            child: Padding(
              padding: const EdgeInsets.all(8),
              child: Row(children: [
                Expanded(child: TextField(controller: _c, onSubmitted: (_) => _send(), decoration: const InputDecoration(hintText: 'Nhập câu hỏi…', border: OutlineInputBorder()))),
                IconButton(onPressed: _send, icon: const Icon(Icons.send)),
              ]),
            ),
          ),
        ]),
      );
}
