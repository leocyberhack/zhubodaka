# Anchor Schedule Web

一个可部署到 Zeabur 的 Flask + SQLite 小项目，用来给主播录入排班，并由管理员按月导出和桌面工具兼容的排班表。

## 当前功能

### 登录与权限

- 首次启动时，登录页会显示初始化按钮。
- 第一个账号固定为 `admin`，由你手动设置密码，自动成为管理员。
- 初始化完成后，登录页不再显示公开注册按钮。
- 只有管理员可以继续创建新账号。

### 管理员能力

- 创建主播账号，需要填写：
  - 账号
  - 密码
  - 主播名
- 查看所有账号。
- 查看账号明文密码。
  - 新创建账号会直接保存可见密码。
  - 历史账号如果之前没有保存明文，会显示“历史账号不可回显”。
  - 管理员可以通过“重置密码”让旧账号重新拥有可见密码。
- 管理员代主播录入排班。
  - 录入时主播名必须从已注册主播列表中选择，不能手动输入。
- 查看全部排班记录。
- 按以下条件筛选记录：
  - 月份
  - 日期
  - 主播
  - 直播账号
  - 关键词
  - 升序 / 降序
- 编辑记录。
- 删除记录。
- 选择“年份 + 月份”后下载该年月的排班 Excel。

### 主播能力

- 使用管理员分配的账号和密码登录。
- 录入以下字段：
  - 直播日期
  - 直播开始时间
  - 直播结束时间
  - 直播账号
- 系统会自动把记录和该账号绑定的主播名一起保存。
- “最近录入”区域只显示当前账号自己录入的记录。
- 主播可以删除自己录入的记录，方便修正误操作。
- 主播不能删除别人录入的记录，也不能进入管理员页面。

### 导出 Excel

导出的 Excel 会按主播拆分 worksheet，每个 sheet 都使用这 4 列：

- `日期`
- `直播开始时间`
- `直播结束时间`
- `直播账号`

这和你现有桌面工具的排班导入字段保持一致。

## 技术栈

- Flask
- Flask-SQLAlchemy
- SQLite
- openpyxl

## 项目结构

```text
anchor_schedule_web/
├─ app.py
├─ Dockerfile
├─ requirements.txt
├─ start_local_test.bat
├─ storage/
└─ portal/
   ├─ __init__.py
   ├─ extensions.py
   ├─ models.py
   ├─ routes.py
   ├─ excel_export.py
   ├─ static/
   │  └─ styles.css
   └─ templates/
```

## 本地启动

### 方式 1：一键启动

直接双击：

```text
start_local_test.bat
```

脚本会自动：

- 优先使用上一级目录的 `venv`
- 安装/校验依赖
- 检查并尝试释放 `5000` 端口
- 启动本地测试服务

默认访问地址：

```text
http://127.0.0.1:5000
```

### 方式 2：命令行启动

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
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

建议部署方式：

1. 直接把当前仓库部署到 Zeabur。
2. 使用仓库里的 `Dockerfile`。
3. 给服务挂载持久化存储到 `/app/storage`。
4. 设置环境变量：
   - `SECRET_KEY=你自己的随机密钥`
   - `DATABASE_URL=sqlite:////app/storage/anchor_schedule.db`

## 数据与安全说明

- 当前版本为了满足业务需求，管理员页面可以直接看到账号明文密码。
- 这会降低安全性，只适合内部使用场景。
- 如果后续要正式公网使用，建议改成：
  - 不显示明文密码
  - 只允许管理员重置密码
  - 增加操作日志
  - 增加更严格的权限控制
