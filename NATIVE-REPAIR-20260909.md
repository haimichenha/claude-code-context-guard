# Native Claude 与 Grok：实测状态（2026-09-09）

## 已验证：客户端使用 100 万窗口

本机 Claude Code 2.1.263、用户配置的 `grok-4.6`：

- 原配置的 `/autocompact` 实际显示 `capped to 200k by model`。此前只读 settings 得到的120万不是有效窗口证明。
- 依用户最新选择，使用 **100万窗口、80%自动压缩**：
  - `autoCompactWindow: 1000000`
  - `CLAUDE_CODE_AUTO_COMPACT_WINDOW=1000000`
  - `CLAUDE_CODE_MAX_CONTEXT_TOKENS=1000000`
  - `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=80`
- native版本针对自定义模型的容量解析接受上述声明，无需修改 `claude.exe`，也没有设置 `DISABLE_COMPACT` 或 `DISABLE_AUTO_COMPACT`。
- 实际 `/autocompact` 不再出现200k限制；`/context` 显示模型grok-4.6、分母1m；真实模型任务的 `modelUsage.contextWindow` 也为1000000。
- 窗口查询API轮次、输入输出token、费用均为0。此结果证明**客户端采用的窗口**，不证明网关实际上能接收百万token，也没有进行长会话压缩触发压力测试。
- 80%作用于扣除摘要预留后的有效窗口，不应简单承诺恰好800000时触发；本机代码保留最多20000摘要空间时，对应约784000。

证据：`observations/native-runtime-1m-20260909.json`。

## 使用与验证

已安装旧guard及AE-tool两个Grok技能的机器：

```powershell
python ./scripts/install-runtime-guards.py --grok-skills-root '<AE-tool>/grok-skills'
python ./scripts/install-runtime-guards.py --grok-skills-root '<AE-tool>/grok-skills' --apply
python "$env:USERPROFILE/.claude/scripts/ensure-claude-context-policy.py" --window 1000000 --pct 80
python ./scripts/verify-native-runtime.py --output '<新的本地报告路径>.json'
```

新会话前重启Claude；已有进程可能仍持有旧环境。守护器会保留选择，不在下一次启动擅自回到120万。这里不改模型名、权限或提供商数据库。旧JS实验分支保留用于历史版本，不能套用到native证明能力。

`validate-claude-context-policy.py` 是静态检查，native仍报告PARTIAL；`verify-native-runtime.py` 才会真正启动只读本地命令验证窗口。它不会用模型自然语言自述作为证据。

## Grok真实执行：发现的问题没有隐藏

真实Claude用户配置与hook下，合成任务要求读取CSV、编程、运行、测试并完成验收；没有使用 `--bare`，没有传私人项目文件。

1. 首轮产生程序但金额计算错误，随后无效重写，被拦截并达到轮次上限。
2. 定向反馈后Grok修正精度，输出正确总额43.95，并完成3项自写测试；但宿主独立检查发现整数数量和有限值要求未满足。
3. 冻结宿主验收测试后再次纠正，仍未修好3个边界案例，并再次空转，被hook终止。本轮停止继续追加同类模型调用。

**因此不能宣称“Grok能够稳定无人监督完成所有任务”。** 当前已验证的是窗口配置、实际工具调用、失败止损和独立验收路径。详细阶段数据见 `observations/grok-effective-simulation-20260909.json`。

修复的控制层缺口：
- 防空转计数覆盖不同文件交替无效Write。成功Write或新用户指令重置，避免把合理下一步误判为空转。
- Claude被hook停止时仍可能返回 `subtype=success`、`is_error=false`，而final为空。AE-tool通用技能新增分类器拒绝这种假完成，也拒绝“模型自测通过、宿主验收失败”。
- 持续执行意味着每步有目标相关的新证据、产物或验证，不是命令字符串不断变化。相同命令在代码或条件变化后可以合理重试。

## 署名与回退

今后的自动署名显式配置 `attribution: {"commit":"","pr":""}`，不改Git真实作者，不重写旧提交历史。旧 `includeCoAuthoredBy=false` 在本机native仍可识别，不能简单断言它完全失效。

安装器在 `~/.claude/backups/runtime-guard-*` 保存逐文件manifest，窗口守护器使用 `native-context-*` 备份。备份可能含凭据，禁止上传。只对照manifest恢复对应文件，勿覆盖之后新增设置。

## 验证范围

- context-guard：22项本地单元测试通过。
- AE-tool通用技能：26项测试通过。
- 真实Grok完整任务：**未通过全部验收**；错误结果及停机情况均保留，不修饰成成功。
- 仓库不包含原始会话、令牌、私有简历、数据库、厂商exe或失败生成的程序。

参考：[Claude hooks](https://code.claude.com/docs/en/hooks)、[设置与署名](https://code.claude.com/docs/en/configuration#attribution-settings)。本机版本的自定义模型容量行为以实际CLI查询为证，其他版本须重测。

## 2026-09-10 后续修复

后来发现独立的旧 stability 启动脚本仍会在 updater 之后覆盖窗口与环境文件；已定位并修复，不把9月9日仅验证 updater 的结果扩大为整个启动链可靠。见 [产物与启动链修复](GROK-ARTIFACT-REPAIR-20260910.md)。
