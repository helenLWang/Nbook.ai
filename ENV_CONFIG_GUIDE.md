# .env 配置文件指南 - 方案一（URS 标准）

## 配置格式

请在项目根目录的 `.env` 文件中使用以下格式（方案一 - URS 标准命名）：

```env
# Reddit API 配置 - 方案一（URS 标准命名）
CLIENT_ID=你的client_id
CLIENT_SECRET=你的client_secret
REDDIT_USERNAME=你的reddit用户名
REDDIT_PASSWORD=你的reddit密码
USER_AGENT=nail-scheduling-research-script v1.0
```

## 获取 Reddit API 凭证的步骤

1. 访问 https://www.reddit.com/prefs/apps
2. 点击页面底部的 **"create another app..."** 或 **"create app"** 按钮
3. 选择应用类型为 **"script"**
4. 填写：
   - **name**: 随便起个名字（如 "nail scheduling research"）
   - **description**: 描述（如 "Research tool for nail tech scheduling"）
   - **redirect uri**: 填 `http://localhost:8080`
5. 点击 **"create app"**
6. 创建后，你会看到：
   - **client_id**: 在应用名称下方，类似 `abc123xyz`
   - **client_secret**: 点击 **"secret"** 按钮显示，类似 `def456uvw`

## 配置示例

```env
CLIENT_ID=abc123xyz_你的实际client_id
CLIENT_SECRET=def456uvw_你的实际client_secret
REDDIT_USERNAME=your_reddit_username
REDDIT_PASSWORD=your_reddit_password
USER_AGENT=nail-scheduling-research-script v1.0
```

## 注意事项

- 不要将 `.env` 文件提交到 Git（已在 .gitignore 中）
- 确保所有值都没有引号（除非值本身包含空格）
- `USER_AGENT` 可以是任意描述性字符串

## 验证配置

配置完成后，运行以下命令验证：

```bash
python reddit_scraper.py
```

如果配置正确，你会看到：
```
✓ Reddit 连接成功，用户：你的用户名
✓ URS 工具已加载
```

如果配置错误，脚本会显示详细的配置指引。
