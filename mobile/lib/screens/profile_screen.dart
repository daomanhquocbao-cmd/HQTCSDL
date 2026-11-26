import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:image_picker/image_picker.dart';

import '../api.dart';
import '../widgets.dart';

class ProfileScreen extends StatefulWidget {
  final VoidCallback onLogout;
  const ProfileScreen({super.key, required this.onLogout});
  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  late Future<List<dynamic>> _f = _load();
  Future<List<dynamic>> _load() async => (await api.get('/api/collections')) as List;
  void _reload() => setState(() => _f = _load());

  Future<void> _create() async {
    final c = TextEditingController();
    final v = await showDialog<String>(
      context: context,
      builder: (d) => AlertDialog(
        title: const Text('Bộ sưu tập mới'),
        content: TextField(controller: c, autofocus: true, decoration: const InputDecoration(hintText: 'Tên bộ sưu tập')),
        actions: [TextButton(onPressed: () => Navigator.pop(d), child: const Text('Hủy')), FilledButton(onPressed: () => Navigator.pop(d, c.text), child: const Text('Tạo'))],
      ),
    );
    if (v != null && v.trim().isNotEmpty && await guard(context, () => api.post('/api/collections', {'name': v.trim()})) != null) _reload();
  }

  @override
  Widget build(BuildContext context) {
    final u = api.user ?? {};
    return Scaffold(
      appBar: AppBar(title: const Text('Hồ sơ'), actions: [IconButton(onPressed: widget.onLogout, icon: const Icon(Icons.logout), tooltip: 'Đăng xuất')]),
      floatingActionButton: FloatingActionButton.extended(onPressed: _create, icon: const Icon(Icons.add), label: const Text('Bộ sưu tập')),
      body: Column(children: [
        ListTile(leading: const CircleAvatar(child: Icon(Icons.person)), title: Text('${u['full_name'] ?? ''}'), subtitle: Text('${u['email'] ?? ''}')),
        const Divider(height: 1),
        const Padding(padding: EdgeInsets.all(12), child: Align(alignment: Alignment.centerLeft, child: Text('Bộ sưu tập ảnh của tôi', style: TextStyle(fontWeight: FontWeight.w600)))),
        Expanded(
          child: AsyncList<List<dynamic>>(
            future: _f,
            onRetry: _reload,
            builder: (list) => list.isEmpty
                ? const Center(child: Text('Chưa có bộ sưu tập'))
                : ListView(children: [
                    for (final c in list)
                      ListTile(
                        leading: const Icon(Icons.photo_library),
                        title: Text('${c['name']}'),
                        subtitle: Text('${c['photo_count'] ?? 0} ảnh'),
                        onTap: () async {
                          await Navigator.push(context, MaterialPageRoute(builder: (_) => CollectionScreen(id: c['collection_id'], name: '${c['name']}')));
                          _reload();
                        },
                      ),
                  ]),
          ),
        ),
      ]),
    );
  }
}

class CollectionScreen extends StatefulWidget {
  final int id;
  final String name;
  const CollectionScreen({super.key, required this.id, required this.name});
  @override
  State<CollectionScreen> createState() => _CollectionScreenState();
}

class _CollectionScreenState extends State<CollectionScreen> {
  late Future<List<dynamic>> _f = _load();
  Future<List<dynamic>> _load() async => (await api.get('/api/collections/${widget.id}/photos')) as List;
  void _reload() => setState(() => _f = _load());

  Future<void> _upload() async {
    final x = await ImagePicker().pickImage(source: ImageSource.gallery, maxWidth: 2400, imageQuality: 88);
    if (x == null) return;
    final bytes = await x.readAsBytes();
    if (await guard(context, () => api.post('/api/collections/${widget.id}/photos', {'data': base64Encode(bytes), 'caption': x.name}), ok: 'Đã tải ảnh lên') != null) _reload();
  }

  Future<void> _share() async {
    final r = await guard(context, () => api.post('/api/collections/${widget.id}/share'));
    if (r == null || !mounted) return;
    final link = '${api.base}/web/customer/shared.html?t=${r['share_token']}';
    await showDialog<void>(
      context: context,
      builder: (d) => AlertDialog(
        title: const Text('Liên kết chia sẻ (chỉ xem)'),
        content: SelectableText(link),
        actions: [
          TextButton(
            onPressed: () async {
              await guard(context, () => api.delete('/api/collections/${widget.id}/share'), ok: 'Đã thu hồi liên kết');
              if (d.mounted) Navigator.pop(d);
            },
            child: const Text('Thu hồi'),
          ),
          FilledButton(
            onPressed: () {
              Clipboard.setData(ClipboardData(text: link));
              Navigator.pop(d);
              snack(context, 'Đã sao chép liên kết');
            },
            child: const Text('Sao chép'),
          ),
        ],
      ),
    );
  }

  Future<void> _restore(int photoId) async {
    final mode = await showModalBottomSheet<String>(
      context: context,
      builder: (s) => SafeArea(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          ListTile(leading: const Icon(Icons.auto_fix_high), title: const Text('Phục hồi ảnh cũ'), onTap: () => Navigator.pop(s, 'restore')),
          ListTile(leading: const Icon(Icons.hd), title: const Text('Tăng cường ảnh scan (2x)'), onTap: () => Navigator.pop(s, 'enhance')),
          ListTile(leading: const Icon(Icons.invert_colors), title: const Text('Đảo âm bản → dương bản'), onTap: () => Navigator.pop(s, 'negative')),
        ]),
      ),
    );
    if (mode != null && await guard(context, () => api.post('/api/collections/photos/$photoId/restore', {'mode': mode}), ok: 'Đã tạo ảnh mới') != null) _reload();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: Text(widget.name), actions: [IconButton(onPressed: _share, icon: const Icon(Icons.share), tooltip: 'Chia sẻ')]),
        floatingActionButton: FloatingActionButton(onPressed: _upload, child: const Icon(Icons.add_a_photo)),
        body: AsyncList<List<dynamic>>(
          future: _f,
          onRetry: _reload,
          builder: (photos) => photos.isEmpty
              ? const Center(child: Text('Chưa có ảnh'))
              : GridView.builder(
                  padding: const EdgeInsets.all(8),
                  gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(crossAxisCount: 2, mainAxisSpacing: 8, crossAxisSpacing: 8),
                  itemCount: photos.length,
                  itemBuilder: (c, i) {
                    final p = photos[i] as Map;
                    return GestureDetector(
                      onTap: () => _restore(p['photo_id']),
                      child: Stack(fit: StackFit.expand, children: [
                        ClipRRect(borderRadius: BorderRadius.circular(8), child: Image.network('${api.base}${p['url']}', fit: BoxFit.cover, errorBuilder: (_, __, ___) => const Icon(Icons.broken_image))),
                        if (p['kind'] != 'ORIGINAL') const Positioned(top: 6, left: 6, child: Chip2('AI')),
                      ]),
                    );
                  },
                ),
        ),
      );
}
