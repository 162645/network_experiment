# measures.py

import argparse, time, subprocess
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from tqdm import tqdm
from icmp_ping import ICMPPing
from icmp_traceroute import ICMPTraceroute
import re

# 全局中文字体 & 负号正常显示
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

def save_ping(target, mode, duration, outdir):
    """
    发送 Ping 并保存结果到 TXT：
    - ping1: 1 pps，持续 duration 秒
    - ping100: 100 pps，持续 duration 秒
    保存格式：seq, 时间戳, RTT(ms)
    """
    pinger = ICMPPing(target, timeout=1)
    rate = 1 if mode=='ping1' else 100
    total = duration * rate
    txt = outdir / f"{mode}.txt"
    with txt.open('w') as f:
        for i in tqdm(range(total), desc=f"{mode} 进度"):
            rtt = pinger.ping_once()
            f.write(f"{i+1},{time.time()},{rtt}\n")
            time.sleep(1/rate)
    return txt

def plot_ping_10s(txt1, txt100, duration, outdir):
    """
    每10秒一个窗口，共 duration/10 个点。
    绘制：RTT 均值 / 标准差 / 丢包率（三张图）。
    横轴：1…duration/10
    """
    N = duration // 10

    # 读取 RTT 列表并拆分成 N 段
    df1   = pd.read_csv(txt1,   names=['seq','ts','rtt'])
    df100 = pd.read_csv(txt100, names=['seq','ts','rtt'])
    arr1   = df1['rtt'].values.reshape(N, -1)
    arr100 = df100['rtt'].values.reshape(N, -1)

    # 忽略 NaN 计算指标
    mean1   = np.nanmean(arr1,   axis=1)
    std1    = np.nanstd(arr1,    axis=1)
    loss1   = np.isnan(arr1).sum(axis=1) / arr1.shape[1]

    mean100 = np.nanmean(arr100, axis=1)
    std100  = np.nanstd(arr100,  axis=1)
    loss100 = np.isnan(arr100).sum(axis=1) / arr100.shape[1]

    x = list(range(1, N+1))

    # 1）RTT 均值对比
    plt.figure(figsize=(8,5))
    plt.plot(x, mean1,   marker='o', label='1pps')
    plt.plot(x, mean100, marker='s', label='100pps')
    plt.xticks(x); plt.xlabel("10秒窗口"); plt.ylabel("RTT 均值 (ms)")
    plt.title("Ping 每10s RTT 均值对比")
    plt.legend(); plt.grid(True); plt.tight_layout()
    plt.savefig(outdir/"ping_10s_mean.png"); plt.close()

    # 2）RTT 标准差对比
    plt.figure(figsize=(8,5))
    plt.plot(x, std1,   marker='o', label='1pps')
    plt.plot(x, std100, marker='s', label='100pps')
    plt.xticks(x); plt.xlabel("10秒窗口"); plt.ylabel("RTT 标准差 (ms)")
    plt.title("Ping 每10s RTT 标准差对比")
    plt.legend(); plt.grid(True); plt.tight_layout()
    plt.savefig(outdir/"ping_10s_std.png"); plt.close()

    # 3）丢包率对比
    plt.figure(figsize=(8,5))
    plt.plot(x, loss1,   marker='o', label='1pps')
    plt.plot(x, loss100, marker='s', label='100pps')
    plt.xticks(x); plt.xlabel("10秒窗口"); plt.ylabel("丢包率")
    plt.title("Ping 每10s 丢包率对比")
    plt.legend(); plt.grid(True); plt.tight_layout()
    plt.savefig(outdir/"ping_10s_loss.png"); plt.close()

