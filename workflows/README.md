# 历史商品整理工作流

`legacy/` 保存历史商品整理批次（2026-10-11 首次入库、2026-10-13 分类整理与二次整理）中使用的 14 个 Python 脚本、1 个浏览器预览检查脚本和 1 个 macOS OCR 工具，供阅读和迁移旧流程时参考。目录只收源码，不包含当时的输入清单、输出报告、预览素材、执行日志或运行状态。这些日期描述历史上下文，不表示当前资料或平台状态仍然存在。

## 文件索引

| 文件 | 职责 | 缺失输入与依赖 |
| --- | --- | --- |
| `legacy/build_career_plan.py` | 根据内容盘点、视觉复核及分类映射生成职业规划资料的整理计划和统计。 | 需要历史盘点、复核与文件清单 JSON；依赖同目录的 `second_pass_reorganize.py` 常量。数据文件不随仓库提供。 |
| `legacy/build_curation_plan.py` | 根据盘点结果与人工分类覆盖表构建创新创业资料分类计划。 | 需要内容盘点、OOXML 档案及视觉判断记录；依赖 `发布记录` 下的历史输入目录。 |
| `legacy/career_content_inventory.py` | 读取职业规划演示文稿及图片，生成内容/视觉盘点数据。 | 需要原始 PPT/PPTX 与分析索引；依赖 Pillow。 |
| `legacy/check_product_preview.cjs` | 在桌面和手机视口检查本地商品图预览的图片数量、尺寸、展开交互及布局。 | 需要已启动的本地预览、其图片素材、Node.js、Playwright 浏览器；旧分享 ID 改为本地环境变量。该脚本会访问预览页面及其静态资源。 |
| `legacy/complete_quark_delivery.py` | 历史流程中创建并检查资料合集分享状态。 | 需要整理报告、云盘授权和外部 `xpan_auto.quark_adapter` 适配器；会产生云盘写入，适合只读理解，不应作为默认流程。 |
| `legacy/curate_ppt_visuals.py` | 将演示文稿渲染为图片并制作视觉审阅材料。 | 需要原始演示文稿；依赖 LibreOffice、pypdfium2 和 Pillow。 |
| `legacy/finish_second_pass.py` | 应用历史二次分类/整理计划并生成结果记录。 | 需要历史清单、整理计划和授权云盘适配器；包含云端整理操作，输入数据未公开。 |
| `legacy/inventory_quark_reorganization.py` | 从本地演示文稿及观察记录建立重组盘点数据。 | 需要历史文件清单、渲染观察记录和源 PPT/PPTX；不包含这些执行数据。 |
| `legacy/quark_ppt_transfer.py` | 历史资料包上传和断点续传实现。 | 需要明确授权的本地源目录、上传清单、私有凭据及外部 `xpan_auto.quark_adapter`。会向云盘写数据，默认禁止运行。 |
| `legacy/reorganize_quark_ppt.py` | 历史云盘文件夹盘点、校验与分类整理实现。 | 需要授权凭据、云盘文件结构及 `xpan_auto` 适配器；部分入口会更名或移动云端文件。 |
| `legacy/save_generated_product_image.py` | 校验并整理生成的商品图片到目标素材目录。 | 需要本地输入图片、目标目录和 Pillow；实际图片未随此目录提供。 |
| `legacy/screen_career_templates.py` | 从职业规划模板中生成用于人工筛选的视觉审阅图。 | 需要模板清单及本地演示文稿；依赖 `curate_ppt_visuals.py`、LibreOffice、pypdfium2 和 Pillow。 |
| `legacy/second_pass_reorganize.py` | 执行职业规划与创新创业资料的二次分类整理及保留性核验。 | 需要历史云盘清单、整理计划与授权适配器；包含会修改云盘目录的入口。 |
| `legacy/verify_curation_delivery.py` | 历史交付后的分享目录与配套文件回读核验，并更新本地报告。 | 需要分享记录、配套文件、授权凭据、外部适配器和网络访问；会读取云端文件并写本地报告/说明。 |
| `legacy/verify_second_pass.py` | 历史二次整理后的分享入口、目录及配套文件核验。 | 需要历史报告/分享记录、授权凭据、外部适配器和网络访问；包含云端回读与本地报告更新。 |
| `legacy/商品图文字核查.swift` | 对清单中的商品图片执行中文/英文 OCR 并写出识别结果。 | 需要图片清单和图片文件；使用 macOS Foundation、Vision、AppKit。它是独立 OCR 工具，不受 Python/CJS 的默认运行保护。 |

## 运行保护与脱敏

所有 Python 文件在常规导入和业务代码前检查 `XIANYU_ENABLE_LEGACY_WORKFLOWS`；未显式设为 `1` 时会退出。CJS 检查同名变量后才加载 Playwright。此开关只用于避免误运行，并不代表流程已安全适配或可直接执行。Swift OCR 保留为独立工具，调用前应自行检查输入清单和输出位置。

原脚本中的 固定的 macOS 用户目录路径已移除，改为 `XIANYU_LEGACY_PATH_<脚本名>_<序号>` 环境变量，默认值是明确的 `/path/to/configure` 占位路径。浏览器检查脚本使用 `XIANYU_LEGACY_PLAYWRIGHT_PATH`、`XIANYU_LEGACY_CHROMIUM_PATH`、`XIANYU_LEGACY_SOURCE_ROOT` 和 `XIANYU_LEGACY_PREVIEW_URL`。旧检查器里的两个私有夸克分享 ID 已分别替换为 `XIANYU_LEGACY_SHARE_ID_CS` 和 `XIANYU_LEGACY_SHARE_ID_ZG`；不要把这些变量的值提交到仓库或日志。

旧脚本引用的 `xpan_auto.quark_adapter` 是外部本地适配器，本目录没有包含它，也不提供安装或凭据。占位路径、缺失的历史数据和适配器意味着这些脚本不是即插即用工具。上传、创建分享、重命名、移动、删除、分享读取等流程可能产生外部副作用；只有重新审核来源、输入、授权和副作用后，才可在独立测试资料上研究运行。

此目录不包含 Cookie、账号配置、云盘分享链接、分享 ID、数据库、浏览器会话、清单/报告 JSON、图片/PPT 源库或执行日志。历史结果只作流程背景，不能证明当前账户、云盘内容、商品素材或发布状态。
