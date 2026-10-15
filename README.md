<div align="center">

# Xianyu Listing Studio

**闲鱼商品发布工作台**

把资料盘点、商品九图、文案准备和本地后台部署整理为一套可复核的流程。

[完整案例](cases/README.md) · [快速开始](docs/getting-started.md) · [项目架构](docs/architecture.md) · [资料到发布](docs/workflow.md) · [运行与验证](docs/operations.md)

</div>

## 先看已经做好的商品

这里展示的图片来自本项目已完成的两款 PPT 资料商品，直接使用 2026-10-13 的最终发布准备 JPG。每款都有完整 9 图和独立文案，不是临时制作的占位图片。

<table>
<tr><th>大学生职业规划</th><th>创新创业大赛</th></tr>
<tr>
<td><a href="cases/career-planning/README.md"><img src="cases/career-planning/images/01.jpg" alt="大学生职业规划商品主图" width="440"></a></td>
<td><a href="cases/innovation-startup/README.md"><img src="cases/innovation-startup/images/01.jpg" alt="创新创业大赛商品主图" width="440"></a></td>
</tr>
<tr><td>784 份演示文件的资料合集；选样 4 套、86 页</td><td>694 份演示文件的资料合集；选样 4 套、82 页</td></tr>
<tr><td><a href="cases/career-planning/README.md">查看完整 9 图与文案 →</a></td><td><a href="cases/innovation-startup/README.md">查看完整 9 图与文案 →</a></td></tr>
</table>

**案例状态：商品展示素材已完成，尚无已核验的闲鱼上架或成交记录。** 784 / 694 按演示文件数量计，包含模板、案例与指南；不代表全部为空白、可编辑的模板。展示图是依据真实 PPT 选样制作的 AI 辅助商品图，局部细节不等同于原始页面。

## 这个项目解决什么问题

整理大量 PPT 资源时，文件名和数量很难说明真实内容。这个工作台把原始目录盘点、文件去重、内容分类、真实选样、连续详情展示和发布文案串起来，并保留每个阶段的核验边界。

| 模块 | 当前提供的内容 | 入口 |
| --- | --- | --- |
| 资料整理 | 盘点、哈希去重、按用途归类、抽样与目录核验的流程及历史源码 | [工作流程](docs/workflow.md) / [历史脚本](workflows/README.md) |
| 商品展示 | 2 款 × 9 张真实成品 JPG、顺序和校验清单 | [案例目录](cases/README.md) |
| 文案准备 | 标题与正文合并的单输入框文案，待确认承诺明确标注 | [职业规划文案](cases/career-planning/listing-copy.txt) / [创新创业文案](cases/innovation-startup/listing-copy.txt) |
| 本地后台 | 上游固定版本接入、管理员初始化、本机启动与 macOS 服务管理 | [快速开始](docs/getting-started.md) |
| 状态修正 | 验证 iframe 未消失时避免误判成功的补丁及测试差异 | [补丁](patches/manual-verification-status-fix.patch) |
| 交付与发布核验 | 元数据 / 抽样回读 / 真实上架 / 订单履约的分阶段验收口径 | [运行与验证](docs/operations.md) |

## 九图如何组织

每款采用 **1 张 1:1 主图 + 8 张 3:4 详情图**。主图集中展示四套封面；每套正文连续看两张，再切到下一套，避免把不同项目的内页混在一起。

| 位置 | 任务 | 成品尺寸 |
| --- | --- | --- |
| 01 | 四款封面与商品主题 | 1800 × 1800 |
| 02–03 | 第 1 套正文连续展示 | 1800 × 2400 |
| 04–05 | 第 2 套正文连续展示 | 1800 × 2400 |
| 06–07 | 第 3 套正文连续展示 | 1800 × 2400 |
| 08–09 | 第 4 套正文连续展示 | 1800 × 2400 |

图片在两个案例 README 中全部可见，点击即可看原尺寸文件。每张图都有 SHA-256；GitHub 展示版没有重新生成或压缩这些 JPG。

## 快速查看与校验

```bash
git clone https://github.com/kirilovamanolo490-ship-it/xianyu-listing-studio.git
cd xianyu-listing-studio
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-gallery.txt
python tools/validate_publication.py
```

浏览案例直接打开上面的 GitHub 链接即可，不需要登录闲鱼，也不会触发商品发布。校验脚本只读取本仓库，核对 18 张图片、文档本地链接和禁止公开的文件类型。

需要运行本地后台时，继续阅读 [完整安装步骤](docs/getting-started.md)。后台基于 [GuDong2003/xianyu-auto-reply-fix](https://github.com/GuDong2003/xianyu-auto-reply-fix)，固定检出 `e8fe7ba4239614fe64d194cf3bed8a3aa16d5ab6`，并应用本仓库补丁。运行适配默认绑定 `127.0.0.1:18790`。

## 仓库结构

```text
cases/                       两款完整九图、文案与图片清单
docs/                        架构、操作、资料流程和公开范围
runtime/                     不含凭据的本地启动与服务脚本
scripts/bootstrap_upstream.sh 固定上游检出与补丁应用
patches/                     本项目的上游修正
workflows/legacy/            历史批处理源码，默认禁用执行
tools/validate_publication.py 公开素材与文档校验
licenses/                    上游许可证副本
```

## 验证过什么

| 证据时间 | 已有证据 | 不能据此推断 |
| --- | --- | --- |
| 2026-10-10 | 本地后台可登录；素材保存与重新载入；发布接口鉴权响应；11 项发布相关单元测试通过 | 闲鱼已上架、自动发货已完成 |
| 2026-10-11 | 记录到业务会话过期，需人工恢复 | 心跳在线就表示业务登录有效 |
| 2026-10-13 | 两款完整九图与文案准备完成；资料整理与核验记录 | 价格、类目、上架与付款履约已验收 |
| 2026-10-15 | 18 张图片哈希与尺寸、文档链接检查通过；固定上游补丁检查通过；35 项相关单元测试通过 | 重新验证了全部历史云盘数据或平台接口 |

本次详细记录见 [公开版核验记录](docs/verification.md)。

现有资料没有两款商品的线上商品 ID 或真实已付款订单闭环。公开文案已把未经验证的自动秒发、费用和退款承诺改为待确认字段。

## 来源与公开范围

后台上游及其派生补丁适用 AGPL-3.0，详见 [第三方来源与素材说明](THIRD_PARTY_NOTICES.md)。图片展示并不转授第三方 PPT、人物、字体或其他素材的商业再分发权利。

本仓库保留项目核心信息、核心流程源码与完整案例。账号凭据、数据库、浏览器会话、交付链接和全套 PPT 源库保留在本机，详见 [公开范围清单](docs/publication-scope.md)。
