# Anchor Schedule Web

一个可部署到 Zeabur 的 Flask + SQLite 小项目，用来给主播录入排班，并由管理员按月导出和桌面工具兼容的排班表。

## 功能

- 首次启动时，登录页会出现初始化按钮。
- 第一个账号固定为 `admin`，由你手动设置密码，自动成为管理员。
- 初始化完成后，登录页不再显示公开注册按钮。
- 管理员可以为其他主播创建账号，创建时需要填写账号、密码、主播名。
- 主播登录后可以录入排班字段：
  - 直播日期
  - 直播开始时间
  - 直播结束时间
  - 直播账号
- 系统会把录入记录和该账号对应的主播名一起保存。
- 管理员可以：
  - 注册新账号
  - 查看全部录入记录
  - 按月份、日期、主播、账号筛选
  - 选择排序字段和升降序
  - 编辑或删除记录
  - 下载指定月份的排班 Excel

## 本地运行

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

默认地址：

```text
http://127.0.0.1:5000
```

## 环境变量

- `SECRET_KEY`
  - 建议线上设置成随机长字符串。
- `DATABASE_URL`
  - 默认值是 `sqlite:///storage/anchor_schedule.db`
  - 如果不设置，会自动在项目内的 `storage` 目录创建 SQLite 数据库。
- `PORT`
  - Zeabur 会自动注入，应用已经兼容。

## Zeabur 部署

根据 Zeabur 官方 Python / Docker 服务文档，应用需要监听 `PORT`，而 SQLite 要配合持久化卷使用，避免容器重建后数据丢失。

建议部署方式：

1. 把这个目录单独推到一个仓库，或直接把它作为子目录部署。
2. 在 Zeabur 创建服务时使用仓库部署。
3. 使用仓库里的 `Dockerfile` 部署。
4. 挂载持久化存储到 `/app/storage`。
5. 设置环境变量：
   - `SECRET_KEY=你自己的随机密钥`
   - `DATABASE_URL=sqlite:////app/storage/anchor_schedule.db`

## 导出模板

导出的 Excel 会按主播拆分 worksheet，每个 sheet 都使用这 4 列：

- `日期`
- `直播开始时间`
- `直播结束时间`
- `直播账号`

这和你现有桌面工具的排班导入字段保持一致。
