import 'package:intl/intl.dart';

final _money = NumberFormat.decimalPattern('vi_VN');
String money(num? v) => '${_money.format((v ?? 0).round())}đ';

DateTime? parseDt(dynamic v) => v == null ? null : DateTime.tryParse('$v');
String fmtDateTime(dynamic v) {
  final d = parseDt(v);
  return d == null ? '—' : DateFormat('dd/MM/yyyy HH:mm').format(d);
}

String fmtDate(DateTime d) => DateFormat('dd/MM/yyyy').format(d);

/// Gửi lên backend dạng ISO không múi giờ (backend lưu giờ địa phương).
String isoLocal(DateTime d) => DateFormat("yyyy-MM-dd'T'HH:mm:ss").format(d);

const statusLabels = {
  'PENDING': 'Chờ duyệt',
  'CONFIRMED': 'Đã xác nhận',
  'IN_USE': 'Đang sử dụng',
  'COMPLETED': 'Hoàn tất',
  'CANCELLED': 'Đã hủy',
};
String statusLabel(String? s) => statusLabels[s] ?? (s ?? '');

const roomTypeLabels = {'STUDIO': 'Phòng chụp', 'DARKROOM': 'Phòng tối'};
