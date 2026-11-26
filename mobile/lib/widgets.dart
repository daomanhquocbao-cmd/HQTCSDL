import 'package:flutter/material.dart';

const kBrand = Color(0xFFE8590C);

void snack(BuildContext c, String msg, {bool bad = false}) {
  ScaffoldMessenger.of(c)
    ..hideCurrentSnackBar()
    ..showSnackBar(SnackBar(content: Text(msg), backgroundColor: bad ? Colors.red.shade700 : null));
}

/// Chạy một tác vụ async, hiện lỗi dưới dạng snackbar. Trả về null nếu lỗi.
Future<T?> guard<T>(BuildContext c, Future<T> Function() job, {String? ok}) async {
  try {
    final r = await job();
    if (ok != null && c.mounted) snack(c, ok);
    return r;
  } catch (e) {
    if (c.mounted) snack(c, '$e', bad: true);
    return null;
  }
}

class Chip2 extends StatelessWidget {
  final String text;
  final Color color;
  const Chip2(this.text, {super.key, this.color = kBrand});
  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
        decoration: BoxDecoration(color: color.withOpacity(.12), borderRadius: BorderRadius.circular(20)),
        child: Text(text, style: TextStyle(color: color, fontSize: 12, fontWeight: FontWeight.w600)),
      );
}

Color statusColor(String? s) => switch (s) {
      'CONFIRMED' => Colors.green.shade700,
      'IN_USE' => Colors.blue.shade700,
      'COMPLETED' => Colors.grey.shade700,
      'CANCELLED' => Colors.red.shade700,
      _ => Colors.orange.shade800,
    };

class AsyncList<T> extends StatelessWidget {
  final Future<T> future;
  final Widget Function(T data) builder;
  final VoidCallback onRetry;
  const AsyncList({super.key, required this.future, required this.builder, required this.onRetry});
  @override
  Widget build(BuildContext context) => FutureBuilder<T>(
        future: future,
        builder: (c, s) {
          if (s.connectionState != ConnectionState.done) return const Center(child: CircularProgressIndicator());
          if (s.hasError) {
            return Center(
                child: Padding(
              padding: const EdgeInsets.all(24),
              child: Column(mainAxisSize: MainAxisSize.min, children: [
                Text('${s.error}', textAlign: TextAlign.center),
                const SizedBox(height: 12),
                FilledButton(onPressed: onRetry, child: const Text('Thử lại')),
              ]),
            ));
          }
          return builder(s.data as T);
        },
      );
}

/// Khung chung cho các tab đơn giản của vai trò nhà cung cấp / chuyên gia / quản trị.
class Pane extends StatelessWidget {
  final String title;
  final Widget child;
  final List<Widget>? actions;
  const Pane({super.key, required this.title, required this.child, this.actions});
  @override
  Widget build(BuildContext context) => Scaffold(appBar: AppBar(title: Text(title), actions: actions), body: child);
}

class KpiCard extends StatelessWidget {
  final String label, value;
  const KpiCard(this.label, this.value, {super.key});
  @override
  Widget build(BuildContext context) => Card(
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(label, style: Theme.of(context).textTheme.bodySmall),
            const SizedBox(height: 4),
            Text(value, style: Theme.of(context).textTheme.titleLarge?.copyWith(color: kBrand, fontWeight: FontWeight.w700)),
          ]),
        ),
      );
}

Future<String?> askText(BuildContext c, String title, {String hint = '', int lines = 1}) {
  final ctl = TextEditingController();
  return showDialog<String>(
    context: c,
    builder: (d) => AlertDialog(
      title: Text(title),
      content: TextField(controller: ctl, autofocus: true, maxLines: lines, decoration: InputDecoration(hintText: hint)),
      actions: [TextButton(onPressed: () => Navigator.pop(d), child: const Text('Hủy')), FilledButton(onPressed: () => Navigator.pop(d, ctl.text), child: const Text('OK'))],
    ),
  );
}

Future<bool> confirmDlg(BuildContext c, String title) async =>
    await showDialog<bool>(
      context: c,
      builder: (d) => AlertDialog(
        title: Text(title),
        actions: [TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Không')), FilledButton(onPressed: () => Navigator.pop(d, true), child: const Text('Đồng ý'))],
      ),
    ) ??
    false;
