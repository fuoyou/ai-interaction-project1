# 课件解析失败：structure_data 字段长度（已修复）

## 现象

- 前端：**课件处理失败，无法学习本课件**（`status === 9` / `task_status === failed`）。
- 接口：`fileUrl` 可能已是 `.pdf`（说明 **PPT→PDF、甚至 Paddle 解析已成功**），但 `page_count` 为 0、`aiScript` 为空。
- 数据库：`biz_lesson.structure_data` 可能为 **NULL**，详情接口里 **`parseError` 缺失**（因提交失败链路异常时未稳定写入）。
- 本地用小脚本测同一文件能通过，但走完整上传链路的大课件失败。

## 根因

- 解析成功后会把 **`paddlePages`（整页版面 JSON）** 与 `chapters` 一并写入 **`biz_lesson.structure_data`**。
- 原表结构该列为 MySQL **`TEXT`（约 64KB）**。
- 页数多、块多的课件，`structure_data` 的 JSON **超过 64KB** 时，`db.session.commit()` 失败（常见：**Data too long for column** / MySQL **1406**）。
- 失败发生在「Paddle 已通过、准备进入讲稿生成」阶段，因此容易误判为「PPT/WPS/Paddle 有问题」。

## 修复（代码与库表）

1. **模型**：`structure_data` 改为 **`LONGTEXT`**（与 `rag_chunks` 类似用法）。
2. **迁移**：`app.py` 启动时执行  
   `ALTER TABLE biz_lesson MODIFY COLUMN structure_data LONGTEXT ...`
3. **容错**：在写入大块 `structure_data` 后的 `commit` 上捕获 **1406 / Data too long**，通过 `_lesson_fail_parse` 返回明确中文提示。
4. **日志**：`uploads/parse_errors.log` 使用**后端根目录绝对路径**，避免工作目录不同导致「找不到日志」。

## 运维注意

- **升级后必须重启后端**，让迁移 SQL 跑至少一次。
- 若仍失败，查看 **`fanya-ai-backend/uploads/parse_errors.log`** 与接口中的 **`data.parseError`**。

记录日期：与「structure_data → LONGTEXT」修复同期。
