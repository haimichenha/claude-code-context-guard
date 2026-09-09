# 可复现的合成任务

将本目录复制到一个新的隔离工作目录。`orders.csv`与`acceptance_test.py`是宿主准备的固定输入，不允许模型修改。不要在个人项目目录执行这个测试。

让当前配置的Grok在真实Claude用户设置与hook下完成：

1. 读取orders.csv，生成标准库summarize.py，提供summarize(path)。
2. 数量必须为有限、非负整数，单价必须有限且非负；金额最终保留两位小数，不能把Decimal有效位精度设成2来模拟小数位。
3. 返回row_count、total_qty、total_amount，提供CLI：`python summarize.py orders.csv report.json`。
4. 实际运行CLI和`python -m unittest -v acceptance_test`；通过后立即结束，不重复写文件。失败时只在有新诊断/相关修改后重试。

宿主独立验收原始三行：行数3、总数量6、金额43.95；并确认固定输入SHA256未变。Grok可自行编写额外测试，但不能拿自己的测试通过替代固定验收。

参考本次边界：首轮最多14工具轮次、1美元CLI上限、360秒；之后最多两次有具体新失败证据的纠正。额度只是CLI限制而非上游实际账单保证。不要把无效结果无限重放。

真实模拟结果见仓库 `observations/grok-effective-simulation-20260909.json`：完整验收未通过。Claude退出码0或result.success不代表目标完成，须检查宿主验收及是否被hook停止。