def plot_ping_100pps_1s(txt100, duration, outdir):
    """
    ping100 每 1 秒 一个窗口，共 duration 点。
    绘制：RTT 均值 / 标准差 / 丢包率（三张图）。
    横轴：1…duration
    """
    df = pd.read_csv(txt100, names=['seq','ts','rtt'])
    arr = df['rtt'].values.reshape(duration, -1)

    mean = np.nanmean(arr, axis=1)
    std  = np.nanstd(arr,  axis=1)
    loss = np.isnan(arr).sum(axis=1) / arr.shape[1]

    x = list(range(1, duration+1))

    # RTT 均值
    plt.figure(figsize=(8,5))
    plt.plot(x, mean, marker='o')
    plt.xticks(x[::5]); plt.xlabel("时间 (s)"); plt.ylabel("RTT 均值 (ms)")
    plt.title("Ping100 每秒 RTT 均值"); plt.grid(True); plt.tight_layout()
    plt.savefig(outdir/"ping100_1s_mean.png"); plt.close()

    # RTT 标准差
    plt.figure(figsize=(8,5))
    plt.plot(x, std, marker='o')
    plt.xticks(x[::5]); plt.xlabel("时间 (s)"); plt.ylabel("RTT 标准差 (ms)")
    plt.title("Ping100 每秒 RTT 标准差"); plt.grid(True); plt.tight_layout()
    plt.savefig(outdir/"ping100_1s_std.png"); plt.close()

    # 丢包率
    plt.figure(figsize=(8,5))
    plt.plot(x, loss, marker='o')
    plt.xticks(x[::5]); plt.xlabel("时间 (s)"); plt.ylabel("丢包率")
    plt.title("Ping100 每秒 丢包率"); plt.grid(True); plt.tight_layout()
    plt.savefig(outdir/"ping100_1s_loss.png"); plt.close()

# def run_mtr(target, cycles):
#     """
#     指定 C:\Windows\System32\mtr.exe（CLI版）并调用。
#     避免弹 GUI。若非 0 退出码则捕获并返回空 DataFrame。
#     """
#     mtr_exe = r"C:\Windows\System32\mtr.exe"
#     if not Path(mtr_exe).exists():
#         raise FileNotFoundError(f"mtr.exe 未找到：{mtr_exe}")
#     cmd = [mtr_exe, "-n", "-r", "-c", str(cycles), target]
#     try:
#         out = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL)
#     except subprocess.CalledProcessError:
#         # 若执行失败，返回空 DataFrame 保证后续绘图不中断
#         return pd.DataFrame(columns=['ttl', 'ip', 'rtt_mean', 'loss_rate']).set_index('ttl')
#     rows = []
#     for line in out.splitlines():
#         parts = line.split()
#         try:
#             if len(parts) >= 8 and parts[0].isdigit():
#                 ttl = int(parts[0])
#                 ip = parts[1]
#                 loss = float(parts[2].strip("%")) / 100
#                 avg = float(parts[6])
#                 rows.append({'ttl': ttl, 'ip': ip, 'rtt_mean': avg, 'loss_rate': loss})
#         except Exception as e:
#             print(f"跳过异常行: {line}, 错误: {e}")
#     # ✅ 如果没有成功解析的数据，返回一个空 DataFrame（避免报错）
#     if not rows:
#         print("警告：mtr 输出为空或解析失败，返回空表。")
#         return pd.DataFrame(columns=['ttl', 'ip', 'rtt_mean', 'loss_rate']).set_index('ttl')
#     # ✅ 有数据则正常返回
#     return pd.DataFrame(rows).set_index('ttl')


def run_mtr(
    target: str,
    cycles: int,
    max_hops: int = 30,
    mtr_exe_path: str = r"C:\Tools\WinMTRCmd.exe"   # <- 改成你的实际路径
) -> pd.DataFrame:
    """
    调用纯 CLI 版 WinMTRCmd.exe，返回 1…max_hops 的 DataFrame：
      ttl（跳数）、ip、rtt_mean（平均 RTT）、loss_rate（丢包率）
    如果某跳未响应，则 ip='*', rtt_mean=NaN, loss_rate=1.0
    """
    exe = Path(mtr_exe_path)
    if not exe.exists():
        raise FileNotFoundError(f"WinMTRCmd 未找到：{exe}")

    # 构造命令：numeric (只输出 IP)、report 一次后退出、cycles
    cmd = [
        str(exe),
        "-n",
        "-r",
        "-c", str(cycles),  # ← 用空格分隔
        target
    ]

    try:
        # 取消 stderr 重定向，方便调试
        out = subprocess.check_output(cmd, text=True)
    except subprocess.CalledProcessError as e:
        print(f"[WinMTRCmd] 非零退出码 {e.returncode}，返回全丢包占位 …")
        # 返回一个全丢包占位表，避免后续绘图出错
        data = [
            {'ttl': i, 'ip': '*', 'rtt_mean': float('nan'), 'loss_rate': 1.0}
            for i in range(1, max_hops + 1)
        ]
        return pd.DataFrame(data).set_index('ttl')

    # 解析输出（示例行格式）：
    #   3  10.0.0.1    0.0%    5    1.2    1.0    0.9    1.4    0.1
    rows = {}
    for line in out.splitlines():
        # 跳过表头和空行
        if not line.strip() or line.lstrip().startswith("HOST:"):
            continue

        # 匹配 “ TTL .|-- host Loss%  Snt  Last  Avg … ” 格式
        m = re.match(
            r"^\s*(\d+)\.\|\-\-\s+(\S+)\s+([\d\.]+)%\s+\d+\s+[\d\.]+\s+([\d\.]+)",
            line
        )
        if m:
            ttl = int(m.group(1))
            ip = m.group(2)  # 若无响应则为 '???'
            loss_rate = float(m.group(3)) / 100.0  # Loss%
            rtt_mean = float(m.group(4))  # Avg 列
            rows[ttl] = {'ip': ip, 'rtt_mean': rtt_mean, 'loss_rate': loss_rate}
        else:
            print(f"[run_mtr] 未匹配行：{line!r}")

    # 把 1…max_hops 都填上，缺失用占位
    data = []
    for i in range(1, max_hops + 1):
        if i in rows:
            data.append({'ttl': i, **rows[i]})
        else:
            data.append({'ttl': i, 'ip': '*', 'rtt_mean': float('nan'), 'loss_rate': 1.0})

    return pd.DataFrame(data).set_index('ttl')

