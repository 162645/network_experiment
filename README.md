本项目为北京邮电大学李昕李教授课程《云网环境中的网络测量与数据分析技术》的第一次作业 - 小实验四，旨在通过高频 Ping 和 WinMTR 以及traceroute工具，进行网络延迟和丢包率的统计与可视化分析。

🧑‍🏫 实验目标：使用 ICMP Ping 和 Traceroute 工具对目标节点进行测量，掌握基本的网络时延统计方法，以及链路路径中各跳点的丢包情况。

📁 文件结构说明
.
├── measures.py           # 主实验逻辑（Ping测量、绘图、WinMTR路径分析）
├── icmp_ping.py          # 自定义的 ICMP Ping 模块
├── icmp_traceroute.py    # 自定义的 Traceroute 模块（如有）
├── output/               # 实验输出目录：txt数据 & 可视化图像
├── README.md             # 项目说明文档
🛠 使用方法
确保你已经安装好以下依赖：
pip install pandas numpy matplotlib tqdm
运行测量与绘图示例：
python measures.py --target 1.1.1.1 --duration 60 --outdir ./output
参数说明：
--target: 要 Ping 的目标 IP 地址
--duration: 测量时长（秒），建议为 60~120
--outdir: 输出结果保存目录

📊 实验内容与功能介绍
✅ 1. 高低速 Ping 数据采集与保存
使用 1pps 与 100pps 的速率进行 Ping 测量，保存格式为：

seq, timestamp, RTT(ms)
🟢 低速 ping（1pps）：用于观察基本网络状况
🔴 高频 ping（100pps）：用于检测瞬时抖动和丢包

📈 2. RTT 与丢包率可视化分析
提供两种分析视角：

⏱ 10秒窗口统计（均值/方差/丢包）对比图
📉 1秒粒度统计（仅限100pps数据）

生成的图像：
ping_10s_mean.png：10秒 RTT 均值对比
ping_10s_std.png：10秒 RTT 标准差对比
ping_10s_loss.png：10秒 丢包率对比
ping100_1s_*.png：1秒粒度的更精细可视化

🌍 3. 路由路径分析（WinMTR）并且和traceroute进行对比分析
调用 CLI 版的 WinMTRCmd.exe 工具，自动提取目标 IP 的路径信息：
每跳 TTL 的 IP 地址
每跳的 RTT 均值
每跳的丢包率（loss rate）
输出为结构化 DataFrame，可用于绘图与进一步分析。

⚠️ 注意事项
WinMTR CLI 工具路径需手动指定：C:\Tools\WinMTRCmd.exe
高 PPS 发送时建议关闭防火墙干扰
Python 需 3.7 以上版本，确保支持 f-string 和 type hints

欢迎 Star ⭐ 或 Fork 🔧
