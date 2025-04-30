import socket, struct, time, select

class ICMPPing:
    ICMP_ECHO_REQ = 8
    ICMP_CODE = socket.getprotobyname('icmp')

    def __init__(self, target, timeout=1):
        self.target = target
        self.timeout = timeout
        self.seq = 1
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, self.ICMP_CODE)
        self.sock.settimeout(self.timeout)

    def checksum(self, data: bytes) -> int:
        # 计算 ICMP 校验和
        csum = 0
        countTo = (len(data) // 2) * 2
        count = 0
        while count < countTo:
            thisVal = data[count + 1] * 256 + data[count]
            csum += thisVal
            csum &= 0xffffffff
            count += 2
        if countTo < len(data):
            csum += data[len(data) - 1]
            csum &= 0xffffffff
        csum = (csum >> 16) + (csum & 0xffff)
        csum += (csum >> 16)
        return ~csum & 0xffff

    def create_packet(self) -> bytes:
        header = struct.pack('!BBHHH', self.ICMP_ECHO_REQ, 0, 0, 0, self.seq)
        payload = struct.pack('d', time.time())
        chk = self.checksum(header + payload)
        header = struct.pack('!BBHHH', self.ICMP_ECHO_REQ, 0, chk, 0, self.seq)
        return header + payload

    def ping_once(self) -> float:
        packet = self.create_packet()
        self.sock.sendto(packet, (self.target, 1))
        start = time.time()
        while True:
            ready = select.select([self.sock], [], [], self.timeout)
            if ready[0] == []:
                return float('nan')  # 超时
            recv, _ = self.sock.recvfrom(1024)
            timeRecv = time.time()
            # 跳过 IP 头部，直接读取 ICMP 中的时间戳
            rtt = (timeRecv - struct.unpack('d', recv[-8:])[0]) * 1000
            return rtt
