# 快速开始

本公开版有两条独立使用路径：直接查看商品案例，或检出上游后运行本地后台。历史云盘批处理另见 [workflows/README.md](../workflows/README.md)，默认禁用执行。

## 查看案例与检查图片

案例和文案均可直接在 GitHub 浏览。若要在本机核对，准备 Python 3.10 或更新版本：

```bash
git clone https://github.com/kirilovamanolo490-ship-it/xianyu-listing-studio.git
cd xianyu-listing-studio
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-gallery.txt
python tools/validate_publication.py
```

脚本检查两款各 9 张、图片顺序、尺寸、文件大小、SHA-256、文档本地链接，以及工作副本中不应发布的文件。它不连接闲鱼或网盘。`cases/*/images/` 中的文件就是本项目原有成品 JPG。

## 运行本地闲鱼后台（macOS）

本项目的历史实际部署环境是 macOS、Python 3.11。以下步骤需要 Git、Python 3.11 和网络；上游依赖安装与平台登录需在自己的环境重新验证。macOS 服务管理使用 `launchctl`，不适用于 Windows 或 Linux。

在仓库根目录执行：

```bash
bash scripts/bootstrap_upstream.sh
python3.11 -m venv apps/xianyu-auto-reply-fix/.venv
apps/xianyu-auto-reply-fix/.venv/bin/python -m pip install -r apps/xianyu-auto-reply-fix/requirements.txt
PLAYWRIGHT_SKIP_BROWSER_GC=1 apps/xianyu-auto-reply-fix/.venv/bin/python -m playwright install chromium
apps/xianyu-auto-reply-fix/.venv/bin/python runtime/setup_local.py
apps/xianyu-auto-reply-fix/.venv/bin/python runtime/start_gudong.py
```

`bootstrap_upstream.sh` 克隆原作者仓库并检出固定提交，应用人工验证状态修正。已有目录的来源、版本或工作树不符合预期时会停止，不会强制重置工作。脚本只处理代码，不安装依赖、不登录账号、不提交商品。

启动后打开 `http://127.0.0.1:18790`。本地管理员初始化脚本生成随机密码并写入 `runtime/admin-credentials.json`，权限为 `0600`，重复执行保留现有凭据。该文件不进入 Git。管理员登录与闲鱼账号扫码登录是不同步骤。

浏览器解析使用已安装的 Playwright Chromium；通过 `PLAYWRIGHT_BROWSERS_PATH` 可指定自己的缓存目录。默认关闭自动滑块和 Drission 回退，平台验证由操作者在可见界面手动完成。

## 可选：macOS 登录后自动启动

先停止上面前台运行的服务，避免端口冲突，再执行：

```bash
apps/xianyu-auto-reply-fix/.venv/bin/python runtime/manage_service.py install
apps/xianyu-auto-reply-fix/.venv/bin/python runtime/manage_service.py status
# 其他操作：stop / start / restart
```

这会安装用户 LaunchAgent。`stop` 停止当前会话中的服务；下次用户登录仍可能启动。取消后续自动启动需自行移除对应 LaunchAgent。脚本遇到同名但路径不同的已有服务会拒绝覆盖。电脑休眠或断网会影响服务，不应据此承诺 24 小时履约。

## 验证补丁与发布相关单元测试

上游就绪后，在仓库根目录执行：

```bash
cd apps/xianyu-auto-reply-fix
.venv/bin/python -m unittest discover -s tests -p 'test_product_sku.py'
.venv/bin/python -m unittest discover -s tests -p 'test_item_publisher_sku.py'
.venv/bin/python -m unittest discover -s tests -p 'test_slider_verification_guards.py'
```

这些是本地代码测试。平台实际发布必须取得商品 ID、链接及商品列表可见性；自动发货必须另外核对已付款订单的发送与履约状态。历史验证的日期和边界见 [运行与验证](operations.md)。
