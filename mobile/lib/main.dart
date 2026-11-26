import 'package:flutter/material.dart';

import 'api.dart';
import 'screens/admin_shell.dart';
import 'screens/expert_shell.dart';
import 'screens/home_shell.dart';
import 'screens/provider_shell.dart';
import 'screens/login_screen.dart';
import 'widgets.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await api.load();
  runApp(const FilmApp());
}

class FilmApp extends StatefulWidget {
  const FilmApp({super.key});
  @override
  State<FilmApp> createState() => _FilmAppState();
}

class _FilmAppState extends State<FilmApp> {
  bool get _in => api.token != null && ['CUSTOMER', 'PROVIDER', 'EXPERT', 'ADMIN'].contains(api.role);

  Future<void> _logout() async {
    await api.logout();
    setState(() {});
  }

  Widget _home() => switch (api.role) {
        'PROVIDER' => ProviderShell(onLogout: _logout),
        'EXPERT' => ExpertShell(onLogout: _logout),
        'ADMIN' => AdminShell(onLogout: _logout),
        _ => HomeShell(onLogout: _logout),
      };

  @override
  Widget build(BuildContext context) => MaterialApp(
        title: 'Film Photography',
        debugShowCheckedModeBanner: false,
        theme: ThemeData(colorSchemeSeed: kBrand, useMaterial3: true),
        home: _in ? _home() : LoginScreen(onDone: () => setState(() {})),
      );
}