def plot_tr_vs_mtr(dfs_tr, dfs_mtr, outdir):
    """
    Traceroute vs mtr RTT 和丢包率对比（6 条曲线）
    """
    # RTT 对比
    plt.figure(figsize=(8,5))
    for k,df in dfs_tr.items():
        plt.plot(df.index, df['rtt_mean'], marker='o', label=f"TR{k}")
    for k,df in dfs_mtr.items():
        plt.plot(df.index, df['rtt_mean'], marker='x', label=f"MTR{k}")
    plt.title("RTT 均值对比")
    plt.xlabel("TTL"); plt.ylabel("RTT (ms)")
    plt.legend(); plt.grid(True); plt.tight_layout()
    plt.savefig(outdir/"tr_mtr_rtt.png"); plt.close()

    # 丢包率对比
    plt.figure(figsize=(8,5))
    for k,df in dfs_tr.items():
        plt.plot(df.index, df['loss_rate'], marker='o', label=f"TR{k}")
    for k,df in dfs_mtr.items():
        plt.plot(df.index, df['loss_rate'], marker='x', label=f"MTR{k}")
    plt.title("丢包率对比")
    plt.xlabel("TTL"); plt.ylabel("丢包率")
    plt.legend(); plt.grid(True); plt.tight_layout()
    plt.savefig(outdir/"tr_mtr_loss.png"); plt.close()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--target',   required=True)
    parser.add_argument('--duration', type=int, default=60)
    args = parser.parse_args()

    od = Path("results")/f"{args.target}_{time.strftime('%Y%m%d_%H%M%S')}"
    od.mkdir(parents=True, exist_ok=True)

    #1. Ping 实验
    txt1   = save_ping(args.target, 'ping1',   args.duration, od)
    txt100 = save_ping(args.target, 'ping100', args.duration, od)
    plot_ping_10s(txt1, txt100, args.duration, od)
    plot_ping_100pps_1s(txt100, args.duration, od)

    # 2. Traceroute & mtr 实验
    modes = {'1':1, '5':5, '20':20}
    dfs_tr, dfs_mtr = {}, {}
    for k, v in modes.items():
        # 自研 traceroute
        tr = ICMPTraceroute(args.target, timeout=2, max_hops=30, probes=v)
        dfs_tr[k] = tr.trace()
        dfs_tr[k].to_csv(od / f"tr{k}.csv", na_rep='*')

        # WinMTRCmd 调用
        dfs_mtr[k] = run_mtr(
            target=args.target,
            cycles=v,
            max_hops=30,
            mtr_exe_path=r"C:\Windows\System32\WinMTRCmd.exe"  # 请改为您的实际路径
        )
        dfs_mtr[k].to_csv(od / f"mtr{k}.csv", na_rep='*')

    plot_tr_vs_mtr(dfs_tr, dfs_mtr, od)
    print("全部完成，结果保存在：", od)

if __name__=='__main__':
    main()

