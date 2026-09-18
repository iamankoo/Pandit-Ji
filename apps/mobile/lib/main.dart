import 'package:flutter/material.dart';

/// Pandit Ji mobile app entry point.
///
/// Phase 3 (Repository & Engineering Foundation) scope only: a placeholder
/// home screen. No product screens are built yet -- see `Phases.md` for
/// when Kundli, chat, Panchang, etc. screens are added.
void main() {
  runApp(const PanditJiApp());
}

class PanditJiApp extends StatelessWidget {
  const PanditJiApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Pandit Ji',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.deepOrange),
      ),
      home: const FoundationHomePage(),
    );
  }
}

class FoundationHomePage extends StatelessWidget {
  const FoundationHomePage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Pandit Ji')),
      body: const Center(
        child: Padding(
          padding: EdgeInsets.all(24.0),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Text(
                'Mobile application foundation',
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
              ),
              SizedBox(height: 8),
              Text('Phase 3 — Repository & Engineering Foundation'),
              SizedBox(height: 8),
              Text('No product screens have been built yet.'),
            ],
          ),
        ),
      ),
    );
  }
}
