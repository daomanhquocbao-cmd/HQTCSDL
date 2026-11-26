import 'package:flutter/material.dart';

import 'ai_chat_screen.dart';
import 'bookings_screen.dart';
import 'community_screen.dart';
import 'explore_screen.dart';
import 'profile_screen.dart';

class HomeShell extends StatefulWidget {
  final VoidCallback onLogout;
  const HomeShell({super.key, required this.onLogout});
  @override
  State<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends State<HomeShell> {
  int _i = 0;
  @override
  Widget build(BuildContext context) {
    final pages = [
      const ExploreScreen(),
      const BookingsScreen(),
      const CommunityScreen(),
      const AiChatScreen(),
      ProfileScreen(onLogout: widget.onLogout),
    ];
    return Scaffold(
      body: IndexedStack(index: _i, children: pages),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _i,
        onDestinationSelected: (v) => setState(() => _i = v),
        destinations: const [
          NavigationDestination(icon: Icon(Icons.search), label: 'Khám phá'),
          NavigationDestination(icon: Icon(Icons.event_note), label: 'Đơn của tôi'),
          NavigationDestination(icon: Icon(Icons.forum), label: 'Cộng đồng'),
          NavigationDestination(icon: Icon(Icons.smart_toy), label: 'Trợ lý AI'),
          NavigationDestination(icon: Icon(Icons.person), label: 'Hồ sơ'),
        ],
      ),
    );
  }
}
