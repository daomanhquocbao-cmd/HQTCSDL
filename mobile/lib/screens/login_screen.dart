import 'package:flutter/material.dart';
import 'package:google_sign_in/google_sign_in.dart';

import '../api.dart';
import '../widgets.dart';

class LoginScreen extends StatefulWidget {
  final VoidCallback onDone;
  const LoginScreen({super.key, required this.onDone});
  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _user = TextEditingController(), _pass = TextEditingController();
  final _email = TextEditingController(), _name = TextEditingController();
  bool _register = false, _busy = false;
  String? _googleClientId;

  @override
  void initState() {
    super.initState();
    _loadGoogle();
  }

  Future<void> _loadGoogle() async {
    try {
      final c = await api.googleConfig();
      if (mounted && c['enabled'] == true) setState(() => _googleClientId = c['client_id'] as String?);
    } catch (_) {/* server cũ hoặc chưa chạy: bỏ qua nút Google */}
  }

  Future<void> _submit() async {
    setState(() => _busy = true);
    final ok = await guard(context, () async {
      if (_register) {
        await api.register({
          'username': _user.text.trim(),
          'password': _pass.text,
          'email': _email.text.trim(),
          'full_name': _name.text.trim(),
          'role': 'CUSTOMER',
        });
      } else {
        await api.login(_user.text.trim(), _pass.text);
      }
      return true;
    });
    if (mounted) setState(() => _busy = false);
    if (ok == true) widget.onDone();
  }

  Future<void> _google() async {
    final ok = await guard(context, () async {
      final acc = await GoogleSignIn(scopes: ['email'], serverClientId: _googleClientId).signIn();
      if (acc == null) return false;
      final tok = (await acc.authentication).idToken;
      if (tok == null) throw ApiError(0, 'Google không trả về id_token. Kiểm tra cấu hình Client ID.');
      await api.loginWithGoogleToken(tok);
      return true;
    });
    if (ok == true) widget.onDone();
  }

  Future<void> _editBase() async {
    final c = TextEditingController(text: api.base);
    final v = await showDialog<String>(
      context: context,
      builder: (d) => AlertDialog(
        title: const Text('Địa chỉ API'),
        content: TextField(controller: c, decoration: const InputDecoration(hintText: 'http://192.168.1.10:8000')),
        actions: [
          TextButton(onPressed: () => Navigator.pop(d), child: const Text('Hủy')),
          FilledButton(onPressed: () => Navigator.pop(d, c.text), child: const Text('Lưu')),
        ],
      ),
    );
    if (v != null && v.trim().isNotEmpty) {
      await api.setBase(v);
      _loadGoogle();
      if (mounted) setState(() {});
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(actions: [IconButton(onPressed: _editBase, icon: const Icon(Icons.settings), tooltip: 'Địa chỉ API')]),
        body: SafeArea(
          child: ListView(padding: const EdgeInsets.all(24), children: [
            const Icon(Icons.camera_roll, size: 64, color: kBrand),
            const SizedBox(height: 8),
            Text('Film Photography', textAlign: TextAlign.center, style: Theme.of(context).textTheme.headlineSmall),
            Text(_register ? 'Tạo tài khoản khách hàng' : 'Đăng nhập (khách hàng, nhà cung cấp, chuyên gia, quản trị)',
                textAlign: TextAlign.center),
            const SizedBox(height: 24),
            if (_register) ...[
              TextField(controller: _name, decoration: const InputDecoration(labelText: 'Họ và tên')),
              TextField(controller: _email, keyboardType: TextInputType.emailAddress, decoration: const InputDecoration(labelText: 'Email')),
            ],
            TextField(controller: _user, decoration: const InputDecoration(labelText: 'Tên đăng nhập')),
            TextField(controller: _pass, obscureText: true, decoration: const InputDecoration(labelText: 'Mật khẩu (≥ 8 ký tự)')),
            const SizedBox(height: 20),
            FilledButton(onPressed: _busy ? null : _submit, child: Text(_busy ? 'Đang xử lý…' : (_register ? 'Đăng ký' : 'Đăng nhập'))),
            if (_googleClientId != null && !_register)
              OutlinedButton.icon(onPressed: _google, icon: const Icon(Icons.login), label: const Text('Đăng nhập bằng Google')),
            TextButton(
                onPressed: () => setState(() => _register = !_register),
                child: Text(_register ? 'Đã có tài khoản? Đăng nhập' : 'Chưa có tài khoản? Đăng ký')),
          ]),
        ),
      );
}
