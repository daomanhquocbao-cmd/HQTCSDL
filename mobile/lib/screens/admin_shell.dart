import 'package:flutter/material.dart';

import '../api.dart';
import '../widgets.dart';

class AdminShell extends StatefulWidget {
  final VoidCallback onLogout;
  const AdminShell({super.key, required this.onLogout});
  @override
  State<AdminShell> createState() => _AdminShellState();
}

class _AdminShellState extends State<AdminShell> {
  int _i = 0;
  @override
  Widget build(BuildContext context) => Scaffold(
        body: IndexedStack(index: _i, children: [
          const _AdminOverview(),
          const _Approvals(),
          const _Settings(),
          Pane(
            title: 'Hồ sơ',
            child: ListView(children: [
              ListTile(leading: const CircleAvatar(child: Icon(Icons.admin_panel_settings)), title: Text('${api.user?['full_name'] ?? ''}'), subtitle: Text('${api.user?['email'] ?? ''}')),
              ListTile(leading: const Icon(Icons.logout), title: const Text('Đăng xuất'), onTap: widget.onLogout),
            ]),
          ),
        ]),
        bottomNavigationBar: NavigationBar(
          selectedIndex: _i,
          onDestinationSelected: (v) => setState(() => _i = v),
          destinations: const [
            NavigationDestination(icon: Icon(Icons.dashboard), label: 'Tổng quan'),
            NavigationDestination(icon: Icon(Icons.verified_user), label: 'Duyệt'),
            NavigationDestination(icon: Icon(Icons.tune), label: 'Cấu hình'),
            NavigationDestination(icon: Icon(Icons.person), label: 'Hồ sơ'),
          ],
        ),
      );
}

class _AdminOverview extends StatefulWidget {
  const _AdminOverview();
  @override
  State<_AdminOverview> createState() => _AdminOverviewState();
}

class _AdminOverviewState extends State<_AdminOverview> {
  late Future<Map> _f = _load();
  Future<Map> _load() async => Map.from(await api.get('/api/admin/overview'));
  void _reload() => setState(() => _f = _load());
  @override
  Widget build(BuildContext context) => Pane(
        title: 'Tổng quan hệ thống',
        actions: [IconButton(onPressed: _reload, icon: const Icon(Icons.refresh))],
        child: AsyncList<Map>(
          future: _f,
          onRetry: _reload,
          builder: (o) => GridView.count(crossAxisCount: 2, padding: const EdgeInsets.all(12), childAspectRatio: 1.6, children: [
            KpiCard('Khách hàng', '${o['customers']}'),
            KpiCard('Tổng số đơn', '${o['reservations']}'),
            KpiCard('Nhà cung cấp chờ duyệt', '${o['pending_providers']}'),
            KpiCard('Studio chờ duyệt', '${o['pending_studios']}'),
            KpiCard('Nhà cung cấp hoạt động', '${o['active_providers']}'),
            KpiCard('Khiếu nại đang mở', '${o['open_disputes']}'),
          ]),
        ),
      );
}

class _Approvals extends StatefulWidget {
  const _Approvals();
  @override
  State<_Approvals> createState() => _ApprovalsState();
}

class _ApprovalsState extends State<_Approvals> {
  late Future<List<dynamic>> _f = _load();
  Future<List<dynamic>> _load() async => [
        await api.get('/api/admin/providers', query: {'status': 'PENDING'}),
        await api.get('/api/admin/studios', query: {'status': 'PENDING'}),
      ];
  void _reload() => setState(() => _f = _load());

  Future<void> _do(Future<dynamic> Function() job, String ok) async {
    if (await guard(context, job, ok: ok) != null) _reload();
  }

  @override
  Widget build(BuildContext context) => Pane(
        title: 'Duyệt nhà cung cấp & studio',
        actions: [IconButton(onPressed: _reload, icon: const Icon(Icons.refresh))],
        child: AsyncList<List<dynamic>>(
          future: _f,
          onRetry: _reload,
          builder: (r) {
            final providers = r[0] as List, studios = r[1] as List;
            if (providers.isEmpty && studios.isEmpty) return const Center(child: Text('Không có mục nào chờ duyệt'));
            return ListView(padding: const EdgeInsets.all(12), children: [
              for (final p in providers)
                Card(
                  child: ListTile(
                    title: Text('${p['full_name']} (${p['username']})'),
                    subtitle: Text('Nhà cung cấp · ${p['email']}'),
                    trailing: FilledButton(onPressed: () => _do(() => api.patch('/api/admin/providers/${p['user_id']}', {'status': 'ACTIVE'}), 'Đã duyệt nhà cung cấp'), child: const Text('Duyệt')),
                  ),
                ),
              for (final s in studios)
                Card(
                  child: ListTile(
                    title: Text('${s['name']}'),
                    subtitle: Text('${s['address']}, ${s['city']}\n${s['provider_name']}'),
                    isThreeLine: true,
                    trailing: Wrap(spacing: 4, children: [
                      IconButton(icon: const Icon(Icons.check_circle, color: Colors.green), onPressed: () => _do(() => api.patch('/api/admin/studios/${s['studio_id']}', {'status': 'APPROVED'}), 'Đã duyệt studio')),
                      IconButton(icon: const Icon(Icons.cancel, color: Colors.red), onPressed: () => _do(() => api.patch('/api/admin/studios/${s['studio_id']}', {'status': 'REJECTED'}), 'Đã từ chối')),
                    ]),
                  ),
                ),
            ]);
          },
        ),
      );
}

class _Settings extends StatefulWidget {
  const _Settings();
  @override
  State<_Settings> createState() => _SettingsState();
}

class _SettingsState extends State<_Settings> {
  late Future<List<dynamic>> _f = _load();
  Future<List<dynamic>> _load() async => (await api.get('/api/admin/settings')) as List;
  void _reload() => setState(() => _f = _load());

  Future<void> _set(String key, Object value) async {
    if (await guard(context, () => api.put('/api/admin/settings/$key', {'value': value}), ok: 'Đã lưu') != null) _reload();
  }

  @override
  Widget build(BuildContext context) => Pane(
        title: 'Cấu hình hệ thống',
        child: AsyncList<List<dynamic>>(
          future: _f,
          onRetry: _reload,
          builder: (list) => ListView(children: [
            for (final s in list)
              (s['value_type'] == 'BOOL')
                  ? SwitchListTile(title: Text('${s['setting_key']}'), subtitle: Text('${s['description'] ?? ''}'), value: s['value'] == true, onChanged: (v) => _set('${s['setting_key']}', v))
                  : ListTile(
                      title: Text('${s['setting_key']}'),
                      subtitle: Text('${s['description'] ?? ''}'),
                      trailing: Text('${s['value']}', style: const TextStyle(fontWeight: FontWeight.bold)),
                      onTap: () async {
                        final v = await askText(context, '${s['setting_key']}', hint: '${s['value']}');
                        if (v == null || v.trim().isEmpty) return;
                        final n = num.tryParse(v.trim());
                        await _set('${s['setting_key']}', n ?? v.trim());
                      },
                    ),
          ]),
        ),
      );
}
