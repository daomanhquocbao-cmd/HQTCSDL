import 'package:flutter_test/flutter_test.dart';
import 'package:film_photo_app/format.dart';

void main() {
  test('định dạng tiền và trạng thái', () {
    expect(money(250000), contains('250'));
    expect(statusLabel('CONFIRMED'), 'Đã xác nhận');
    expect(isoLocal(DateTime(2026, 11, 25, 9)), '2026-11-25T09:00:00');
  });
}
