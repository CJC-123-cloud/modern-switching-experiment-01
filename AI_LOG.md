# AI协作记录

工具与模型：DeepSeek Harness 编程助手（DeepSeek 模型），2026-10-19。任务范围：阅读课程框架、实现 `serve_circuit`／`serve_packet`／`summarize` 三个TODO、设计自拟反例、核对结果；所有采纳的判断都以手算和公开测试为依据。

## 一项真实协作过程

**需求与输入。** 我的提示词是："先读 README.md、docs/model_contract.md、src/models.py 和三个TODO的docstring；说明输入输出、`tick % users` 的时隙规则、跨tick续传规则，然后一次只补全一个函数；`remaining_wire_bits` 已经含一次包头，不要重复加；不要改教师测试和接口；最后解释AC04的预期怎么验证。"同时贴了第5节的指标定义和第6.1节的两用户基准。

**AI建议。** AI 先归纳了模型约束：电路的时隙由 `tick % users` 唯一确定、空闲时隙不能转借；分组的 `remaining_wire_bits` 在准入时已等于 `payload_bits + header_bits`，发送时只能扣减不能重算；两种模型都只处理"队首"，预算耗尽必须保留剩余量跨tick。随后给出实现骨架：`while budget > 0 and queue:` 循环里取 `send = min(budget, record.remaining_wire_bits)`、扣预算与剩余量、`remaining_wire_bits == 0` 才 `popleft()` 并记入完成列表，否则 `break`。`summarize` 则按 PRD 公式逐项计算，先做 `generated = delivered + dropped + backlog` 检查再算时延，无完成样本返回 `None`。

**我的手算与测试。** 采纳前我先手算了两组，再跑测试：

1. **AC04（共享FIFO不交错）**：A的wire是232、B的wire是64，容量128。tick 0：先发A 128，A余104≥0，B不动，返回128；tick 1：A余104先发完，预算剩24，再发B 24，B余40，返回128。预期 `(128, [A])` 后 B 的 `remaining_wire_bits == 40`。代码运行结果与手算一致（`grading/test_packet.py::test_fifo_no_interleave`）。
2. **AC02（电路部分发送）**：1用户、200 bit记录，tick 0发128余72，tick 1发72完成。与手算一致（`grading/test_circuit.py::test_partial`）。
3. **6.1两用户基准**：手算电路2 ms/37.5%/37.5%，分组1 ms/37.5%/50%，实测完全一致（`student_tests/test_my_case.py::test_two_user_hand_calc`）。

实际运行记录：核心测试15 passed、集成测试3 passed、自拟用例5 passed、`calculate_grade.py` 自动分70.0/70（environment 5/5、circuit 20/20、packet 20/20、metrics 15/15、artifacts 10/10）。另外把 `results/comparison.csv` 与 `examples/teacher_results/comparison.csv` 逐行核对，8行指标完全一致。

**修正或采纳理由。** 首次生成即通过公开测试，所以没有编造"改错"过程；但采纳时做了三项边界验证，其中一项导致了真实的修正：

- 反例验证：补写 `test_packet_header_counted_once`，用200 bit记录断言两tick总发送量为232（200+32）。若实现每tick重加包头会得到264，断言立即失败——这证明"包头只计一次"确实靠代码保证，而不是靠测试恰好没覆盖。
- 反例验证：`test_circuit_never_lends_idle_slot` 断言tick 0用户0空队列时返回 `(0, [])`，防止把空闲时隙偷偷让给其他用户（那会把电路模型改成统计复用）。
- **真实修正**：初稿报告在解释 synchronized_burst 时写"分组需要38.4个时隙"，我按 `comparison.json` 的原始轨迹复算后发现有误——一批突发32条×128 bit = 4096 bit，恰好32个时隙，电路则是3072/128 = 24个时隙；窗口末尾只剩16个时隙，所以分组只送出16条、积压1536 bit，电路交付20条完整记录加4条部分记录、积压1152 bit。报告已按复算结果改写，没有保留错误说法。

**我能解释的核心逻辑。** `serve_packet` 的循环之所以能同时满足四条规则，是因为它只认"队首"：`min(budget, remaining_wire_bits)` 保证一个tick不超过128 bit；扣减后若剩余量非零就 `break`，于是大分组跨tick续传且不交错；`remaining_wire_bits == 0` 时先 `popleft()` 再记完成，保证部分发送不会被误报为交付；循环回到开头时预算还有剩余，自然继续下一条（AC05两条48 bit共96 bit一次发完）。包头在准入时已经写进 `remaining_wire_bits`，发送函数里没有任何 `+ cfg.header_bits`，所以不会重复加头。电路函数结构相同，只是把"队列"换成 `queues[tick % cfg.users]`，从而既不借用别的用户的时隙，也不让空闲时隙自动流转。
