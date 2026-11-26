import 'package:flutter/material.dart';

import '../api.dart';
import '../format.dart';
import '../widgets.dart';

class CommunityScreen extends StatefulWidget {
  const CommunityScreen({super.key});
  @override
  State<CommunityScreen> createState() => _CommunityScreenState();
}

class _CommunityScreenState extends State<CommunityScreen> {
  final _q = TextEditingController();
  late Future<List<dynamic>> _f = _load();

  /// Có từ khóa -> tìm tri thức (TF-IDF + từ đồng nghĩa); không có -> bài mới nhất.
  Future<List<dynamic>> _load() async {
    final q = _q.text.trim();
    if (q.length >= 2) return ((await api.get('/api/community/search', query: {'q': q}))['results'] as List);
    return (await api.get('/api/community/posts', query: {'limit': 30})) as List;
  }

  void _reload() => setState(() => _f = _load());

  /// Bài đăng thường có post_id; kết quả tìm kiếm dùng id + kind (workshop thì không mở chi tiết bài).
  int? _postId(Map p) => p['post_id'] ?? (p['kind'] == 'POST' ? p['id'] : null);

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('Cộng đồng')),
        body: Column(children: [
          Padding(
            padding: const EdgeInsets.all(12),
            child: TextField(
              controller: _q,
              textInputAction: TextInputAction.search,
              onSubmitted: (_) => _reload(),
              decoration: InputDecoration(hintText: 'Tìm kiến thức: tráng phim, ánh sáng…', prefixIcon: const Icon(Icons.search), border: OutlineInputBorder(borderRadius: BorderRadius.circular(12))),
            ),
          ),
          Expanded(
            child: AsyncList<List<dynamic>>(
              future: _f,
              onRetry: _reload,
              builder: (items) => items.isEmpty
                  ? const Center(child: Text('Chưa có nội dung'))
                  : ListView.builder(
                      itemCount: items.length,
                      itemBuilder: (c, i) {
                        final p = items[i] as Map;
                        return ListTile(
                          title: Text('${p['title']}'),
                          subtitle: Text('${p['snippet'] ?? p['content'] ?? ''}', maxLines: 2, overflow: TextOverflow.ellipsis),
                          trailing: p['post_type'] != null ? Chip2('${p['post_type']}') : null,
                          onTap: _postId(p) == null ? null : () => Navigator.push(c, MaterialPageRoute(builder: (_) => PostScreen(id: _postId(p)!))),
                        );
                      },
                    ),
            ),
          ),
        ]),
      );
}

class PostScreen extends StatefulWidget {
  final int id;
  const PostScreen({super.key, required this.id});
  @override
  State<PostScreen> createState() => _PostScreenState();
}

class _PostScreenState extends State<PostScreen> {
  late Future<Map> _f = _load();
  final _c = TextEditingController();
  Future<Map> _load() async => Map.from(await api.get('/api/community/posts/${widget.id}'));

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('Bài viết')),
        body: AsyncList<Map>(
          future: _f,
          onRetry: () => setState(() => _f = _load()),
          builder: (p) => ListView(padding: const EdgeInsets.all(16), children: [
            Text('${p['title']}', style: Theme.of(context).textTheme.titleLarge),
            Text('${p['author_name']} · ${fmtDateTime(p['created_at'])}'),
            const SizedBox(height: 12),
            Text('${p['content']}'),
            const Divider(height: 32),
            Text('Bình luận (${(p['comments'] as List? ?? []).length})', style: const TextStyle(fontWeight: FontWeight.w600)),
            for (final c in (p['comments'] as List? ?? [])) ListTile(dense: true, title: Text('${c['user_name']}'), subtitle: Text('${c['content']}')),
            Row(children: [
              Expanded(child: TextField(controller: _c, decoration: const InputDecoration(hintText: 'Viết bình luận…'))),
              IconButton(
                icon: const Icon(Icons.send),
                onPressed: () async {
                  if (_c.text.trim().isEmpty) return;
                  final r = await guard(context, () => api.post('/api/community/posts/${widget.id}/comments', {'content': _c.text.trim()}));
                  if (r != null) {
                    _c.clear();
                    setState(() => _f = _load());
                  }
                },
              ),
            ]),
          ]),
        ),
      );
}

