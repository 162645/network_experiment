# import socket, struct, time, select
#
# class ICMPTraceroute:
#     ICMP_ECHO_REQ = 8
#     ICMP_ECHO_REPLY = 0
#     ICMP_TIME_EXCEEDED = 11
#     ICMP_CODE = socket.getprotobyname('icmp')
#
#     def __init__(self, target, timeout=1, max_hops=30, probes_per_hop=3):
#         self.target = target
#         self.timeout = timeout
#         self.max_hops = max_hops
#         self.probes_per_hop = probes_per_hop
#         self.seq = 1
#         self.sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, self.ICMP_CODE)
#         self.sock.settimeout(self.timeout)
#         self.dest_ip = socket.gethostbyname(self.target)
#
#     def checksum(self, data: bytes) -> int:
#         # 计算 ICMP 校验和
#         csum = 0
#         countTo = (len(data) // 2) * 2
#         count = 0
#         while count < countTo:
#             thisVal = data[count + 1] * 256 + data[count]
#             csum += thisVal
#             csum &= 0xffffffff
#             count += 2
#         if countTo < len(data):
#             csum += data[len(data) - 1]
#             csum &= 0xffffffff
#         csum = (csum >> 16) + (csum & 0xffff)
#         csum += (csum >> 16)
#         return ~csum & 0xffff
#
#     def create_packet(self) -> bytes:
#         # 构造 ICMP Echo Request 数据包
#         header = struct.pack('!BBHHH', self.ICMP_ECHO_REQ, 0, 0, 0, self.seq)
#         payload = struct.pack('d', time.time())
#         chk = self.checksum(header + payload)
#         header = struct.pack('!BBHHH', self.ICMP_ECHO_REQ, 0, chk, 0, self.seq)
#         return header + payload
#
#     def trace(self):
#         # 主执行逻辑
#         for ttl in range(1, self.max_hops + 1):
#             self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_TTL, struct.pack('I', ttl))
#             rtts = []
#             addrs = []
#             for _ in range(self.probes_per_hop):
#                 packet = self.create_packet()
#                 self.seq += 1
#                 try:
#                     self.sock.sendto(packet, (self.target, 0))
#                     start = time.time()
#                     ready = select.select([self.sock], [], [], self.timeout)
#                     if ready[0] == []:
#                         rtts.append(None)
#                         addrs.append(None)
#                         continue
#                     recv, addr = self.sock.recvfrom(1024)
#                     timeRecv = time.time()
#                     ip_header = recv[:20]
#                     icmp_header = recv[20:28]
#                     type, code, checksum, p_id, seq = struct.unpack('!BBHHH', icmp_header)
#                     if type == self.ICMP_TIME_EXCEEDED or type == self.ICMP_ECHO_REPLY:
#                         rtts.append((timeRecv - start) * 1000)
#                         addrs.append(addr[0])
#                     else:
#                         rtts.append(None)
#                         addrs.append(None)
#                 except socket.timeout:
#                     rtts.append(None)
#                     addrs.append(None)
#
#             # 统计这一跳的 IP 和 RTT
#             display_addr = next((a for a in addrs if a), '*')
#             display_rtts = ['*' if rtt is None else f"{rtt:.1f}ms" for rtt in rtts]
#             print(f"{ttl:2}  {display_addr:>15}  {'  '.join(display_rtts)}")
#
#             if display_addr == self.dest_ip:
#                 break
#
# if __name__ == "__main__":
#     tracer = ICMPTraceroute('8.8.8.8', timeout=2, max_hops=30, probes_per_hop=5)
#     tracer.trace()

# icmp_traceroute.py
import socket, struct, time, select, pandas as pd

class ICMPTraceroute:
    ICMP_ECHO_REQ      = 8
    ICMP_TIME_EXCEEDED = 11
    ICMP_CODE          = socket.getprotobyname('icmp')

    def __init__(self, target, timeout=1, max_hops=30, probes=3):
        """
        target   – 目标域名或 IP
        timeout  – 探针超时（秒）
        max_hops – 最大跳数
        probes   – 每跳探针数
        """
        self.target   = target
        self.timeout  = timeout
        self.max_hops = max_hops
        self.probes   = probes
        self.seq      = 1
        # 单一原始 ICMP 套接字（发送 & 接收）
        self.sock = socket.socket(socket.AF_INET,
                                  socket.SOCK_RAW,
                                  self.ICMP_CODE)
        self.sock.settimeout(self.timeout)
        self.dest_ip = socket.gethostbyname(self.target)

    def checksum(self, data: bytes) -> int:
        """计算 ICMP 校验和"""
        csum = 0
        countTo = (len(data)//2)*2
        for i in range(0, countTo, 2):
            csum += data[i+1]*256 + data[i]
            csum &= 0xffffffff
        if countTo < len(data):
            csum += data[-1]
            csum &= 0xffffffff
        csum = (csum>>16) + (csum & 0xffff)
        csum += (csum>>16)
        return ~csum & 0xffff

    def create_packet(self) -> bytes:
        """构造 ICMP Echo Request 报文"""
        header = struct.pack('!BBHHH',
                             self.ICMP_ECHO_REQ, 0, 0, 0, self.seq)
        payload = struct.pack('d', time.time())
        chk = self.checksum(header + payload)
        return struct.pack('!BBHHH',
                           self.ICMP_ECHO_REQ, 0, chk, 0, self.seq) + payload

    def trace(self) -> pd.DataFrame:
        """
        执行 Traceroute，返回 DataFrame：
        index = ttl，columns = ['ip','rtt_mean','rtt_std','loss_rate']
        """
        rows = []
        for ttl in range(1, self.max_hops+1):
            # 在同一套接字上设置 TTL
            self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_TTL, struct.pack('I', ttl))

            rtts, addrs = [], []
            for _ in range(self.probes):
                pkt = self.create_packet()
                self.seq += 1
                send_t = time.time()
                try:
                    # 发送 & 接收同用 self.sock
                    self.sock.sendto(pkt, (self.target, 0))
                    ready = select.select([self.sock], [], [], self.timeout)
                    if not ready[0]:
                        rtts.append(float('nan'))
                        addrs.append(None)
                    else:
                        recv, addr = self.sock.recvfrom(1024)
                        rtts.append((time.time() - send_t)*1000)
                        addrs.append(addr[0])
                except Exception:
                    rtts.append(float('nan'))
                    addrs.append(None)

            loss = sum(1 for x in rtts if pd.isna(x)) / self.probes
            ip   = next((a for a in addrs if a), '*')
            s    = pd.Series(rtts)
            mean = s.dropna().mean() if loss < 1 else float('nan')
            std  = s.dropna().std()  if loss < 1 else float('nan')

            # 控制台输出
            disp = [f"{x:.1f}ms" if not pd.isna(x) else '*' for x in rtts]
            print(f"TTL={ttl:2d}  {ip:15s}  {'  '.join(disp)}  "
                  f"平均RTT={mean:.1f}ms  丢包率={loss*100:.1f}%")

            rows.append({'ttl':ttl, 'ip':ip,
                         'rtt_mean':mean,
                         'rtt_std':std,
                         'loss_rate':loss})
            if ip == self.dest_ip:
                break

        return pd.DataFrame(rows).set_index('ttl')

if __name__ == "__main__":
    tracer = ICMPTraceroute('8.8.8.8', timeout=2, max_hops=30, probes=5)
    tracer.trace()
