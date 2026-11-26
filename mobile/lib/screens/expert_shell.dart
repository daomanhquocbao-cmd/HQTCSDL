import 'package:flutter/material.dart';

import '../api.dart';
import '../format.dart';
import '../widgets.dart';
import 'community_screen.dart';

class ExpertShell extends StatefulWidget {
  final VoidCallback onLogout;
  const ExpertShell({super.key, required this.onLogout});
  @override
  State<ExpertShell> createState() => _ExpertShellState();
}

class _ExpertShellState extends State<ExpertShell> {
  int _i = 0;
  @override
  Widget build(BuildContext context) => Scaffold(
        body: IndexedStack(index: _i, children: [
          const _Workshops(),
          const _Posts(),
          const CommunityScreen(),
          Pane(
            title: 'Hồ sơ',
            child: ListView(children: [
              ListTile(leading: const CircleAvatar(child: Icon(Icons.school)), title: Text('${api.user?['full_name'] ?? ''}'), subtitle: Text('${api.user?['email'] ?? ''}')),
              ListTile(leading: const Icon(Icons.logout), title: const Text('Đăng xuất'), onTap: widget.onLogout),
            ]),
          ),
        ]),
        bottomNavigationBar: NavigationBar(
          selectedIndex: _i,
          onDestinationSelected: (v) => setState(() => _i = v),
          destinations: const [
            NavigationDestination(icon: Icon(Icons.event), label: 'Workshop'),
            NavigationDestination(icon: Icon(Icons.edit_note), label: 'Bài viết'),
            NavigationDestination(icon: Icon(Icons.forum), label: 'Thảo luận'),
            NavigationDestination(icon: Icon(Icons.person), label: 'Hồ sơ'),
          ],
        ),
      );
}

class _Workshops extends StatefulWidget {
  const _Workshops();
  @override
  State<_Workshops> createState() => _WorkshopsState();
}

class _WorkshopsState extends State<_Workshops> {
  late Future<List<dynamic>> _f = _load();
  Future<List<dynamic>> _load() async {
    final all = (await api.get('/api/workshops')) as List;
    final me = api.user?['user_id'];
    return api.role == 'ADMIN' ? all : all.where((w) => w['expert_id'] == me).toList();
  }

  void _reload() => setState(() => _f = _load());

  Future<void> _create() async {
    final title = await askText(context, 'Tên workshop');
    if (title == null || title.trim().length < 3) return;
    final day = await showDatePicker(context: context, initialDate: DateTime.now().add(const Duration(days: 3)), firstDate: DateTime.now(), lastDate: DateTime.now().add(const Duration(days: 365)));
    if (day == null) return;
    final t = await showTimePicker(context: context, initialTime: const TimeOfDay(hour: 19, minute: 0));
    if (t == null) return;
    final cap = await askText(context, 'Số chỗ tối đa', hint: '20');
    final start = DateTime(day.year, day.month, day.day, t.hour, t.minute);
    final ok = await guard(
        context,
        () => api.post('/api/workshops', {
              'title': title.trim(),
              'capacity': int.tryParse(cap ?? '') ?? 20,
              'start_time': isoLocal(start),
              'end_time': isoLocal(start.add(const Duration(hours: 2))),
            }),
        ok: 'Đã tạo workshop');
    if (ok != null) _reload();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('Workshop của tôi')),
        floatingActionButton: FloatingActionButton.extended(onPressed: _create, icon: const Icon(Icons.add), label: const Text('Tạo workshop')),
        body: AsyncList<List<dynamic>>(
          future: _f,
          onRetry: _reload,
          builder: (list) => list.isEmpty
              ? const Center(child: Text('Chưa có workshop'))
              : ListView(padding: const EdgeInsets.all(12), children: [
                  for (final w in list)
                    Card(
                      child: ListTile(
                        title: Text('${w['title']}'),
                        subtitle: Text('${fmtDateTime(w['start_time'])}\nĐã đăng ký ${w['registered']}/${w['capacity']}'),
                        isThreeLine: true,
                        trailing: Chip2('còn ${w['remaining_slots']} chỗ'),
                      ),
                    ),
                ]),
        ),
      );
}

class _Posts extends StatefulWidget {
  const _Posts();
  @override
  State<_Posts> createState() => _PostsState();
}

class _PostsState extends State<_Posts> {
  late Future<List<dynamic>> _f = _load();
  Future<List<dynamic>> _load() async => (await api.get('/api/community/posts', query: {'limit': 50})) as List;
  void _reload() => setState(() => _f = _load());

  Future<void> _create() async {
    String type = 'TUTORIAL';
    final title = TextEditingController(), body = TextEditingController();
    final yes = await showDialog<bool>(
      context: context,
      builder: (d) => StatefulBuilder(
        builder: (d, set) => AlertDialog(
          title: const Text('Bài viết mới'),
          content: SingleChildScrollView(
            child: Column(mainAxisSize: MainAxisSize.min, children: [
              DropdownButton<String>(
                value: type,
                isExpanded: true,
                items: const [
                  DropdownMenuItem(value: 'TUTORIAL', child: Text('Hướng dẫn')),
                  DropdownMenuItem(value: 'ARTICLE', child: Text('Bài viết')),
                  DropdownMenuItem(value: 'EQUIPMENT_REVIEW', child: Text('Review thiết bị')),
                ],
                onChanged: (v) => set(() => type = v ?? type),
              ),
              TextField(controller: title, decoration: const InputDecoration(labelText: 'Tiêu đề')),
              TextField(controller: body, maxLines: 5, decoration: const InputDecoration(labelText: 'Nội dung')),
            ]),
          ),
          actions: [TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Hủy')), FilledButton(onPressed: () => Navigator.pop(d, true), child: const Text('Đăng'))],
        ),
      ),
    );
    if (yes == true && await guard(context, () => api.post('/api/community/posts', {'post_type': type, 'title': title.text.trim(), 'content': body.text.trim()}), ok: 'Đã đăng bài') != null) _reload();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('Bài viết')),
        floatingActionButton: FloatingActionButton.extended(onPressed: _create, icon: const Icon(Icons.edit), label: const Text('Viết bài')),
        body: AsyncList<List<dynamic>>(
          future: _f,
          onRetry: _reload,
          builder: (list) => ListView(padding: const EdgeInsets.all(12), children: [
            for (final p in list)
              Card(
                child: ListTile(
                  title: Text('${p['title']}'),
                  subtitle: Text('${p['post_type']} · ${p['author_name'] ?? ''}'),
                  onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => PostScreen(id: p['post_id']))),
                ),
              ),
          ]),
        ),
      );
}
