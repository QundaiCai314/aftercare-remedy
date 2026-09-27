# aftercare-remedy

面向单件商品的一笔售后，依据已确认诉求、目标商品和当前平台证据，解释处理方案、核对要求并记录用户选择。

这是可加载的 Codex Skill 和离线测试工程，不是完整售后 Agent。不会登录、浏览购物网站、上传凭证或提交售后申请。

## 使用

将 `aftercare-remedy/` 目录放入宿主的 Skills 目录。入口为 [SKILL.md](aftercare-remedy/SKILL.md)。主 Agent 必须提供契约请求及已解析的可信上下文。

**推荐不是选择，选择不是提交授权。** 当前中央 v1 与上游本地 v2 尚未正式接通；本包保留申请准备阻断。安装 Skill 不会自动实现运行时授权或平台适配。

## 文件

- [接入说明](接入说明.md)
- [测试报告](测试报告.md)：原始本地交付测试及局限
- [契约修订提案](契约修订提案.md)：未部署的新结构
- `examples/`：合成请求、结果和下游接口样例
- `tests/`：26组场景、63项离线检查和测试记录
- `candidate/`：独立评审附件及正反例，不是正式接口

## 离线验证

```sh
python -m pip install -r tests/requirements.txt
python -B tests/run_checks.py
python -B tests/check_candidate.py
```

默认测试不要求原作者电脑上的文件。`tests/results.json` 是公开版离线复跑结果；`tests/original-local-results.json` 保留原始本地部分衔接记录。它们不能视为独立模型评测或完整端到端通过。

如有完整上游工程，可在不提交的 `tests/source-paths.local.json` 配置 `central`、`order`、`intake` 三个目录，再运行 `python -B tests/run_checks.py --integration`。central 应包含中央 contracts.schema.json，order 应含 tests/selection_checks.py，intake 应为 release-1.2.0 根目录。

## 发布说明

公开版移除了本机绝对路径和安装记录，调整了测试入口，使没有上游工程的环境也可执行离线测试。Skill 行为指令未改变。所有业务样例均为合成数据。没有独立模型前向评测、生产授权服务或真实平台执行能力的完成声明。
