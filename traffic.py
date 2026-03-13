import time
from ostinato.core import ost_pb, DroneProxy
# Import các thư viện giao thức (Protocol Buffers)
from ostinato.protocols.mac_pb2 import mac
from ostinato.protocols.ip4_pb2 import ip4

# ==========================================
# CẤU HÌNH CƠ BẢN (BẠN CẦN SỬA PHẦN NÀY)
# ==========================================
DRONE_IP = '127.0.0.1'
TX_PORT = 1  # ĐỔI THÀNH ID CỦA CARD MẠNG BẠN MUỐN PHÁT TRAFFIC (Lấy từ bước trước)


def start_background_traffic():
    # 1. Kết nối tới Drone
    drone = DroneProxy(DRONE_IP)
    drone.connect()
    print(f"[+] Đã kết nối tới Ostinato Drone tại {DRONE_IP}")

    # Khởi tạo đối tượng Port
    tx_port = ost_pb.PortIdList()
    tx_port.port_id.add().id = TX_PORT

    # Khởi tạo đối tượng Stream
    stream_id = ost_pb.StreamIdList()
    stream_id.port_id.copy_from(tx_port.port_id[0])
    stream_id.stream_id.add().id = 1

    # Xóa các luồng cũ (nếu có) trên Port này để làm sạch
    drone.deleteStream(stream_id)
    # Thêm luồng mới
    drone.addStream(stream_id)

    # ==========================================
    # 2. XÂY DỰNG GÓI TIN (PACKET BUILDER)
    # ==========================================
    stream_cfg = ost_pb.StreamConfigList()
    stream_cfg.port_id.copy_from(tx_port.port_id[0])
    s = stream_cfg.stream.add()
    s.stream_id.id = stream_id.stream_id[0].id
    s.core.is_enabled = True

    # Thêm Lớp MAC (Layer 2)
    p = s.protocol.add()
    p.protocol_id.id = ost_pb.Protocol.kMacFieldNumber

    # Thêm Lớp Ethernet
    p = s.protocol.add()
    p.protocol_id.id = ost_pb.Protocol.kEth2FieldNumber

    # Thêm Lớp IPv4 (Layer 3)
    p = s.protocol.add()
    p.protocol_id.id = ost_pb.Protocol.kIp4FieldNumber
    # Cấu hình IP (Ostinato dùng mã Hex cho IP. 0xC0A80101 = 192.168.1.1)
    p.Extensions[ip4].src_ip = 0xC0A80101  # IP Nguồn giả lập
    p.Extensions[ip4].dst_ip = 0xC0A80102  # IP Đích giả lập

    # Thêm Lớp UDP (Layer 4)
    p = s.protocol.add()
    p.protocol_id.id = ost_pb.Protocol.kUdpFieldNumber

    # ==========================================
    # 3. CẤU HÌNH BĂNG THÔNG & LƯU LƯỢNG
    # ==========================================
    # Đặt num_packets = 0 để luồng chạy LIÊN TỤC không bao giờ dừng
    s.control.num_packets = 0
    # Tốc độ: 1000 gói tin mỗi giây (Bạn có thể tăng giảm tùy ý)
    s.control.packets_per_sec = 1000

    # Gửi cấu hình xuống Drone
    drone.modifyStream(stream_cfg)
    print(f"[+] Đã nạp cấu hình: UDP, Tốc độ 1000 packets/sec vào Port {TX_PORT}")

    # ==========================================
    # 4. BẮT ĐẦU PHÁT VÀ DUY TRÌ LƯU LƯỢNG
    # ==========================================
    tx_cfg = ost_pb.TransmitConfig()
    tx_cfg.port_id_list.extend(tx_port.port_id)
    tx_cfg.tx_state = True
    drone.modifyTransmit(tx_cfg)

    print("\n🚀 ĐANG PHÁT LƯU LƯỢNG NỀN... (Nhấn Ctrl+C để dừng script và ngắt traffic)")

    try:
        # Vòng lặp vô hạn để giữ script chạy. Traffic đang được Drone tự động phát ngầm.
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[!] Đã nhận lệnh dừng từ bàn phím (Ctrl+C)...")
    finally:
        # Khi thoát script, gửi lệnh tắt traffic để tránh Drone phát mãi mãi
        tx_cfg.tx_state = False
        drone.modifyTransmit(tx_cfg)
        print("[-] Đã dừng phát lưu lượng nền thành công. Tạm biệt!")


if __name__ == "__main__":
    start_background_traffic()