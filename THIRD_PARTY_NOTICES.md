# 第三方来源与素材说明

## 闲鱼后台

后台依赖 [GuDong2003/xianyu-auto-reply-fix](https://github.com/GuDong2003/xianyu-auto-reply-fix)，固定提交为 `e8fe7ba4239614fe64d194cf3bed8a3aa16d5ab6`（本地部署版本 v2.0.7）。其代码遵循 AGPL-3.0；许可证副本见 [licenses/upstream-AGPL-3.0.txt](licenses/upstream-AGPL-3.0.txt)。仓库以安装脚本检出上游，不将第三方整份项目改名为本项目原创。

`patches/manual-verification-status-fix.patch` 是针对此上游的改动，包含相应测试差异，遵循上游 AGPL-3.0。它修正验证 iframe 仍存在时，外层聊天页变化被错误当作验证成功的问题。应用、分发或通过网络提供修改后的上游服务时，应遵守该许可证。

## 公开案例图片

`cases/` 中的 18 张 JPG 直接来自本项目 2026-10-13 已完成的商品发布素材。图片由真实 PPT 选样引导生成并作尺寸规范化；它们不是原页的逐像素截图。没有因本次 GitHub 展示重新绘制图片。每张图片的尺寸、大小和 SHA-256 记录在案例清单中。

案例原文件、人物、标志、字体、插画及第三方素材的权利属于相应权利人。仓库公开用于展示工作流程及成品效果，不表示拥有整套 PPT 源库的全部权利，也不授予对第三方素材的再次销售、再分发或商用许可。涉及样例人物经历、奖项、机构与数据时，应视为样例内容，不当作维护者的实际成果。

## 本项目代码和文档

本仓库未为原创整理脚本、文档和案例图片添加统一的开源许可。公开可查看不等于取得任意复用或商业再分发授权。上游及其派生补丁的许可单独适用。

## 研究参考

- [GuDong2003/xianyu-auto-reply-fix](https://github.com/GuDong2003/xianyu-auto-reply-fix)：实际本地部署基础。
- [zhinianboke/xianyu-auto-reply](https://github.com/zhinianboke/xianyu-auto-reply)：自动回复与订单流程调研参考。
- [23Star/xianyu-super-butler](https://github.com/23Star/xianyu-super-butler)：后台能力比较参考。
- [OpenListTeam/OpenList](https://github.com/OpenListTeam/OpenList)：历史夸克上传脚本中的协议研究参考。

未把这些参考仓库的下载副本、各自依赖或 Git 历史一并发布。
