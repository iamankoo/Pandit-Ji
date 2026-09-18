import 'package:flutter_test/flutter_test.dart';
import 'package:pandit_ji_mobile/main.dart';

void main() {
  testWidgets('renders the Phase 3 foundation placeholder', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(const PanditJiApp());

    expect(find.text('Pandit Ji'), findsOneWidget);
    expect(find.text('Mobile application foundation'), findsOneWidget);
  });
}
