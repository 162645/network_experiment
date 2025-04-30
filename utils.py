'''
这个文件用处不大
'''

import subprocess
import re
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

def run_and_save(cmd: list, out_txt: Path):
    """运行外部命令，将 stdout 实时写入 out_txt。"""
    with out_txt.open('w', encoding='utf-8') as f:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in proc.stdout:
            f.write(line)
        proc.wait()

def parse_ping(txt_path: Path) -> pd.DataFrame:
    """解析 ping 输出，抽取每个请求的 RTT（ms）或丢包（NaN）。"""
    rtts = []
    pat = re.compile(r'time[=<]\s*(\d+\.?\d*)\s*ms', re.IGNORECASE)
    for line in txt_path.read_text(errors='ignore').splitlines():
        m = pat.search(line)
        rtts.append(float(m.group(1)) if m else float('nan'))
    return pd.DataFrame({'rtt': rtts})

# def window_stats(df: pd.DataFrame, window_s: int) -> pd.DataFrame:
#     """按固定秒窗口重采样，计算 rtt_mean、rtt_std、loss_rate。"""
#     df = df.copy()
#     # 构造时间索引，频率 1s
#     df.index = pd.timedelta_range(start='0s', periods=len(df), freq='1s')
#     res = df['rtt'].resample(f'{window_s}s').agg(['mean','std', lambda x: x.isna().mean()])
#     res.columns = ['rtt_mean','rtt_std','loss_rate']
#     return res

# utils.py
import pandas as pd
def window_stats(df: pd.DataFrame, window_s: int) -> pd.DataFrame:
    """
    对时间序列 df（索引为时间戳，列含 'rtt'）按 window_s 重采样，
    返回 DataFrame ['rtt_mean','rtt_std','loss_rate']。
    """
    df2 = df.copy()
    df2.index = pd.to_datetime(df2.index, unit='s')
    grp = df2['rtt'].resample(f'{window_s}s')
    return pd.DataFrame({
        'rtt_mean': grp.mean(),
        'rtt_std':  grp.std(),
        'loss_rate':grp.apply(lambda x: x.isna().mean())
    })

def parse_traceroute(txt_path: Path) -> pd.DataFrame:
    """
    解析 tracert 或 mtr --report 输出，提取每跳的 RTT 列表与丢包率，
    返回 DataFrame(index=ttl, columns=[rtt_mean,rtt_std,loss_rate])
    """
    lines = txt_path.read_text(errors='ignore').splitlines()
    hops = {}
    # 假设每行以 TTL 开头，如 "  1    1 ms    1 ms    1 ms  192.168.0.1"
    pat = re.compile(r'^\s*(\d+)\s+((?:\d+ ms|\*\s+){3,})')
    for ln in lines:
        m = pat.match(ln)
        if m:
            ttl = int(m.group(1))
            parts = m.group(2).split()
            times = []
            loss = parts.count('*')
            for p in parts:
                if p.endswith('ms'):
                    try:
                        times.append(float(p.replace('ms','')))
                    except:
                        pass
            if times:
                hops[ttl] = {
                    'rtt_mean': sum(times)/len(times),
                    'rtt_std': pd.Series(times).std(),
                    'loss_rate': loss/len(parts)
                }
    return pd.DataFrame.from_dict(hops, orient='index').sort_index()

def plot_time_curves(results: dict, out_png: Path, title: str):
    """
    对比多条时间序列曲线（RTT 均值）。
    参数：
      results: dict[name → DataFrame]，DataFrame 需包含 'rtt_mean' 列。
      out_png: 输出图片路径。
      title: 图表标题。
    """
    plt.figure(figsize=(10, 6))
    has_curve = False

    for name, df in results.items():
        # 跳过空表或无效列
        if df.empty or 'rtt_mean' not in df:
            continue
        # 将 TimedeltaIndex 转为秒数，否则用原始索引
        if isinstance(df.index, pd.TimedeltaIndex):
            x = df.index.total_seconds()
        else:
            x = df.index.values
        y = df['rtt_mean'].fillna(0).values
        plt.plot(x, y, marker='o', label=f'{name} RTT 均值')
        has_curve = True

    if not has_curve:
        raise ValueError("没有有效数据可绘制，请检查 DataFrame 是否非空且包含 rtt_mean 列")  # 提前失败
    plt.title(title)
    plt.xlabel('时间 (s)')
    plt.ylabel('RTT 均值 (ms)')
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(out_png)
    plt.close()

def plot_hop_curves(hops_dfs: dict, out_png: Path, metric='rtt_mean'):
    """
    对比多条跳数序列曲线（每跳 RTT 或丢包率）。
    参数：
      hops_dfs: dict[name → DataFrame]，索引为跳数，包含 metric 列。
      metric: 要绘制的列名（'rtt_mean' 或 'loss_rate'）。
    """
    plt.figure(figsize=(10, 6))
    has_curve = False

    for name, df in hops_dfs.items():
        if df.empty or metric not in df:
            continue
        x = df.index.values
        y = df[metric].fillna(0).values
        plt.plot(x, y, marker='o', label=name)
        has_curve = True

    if not has_curve:
        raise ValueError("没有有效跳数数据可绘制，请检查解析结果")  # 提前失败
    plt.title(f'{metric.replace("_"," ").title()} vs 跳数')
    plt.xlabel('跳数 (TTL)')
    plt.ylabel(metric.replace('_',' ').title())
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(out_png)
    plt.close()
