import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

/// Địa chỉ backend. Emulator Android dùng 10.0.2.2 để trỏ về máy tính; máy thật dùng IP LAN của máy chạy backend.
/// Đổi ngay trong ứng dụng ở màn hình đăng nhập (biểu tượng ⚙) hoặc truyền --dart-define=API_BASE=http://...
const String kDefaultBase = String.fromEnvironment('API_BASE', defaultValue: 'http://10.0.2.2:8000');

class ApiError implements Exception {
  final int status;
  final String message;
  ApiError(this.status, this.message);
  @override
  String toString() => message;
}

class Api {
  Api._();
  static final Api instance = Api._();

  String base = kDefaultBase;
  String? token;
  Map<String, dynamic>? user;

  Future<void> load() async {
    final p = await SharedPreferences.getInstance();
    base = p.getString('api_base') ?? kDefaultBase;
    token = p.getString('token');
    final u = p.getString('user');
    user = u == null ? null : jsonDecode(u) as Map<String, dynamic>;
  }

  Future<void> setBase(String value) async {
    base = value.trim().replaceAll(RegExp(r'/+$'), '');
    (await SharedPreferences.getInstance()).setString('api_base', base);
  }

  Future<void> _save(Map<String, dynamic> data) async {
    token = data['access_token'] as String;
    user = Map<String, dynamic>.from(data['user'] as Map);
    final p = await SharedPreferences.getInstance();
    await p.setString('token', token!);
    await p.setString('user', jsonEncode(user));
  }

  Future<void> logout() async {
    token = null;
    user = null;
    final p = await SharedPreferences.getInstance();
    await p.remove('token');
    await p.remove('user');
  }

  Map<String, String> get _headers => {
        'Content-Type': 'application/json',
        if (token != null) 'Authorization': 'Bearer $token',
      };

  Future<dynamic> _send(String method, String path, {Map<String, dynamic>? query, Object? body}) async {
    final q = <String, String>{};
    query?.forEach((k, v) {
      if (v != null && '$v'.isNotEmpty) q[k] = '$v';
    });
    final uri = Uri.parse('$base$path').replace(queryParameters: q.isEmpty ? null : q);
    late http.Response r;
    try {
      final req = http.Request(method, uri)..headers.addAll(_headers);
      if (body != null) req.body = jsonEncode(body);
      r = await http.Response.fromStream(await req.send().timeout(const Duration(seconds: 15)));
    } catch (_) {
      throw ApiError(0, 'Không kết nối được máy chủ ($base). Kiểm tra backend và địa chỉ API.');
    }
    final text = utf8.decode(r.bodyBytes);
    final data = text.isEmpty ? null : jsonDecode(text);
    if (r.statusCode >= 400) {
      if (r.statusCode == 401 && token != null) await logout();
      throw ApiError(r.statusCode, _detail(data) ?? 'Lỗi ${r.statusCode}');
    }
    return data;
  }

  String? _detail(dynamic d) {
    if (d is Map) {
      final x = d['detail'] ?? d['message'];
      if (x is String) return x;
      if (x is List && x.isNotEmpty) return x.map((e) => e is Map ? (e['msg'] ?? '$e') : '$e').join('; ');
    }
    return null;
  }

  Future<dynamic> get(String path, {Map<String, dynamic>? query}) => _send('GET', path, query: query);
  Future<dynamic> post(String path, [Object? body]) => _send('POST', path, body: body ?? {});
  Future<dynamic> delete(String path) => _send('DELETE', path);
  Future<dynamic> patch(String path, Object body) => _send('PATCH', path, body: body);
  Future<dynamic> put(String path, Object body) => _send('PUT', path, body: body);

  String get role => '${user?['role'] ?? ''}'.toUpperCase();

  Future<void> login(String username, String password) async {
    await _save(Map<String, dynamic>.from(
        await _send('POST', '/api/users/login', body: {'username': username, 'password': password})));
  }

  Future<void> register(Map<String, dynamic> body) async {
    await _send('POST', '/api/users/register', body: body);
    await login(body['username'] as String, body['password'] as String);
  }

  Future<void> loginWithGoogleToken(String idToken) async {
    await _save(Map<String, dynamic>.from(await _send('POST', '/api/auth/google', body: {'id_token': idToken})));
  }

  Future<Map<String, dynamic>> googleConfig() async =>
      Map<String, dynamic>.from(await _send('GET', '/api/auth/google/config'));
}

final api = Api.instance;