# # measures.py
#
# import argparse, time, subprocess
# import pandas as pd
# import matplotlib.pyplot as plt
# from pathlib import Path
# from tqdm import tqdm
# from icmp_ping import ICMPPing
# from icmp_traceroute import ICMPTraceroute
# from utils import window_stats
#
# # 全局中文字体 & 负号正常显示
# plt.rcParams['font.sans-serif'] = ['SimHei']
# plt.rcParams['axes.unicode_minus'] = False
#
# def save_ping(target, mode, duration, outdir):
#     """
#     发送 Ping 并保存结果到 TXT：
#     - ping1: 1 pps，持续 duration 秒
#     - ping100: 100 pps，持续 duration 秒
#     """
#     pinger = ICMPPing(target, timeout=1)
#     rate = 1 if mode=='ping1' else 100
#     total = duration * rate
#     txt = outdir / f"{mode}.txt"
#     with txt.open('w') as f:
#         for i in tqdm(range(total), desc=f"{mode} 进度"):
#             rtt = pinger.ping_once()
#             f.write(f"{i+1},{time.time()},{rtt}\n")
#             time.sleep(1/rate)
#     return txt
#
# def plot_ping_10s(txt1, txt100, duration, outdir):
#     """
#     每10秒一个窗口，共 duration/10 个点。
#     分别绘制 RTT 均值、标准差、丢包率（3 图）。
#     横轴：1…duration/10
#     """
#     # 窗口数
#     N = duration // 10
#     # 读取 RTT 列表
#     df1   = pd.read_csv(txt1,   names=['seq','ts','rtt'])
#     df100 = pd.read_csv(txt100, names=['seq','ts','rtt'])
#     # 切分为 N 段
#     arr1   = df1['rtt'].values.reshape(N, -1)
#     arr100 = df100['rtt'].values.reshape(N, -1)
#
#     # 计算各窗口指标
#     mean1   = arr1.mean(axis=1)
#     std1    = pd.DataFrame(arr1).std(axis=1).values
#     loss1   = (pd.DataFrame(arr1).isna().sum(axis=1) / arr1.shape[1]).values
#
#     mean100 = arr100.mean(axis=1)
#     std100  = pd.DataFrame(arr100).std(axis=1).values
#     loss100 = (pd.DataFrame(arr100).isna().sum(axis=1) / arr100.shape[1]).values
#
#     x = list(range(1, N+1))
#
#     # RTT 均值
#     plt.figure(figsize=(8,5))
#     plt.plot(x, mean1,   marker='o', label='1pps')
#     plt.plot(x, mean100, marker='s', label='100pps')
#     plt.xticks(x); plt.xlabel("10s 窗口"); plt.ylabel("RTT 均值 (ms)")
#     plt.title("Ping 每10s RTT 均值对比")
#     plt.legend(); plt.grid(True); plt.tight_layout()
#     plt.savefig(outdir/"ping_10s_mean.png"); plt.close()
#
#     # RTT 标准差
#     plt.figure(figsize=(8,5))
#     plt.plot(x, std1,   marker='o', label='1pps')
#     plt.plot(x, std100, marker='s', label='100pps')
#     plt.xticks(x); plt.xlabel("10s 窗口"); plt.ylabel("RTT 标准差 (ms)")
#     plt.title("Ping 每10s RTT 标准差对比")
#     plt.legend(); plt.grid(True); plt.tight_layout()
#     plt.savefig(outdir/"ping_10s_std.png"); plt.close()
#
#     # 丢包率
#     plt.figure(figsize=(8,5))
#     plt.plot(x, loss1,   marker='o', label='1pps')
#     plt.plot(x, loss100, marker='s', label='100pps')
#     plt.xticks(x); plt.xlabel("10s 窗口"); plt.ylabel("丢包率")
#     plt.title("Ping 每10s 丢包率对比")
#     plt.legend(); plt.grid(True); plt.tight_layout()
#     plt.savefig(outdir/"ping_10s_loss.png"); plt.close()
#
# def plot_ping_100pps_1s(txt100, duration, outdir):
#     """
#     ping100 每 1s 窗口统计并绘图（duration 秒，横轴 1…duration）
#     """
#     df = pd.read_csv(txt100, names=['seq','ts','rtt'])
#     arr = df['rtt'].values.reshape(duration, -1)
#
#     mean   = arr.mean(axis=1)
#     std    = pd.DataFrame(arr).std(axis=1).values
#     loss   = (pd.DataFrame(arr).isna().sum(axis=1) / arr.shape[1]).values
#     x = list(range(1, duration+1))
#
#     # 绘 3 张图
#     plt.figure(figsize=(8,5))
#     plt.plot(x, mean, marker='o')
#     plt.xticks(x[::5]); plt.xlabel("时间 (s)"); plt.ylabel("RTT 均值 (ms)")
#     plt.title("Ping100 每秒 RTT 均值"); plt.grid(True); plt.tight_layout()
#     plt.savefig(outdir/"ping100_1s_mean.png"); plt.close()
#
#     plt.figure(figsize=(8,5))
#     plt.plot(x, std, marker='o')
#     plt.xticks(x[::5]); plt.xlabel("时间 (s)"); plt.ylabel("RTT 标准差 (ms)")
#     plt.title("Ping100 每秒 RTT 标准差"); plt.grid(True); plt.tight_layout()
#     plt.savefig(outdir/"ping100_1s_std.png"); plt.close()
#
#     plt.figure(figsize=(8,5))
#     plt.plot(x, loss, marker='o')
#     plt.xticks(x[::5]); plt.xlabel("时间 (s)"); plt.ylabel("丢包率")
#     plt.title("Ping100 每秒 丢包率"); plt.grid(True); plt.tight_layout()
#     plt.savefig(outdir/"ping100_1s_loss.png"); plt.close()
#
# def run_mtr(target, cycles):
#     """
#     调用 WinMTR.exe（指定路径），返回 DataFrame
#     """
#     mtr_exe = r"C:\Windows\System32\WinMTR.exe"
#     if not Path(mtr_exe).exists():
#         raise FileNotFoundError(f"WinMTR 未找到：{mtr_exe}")
#     cmd = [mtr_exe, "-n", "-r", "-c", str(cycles), target]
#     out = subprocess.check_output(cmd, text=True)
#     rows = []
#     for line in out.splitlines():
#         parts = line.split()
#         if len(parts)>=8 and parts[0].isdigit():
#             ttl = int(parts[0]); ip=parts[1]
#             loss = float(parts[2].strip("%"))/100
#             avg  = float(parts[6])
#             rows.append({'ttl':ttl,'ip':ip,'rtt_mean':avg,'loss_rate':loss})
#     return pd.DataFrame(rows).set_index('ttl')
#
# def plot_tr_vs_mtr(dfs_tr, dfs_mtr, outdir):
#     """Traceroute vs WinMTR RTT 和丢包率对比（6 条曲线）"""
#     # RTT
#     plt.figure(figsize=(8,5))
#     for k,df in dfs_tr.items():
#         plt.plot(df.index, df['rtt_mean'], marker='o', label=f"TR{ k }")
#     for k,df in dfs_mtr.items():
#         plt.plot(df.index, df['rtt_mean'], marker='x', label=f"MTR{ k }")
#     plt.title("RTT 均值对比"); plt.xlabel("TTL"); plt.ylabel("ms")
#     plt.legend(); plt.grid(True); plt.tight_layout()
#     plt.savefig(outdir/"tr_mtr_rtt.png"); plt.close()
#
#     # 丢包率
#     plt.figure(figsize=(8,5))
#     for k,df in dfs_tr.items():
#         plt.plot(df.index, df['loss_rate'], marker='o', label=f"TR{ k }")
#     for k,df in dfs_mtr.items():
#         plt.plot(df.index, df['loss_rate'], marker='x', label=f"MTR{ k }")
#     plt.title("丢包率对比"); plt.xlabel("TTL"); plt.ylabel("丢包率")
#     plt.legend(); plt.grid(True); plt.tight_layout()
#     plt.savefig(outdir/"tr_mtr_loss.png"); plt.close()
#
# def main():
#     parser = argparse.ArgumentParser()
#     parser.add_argument('--target',   required=True)
#     parser.add_argument('--duration', type=int, default=60)
#     args = parser.parse_args()
#
#     od = Path("results")/f"{args.target}_{time.strftime('%Y%m%d_%H%M%S')}"
#     od.mkdir(parents=True, exist_ok=True)
#
#     # 1. Ping
#     txt1   = save_ping(args.target, 'ping1',   args.duration, od)
#     txt100 = save_ping(args.target, 'ping100', args.duration, od)
#     plot_ping_10s(txt1, txt100, args.duration, od)
#     plot_ping_100pps_1s(txt100, args.duration, od)
#
#     # 2. Traceroute & WinMTR
#     modes = {'1':1, '5':5, '20':20}
#     dfs_tr, dfs_mtr = {}, {}
#     for k,v in modes.items():
#         tr = ICMPTraceroute(args.target, timeout=2, max_hops=30, probes=v)
#         dfs_tr[k]  = tr.trace()
#         dfs_tr[k].to_csv(od/f"tr{k}.csv", na_rep='*')
#         dfs_mtr[k] = run_mtr(args.target, v)
#
#     plot_tr_vs_mtr(dfs_tr, dfs_mtr, od)
#     print("完成，结果在：", od)
#
# if __name__=='__main__':
#     main()
