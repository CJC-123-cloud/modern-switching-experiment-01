# 附加参数实验（选做）

本目录是**改变参数后的附加结果**，参数与基线不同，不能与 `results/comparison.*` 的8组基线混用。

- 生成脚本：`src/extra_parameter_scan.py`（`python src/extra_parameter_scan.py`）
- 随机种子：`seed=2026`，与基线一致
- 固定不变：`users=4`、`ticks=256`、`slot_bits=128`、`tick_ms=1.0`、四类业务生成规则
- 本目录文件：
  - `header_scan.csv`：`header_bits ∈ {0, 16, 32, 64, 96}`，4业务 × 2模型，共40行
  - `buffer_scan.csv`：`buffer_payload_bits ∈ {512, 1024, 2048, 4096, 8192}`，4业务 × 2模型，共40行
  - `parameter_scan.json`：两次扫描的全部行 + 基线config + 变化量，便于复核
  - `parameter_scan.png`：包头对有效利用率、缓存对丢失率的影响

结论摘要见 `REPORT.md` 的"参数敏感性"一节：包头0时continuous的分组利用率回到1.0000（与电路相同），说明该场景差距全部来自包头；缓存从512 bit增到8192 bit时staggered_burst电路的丢失率从60.16%降到0，但积压升到6240 bit——缓存只是把丢弃换成了排队，并不增加窗口内的交付。

注意：`.gitignore` 默认忽略 `results/*`，提交这些附加结果需执行
`git add -f results/extra/*.csv results/extra/*.json results/extra/*.png`。
