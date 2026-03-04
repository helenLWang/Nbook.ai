# Reddit 爬虫使用说明

## 功能
抓取 Reddit 上 2023-2026 年期间，包含以下关键词的帖子：
- reschedule / reshedule（改期）
- communication（沟通）
- cancel / cancellation（取消）
- no time / time management（时间问题）
- double book（重复预约）
- no show（爽约）
- appointment / booking（预约）
- schedule / scheduling（排班）

## 使用步骤

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 配置 Reddit API

#### 获取 Reddit API 凭证：
1. 访问 https://www.reddit.com/prefs/apps
2. 点击 "create another app..." 或 "create app"
3. 选择 **"script"** 类型
4. 填写：
   - **name**: 随便起个名字（如 "nail scheduling research"）
   - **description**: 描述（如 "Research tool for nail tech scheduling"）
   - **redirect uri**: 填 `http://localhost:8080`
5. 创建后，你会看到：
   - **client_id**: 在应用名称下方，类似 `abc123xyz`
   - **client_secret**: 点击 "secret" 按钮显示，类似 `def456uvw`

#### 配置环境变量：
1. 复制 `.env.example` 为 `.env`
2. 编辑 `.env` 文件，填入你的 Reddit API 信息：
```
REDDIT_CLIENT_ID=你的client_id
REDDIT_CLIENT_SECRET=你的client_secret
REDDIT_USERNAME=你的reddit用户名
REDDIT_PASSWORD=你的reddit密码
REDDIT_USER_AGENT=nail-scheduling-research-script v1.0
```

### 3. 运行脚本
```bash
python reddit_scraper.py
```

## 输出文件

脚本会生成以下文件：

1. **reddit_posts_YYYYMMDD_HHMMSS.csv**
   - 完整的帖子数据（CSV 格式，可用 Excel 打开）

2. **reddit_posts_YYYYMMDD_HHMMSS.json**
   - 完整的帖子数据（JSON 格式，便于程序处理）

3. **reddit_analysis_report_YYYYMMDD_HHMMSS.txt**
   - 简要分析报告

## 统计内容

脚本会自动生成以下统计：

1. **关键词出现频率**（Top 10）
2. **按 Subreddit 统计**（帖子数、平均点赞、平均评论）
3. **按年度统计**（2023、2024、2025、2026）
4. **最热门帖子**（按点赞数排序，Top 10）
5. **最受讨论帖子**（按评论数排序，Top 10）
6. **关键词组合频率**（哪些关键词经常一起出现）

## 注意事项

- Reddit API 有速率限制，脚本会自动处理
- 如果遇到连接问题，检查网络和 API 凭证
- 数据抓取可能需要一些时间，请耐心等待
- 建议在非高峰时段运行（避免触发速率限制）

## 自定义配置

可以在 `reddit_scraper.py` 中修改：

- **KEYWORDS**: 添加或删除关键词
- **SUBREDDITS**: 添加或删除要搜索的版块
- **START_DATE / END_DATE**: 修改时间范围
- **limit_per_sub**: 每个 subreddit 每个关键词的搜索数量限制
