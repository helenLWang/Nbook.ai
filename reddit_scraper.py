"""
Reddit 爬虫：抓取美甲师排单相关抱怨和讨论
时间范围：2023-2026年
关键词：reschedule, communication, cancel, no time 等
"""

import praw
import pandas as pd
from datetime import datetime, timezone
import re
import json
from collections import Counter
import os
import sys
from dotenv import load_dotenv

# 添加 URS 路径以便导入其工具
URS_PATH = r"C:\Users\13360\Downloads\URS-master"
if os.path.exists(URS_PATH) and URS_PATH not in sys.path:
    sys.path.insert(0, URS_PATH)

try:
    from urs.praw_scrapers.utils.Objectify import Objectify
    from urs.utils.Global import convert_time
    URS_AVAILABLE = True
except ImportError:
    URS_AVAILABLE = False
    print("警告：无法导入 URS 工具，将使用基础方法")

# 加载环境变量
load_dotenv()

# Reddit API 配置（从环境变量读取，优先使用 URS 的命名，兼容我们的命名）
CLIENT_ID = os.getenv("CLIENT_ID") or os.getenv("REDDIT_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("CLIENT_SECRET") or os.getenv("REDDIT_CLIENT_SECRET", "")
USERNAME = os.getenv("REDDIT_USERNAME", "")
PASSWORD = os.getenv("REDDIT_PASSWORD", "")
USER_AGENT = os.getenv("USER_AGENT") or os.getenv("REDDIT_USER_AGENT", "nail-scheduling-research-script v1.0")

# 关键词列表（不区分大小写）
KEYWORDS = [
    "reschedule", "reshedule",  # 改期
    "communication", "communicate",  # 沟通
    "cancel", "cancellation", "cancelled",  # 取消
    "no time", "not enough time", "time management",  # 时间问题
    "double book", "double booking",  # 重复预约
    "no show", "no-show",  # 爽约
    "appointment", "booking",  # 预约
    "client", "customer",  # 客户
    "schedule", "scheduling",  # 排班
]

# 抱怨相关关键词（用于识别抱怨内容）
COMPLAINT_KEYWORDS = [
    "frustrated", "frustrating", "annoying", "annoyed",
    "problem", "issue", "difficult", "hard",
    "hate", "complaint", "complain",
    "mess", "chaos", "confusion",
    "late", "delay", "missed",
    "forgot", "forget", "mistake",
    "wrong", "error", "failed",
]

# 要搜索的 subreddit（美甲师、美业、小商家相关）
SUBREDDITS = [
    "nailtechs",
    "NailArt",
    "Hairstylist",
    "SmallBusiness",
    "Entrepreneur",
    "beauty",
    "skincare",
    "Esthetics",
]

# 时间范围
START_DATE = datetime(2023, 1, 1, tzinfo=timezone.utc)
END_DATE = datetime(2026, 1, 1, tzinfo=timezone.utc)


def init_reddit():
    """初始化 Reddit 客户端（使用 URS 的方法）"""
    if not all([CLIENT_ID, CLIENT_SECRET, USERNAME, PASSWORD]):
        print("=" * 60)
        print("错误：请先配置 Reddit API 凭证")
        print("=" * 60)
        print("\n请按以下步骤操作：")
        print("1. 访问 https://www.reddit.com/prefs/apps")
        print("2. 点击 'create another app...'")
        print("3. 选择 'script' 类型")
        print("4. 填写名称和描述，redirect uri 填 http://localhost:8080")
        print("5. 创建后，你会得到 client_id 和 client_secret")
        print("\n然后在项目根目录创建 .env 文件，添加：")
        print("CLIENT_ID=你的client_id (或 REDDIT_CLIENT_ID)")
        print("CLIENT_SECRET=你的client_secret (或 REDDIT_CLIENT_SECRET)")
        print("REDDIT_USERNAME=你的reddit用户名")
        print("REDDIT_PASSWORD=你的reddit密码")
        print("USER_AGENT=你的应用描述 (或 REDDIT_USER_AGENT)")
        print("=" * 60)
        return None
    
    try:
        # 使用 URS 的方式初始化（与 URS 保持一致）
        reddit = praw.Reddit(
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            user_agent=USER_AGENT,
            username=USERNAME,
            password=PASSWORD,
        )
        # 测试连接
        reddit.user.me()
        print(f"✓ Reddit 连接成功，用户：{reddit.user.me()}")
        if URS_AVAILABLE:
            print("✓ URS 工具已加载")
        return reddit
    except Exception as e:
        print(f"✗ Reddit 连接失败：{e}")
        return None


def contains_keywords(text, keywords):
    """检查文本是否包含关键词"""
    if not text:
        return False
    text_lower = text.lower()
    for keyword in keywords:
        if keyword.lower() in text_lower:
            return True
    return False


def extract_keywords_found(text, keywords):
    """提取文本中匹配到的关键词"""
    if not text:
        return []
    text_lower = text.lower()
    found = []
    for keyword in keywords:
        if keyword.lower() in text_lower:
            found.append(keyword)
    return found


def is_in_date_range(post_date):
    """检查帖子是否在时间范围内"""
    return START_DATE <= post_date <= END_DATE


def scrape_comments(reddit, post, max_comments=20):
    """抓取帖子的热门评论（包含抱怨关键词的）"""
    comments_data = []
    try:
        post.comments.replace_more(limit=0)  # 展开所有评论
        comment_count = 0
        for comment in post.comments.list():
            if comment_count >= max_comments:
                break
            if hasattr(comment, 'body') and comment.body:
                comment_text = comment.body
                # 检查评论是否包含关键词或抱怨关键词
                if (contains_keywords(comment_text, KEYWORDS) or 
                    contains_keywords(comment_text, COMPLAINT_KEYWORDS)):
                    comments_data.append({
                        "comment_id": comment.id,
                        "body": comment_text[:300],  # 限制长度
                        "score": comment.score,
                        "created_utc": datetime.fromtimestamp(comment.created_utc, tz=timezone.utc),
                        "author": str(comment.author) if comment.author else "[deleted]",
                    })
                    comment_count += 1
    except Exception as e:
        # 评论抓取失败不影响主流程
        pass
    return comments_data


def scrape_posts(reddit, limit_per_sub=200, include_comments=True):
    """抓取帖子（可选：包含评论）"""
    all_posts = []
    total_found = 0
    
    print(f"\n开始抓取数据...")
    print(f"时间范围：{START_DATE.date()} 至 {END_DATE.date()}")
    print(f"关键词：{', '.join(KEYWORDS[:5])}... (共 {len(KEYWORDS)} 个)")
    print(f"抱怨关键词：{', '.join(COMPLAINT_KEYWORDS[:5])}... (共 {len(COMPLAINT_KEYWORDS)} 个)")
    print(f"Subreddits：{', '.join(SUBREDDITS)}")
    print(f"包含评论：{'是' if include_comments else '否'}")
    print("-" * 60)
    
    for subreddit_name in SUBREDDITS:
        try:
            subreddit = reddit.subreddit(subreddit_name)
            print(f"\n正在搜索 r/{subreddit_name}...")
            
            # 搜索每个关键词
            for keyword in KEYWORDS:
                try:
                    count = 0
                    for post in subreddit.search(keyword, limit=limit_per_sub, sort="relevance", time_filter="all"):
                        post_date = datetime.fromtimestamp(post.created_utc, tz=timezone.utc)
                        
                        # 检查时间范围
                        if not is_in_date_range(post_date):
                            continue
                        
                        # 检查是否包含关键词（标题或正文）
                        title_text = post.title
                        body_text = post.selftext
                        combined_text = f"{title_text} {body_text}"
                        
                        if contains_keywords(combined_text, KEYWORDS):
                            keywords_found = extract_keywords_found(combined_text, KEYWORDS)
                            
                            # 检查是否包含抱怨关键词
                            is_complaint = contains_keywords(combined_text, COMPLAINT_KEYWORDS)
                            complaint_keywords_found = extract_keywords_found(combined_text, COMPLAINT_KEYWORDS) if is_complaint else []
                            
                            # 使用 URS 的 Objectify 方法格式化数据（如果可用）
                            if URS_AVAILABLE:
                                try:
                                    objectify = Objectify()
                                    submission_obj = objectify.make_submission(False, post)
                                    # 使用 URS 格式化的数据，但添加我们的额外字段
                                    post_data = submission_obj.copy()
                                    post_data.update({
                                        "subreddit": subreddit_name,
                                        "keyword_searched": keyword,
                                        "keywords_found": ", ".join(keywords_found),
                                        "is_complaint": is_complaint,
                                        "complaint_keywords": ", ".join(complaint_keywords_found) if complaint_keywords_found else "",
                                        "created_date": post_date.date(),
                                    })
                                except Exception as e:
                                    # 如果 URS 格式化失败，使用基础方法
                                    post_data = {
                                        "subreddit": subreddit_name,
                                        "keyword_searched": keyword,
                                        "keywords_found": ", ".join(keywords_found),
                                        "is_complaint": is_complaint,
                                        "complaint_keywords": ", ".join(complaint_keywords_found) if complaint_keywords_found else "",
                                        "post_id": post.id,
                                        "title": title_text,
                                        "selftext": body_text[:500] if body_text else "",
                                        "score": post.score,
                                        "num_comments": post.num_comments,
                                        "created_utc": post_date,
                                        "created_date": post_date.date(),
                                        "url": post.url,
                                        "permalink": f"https://www.reddit.com{post.permalink}",
                                        "author": str(post.author) if post.author else "[deleted]",
                                    }
                            else:
                                # 使用基础方法
                                post_data = {
                                    "subreddit": subreddit_name,
                                    "keyword_searched": keyword,
                                    "keywords_found": ", ".join(keywords_found),
                                    "is_complaint": is_complaint,
                                    "complaint_keywords": ", ".join(complaint_keywords_found) if complaint_keywords_found else "",
                                    "post_id": post.id,
                                    "title": title_text,
                                    "selftext": body_text[:500] if body_text else "",
                                    "score": post.score,
                                    "num_comments": post.num_comments,
                                    "created_utc": post_date,
                                    "created_date": post_date.date(),
                                    "url": post.url,
                                    "permalink": f"https://www.reddit.com{post.permalink}",
                                    "author": str(post.author) if post.author else "[deleted]",
                                }
                            
                            # 抓取评论（如果启用）
                            comments_data = []
                            if include_comments and post.num_comments > 0:
                                comments_data = scrape_comments(reddit, post, max_comments=10)
                            
                            # 添加评论相关字段
                            post_data["comments_scraped"] = len(comments_data)
                            
                            # 如果有评论，添加评论数据
                            if comments_data:
                                post_data["top_comments"] = comments_data
                            
                            all_posts.append(post_data)
                            count += 1
                            total_found += 1
                            
                            if count % 10 == 0:
                                print(f"  已找到 {count} 条匹配帖子...", end="\r")
                    
                    if count > 0:
                        print(f"  关键词 '{keyword}': 找到 {count} 条")
                
                except Exception as e:
                    print(f"  搜索关键词 '{keyword}' 时出错：{e}")
                    continue
            
            print(f"  r/{subreddit_name} 总计：{len([p for p in all_posts if p['subreddit'] == subreddit_name])} 条")
        
        except Exception as e:
            print(f"  访问 r/{subreddit_name} 时出错：{e}")
            continue
    
    print(f"\n" + "=" * 60)
    print(f"抓取完成！共找到 {len(all_posts)} 条匹配的帖子")
    complaint_count = len([p for p in all_posts if p.get('is_complaint', False)])
    print(f"其中包含抱怨的帖子：{complaint_count} 条")
    print("=" * 60)
    
    return all_posts


def analyze_and_summarize(posts):
    """统计分析和排序"""
    if not posts:
        print("没有数据可分析")
        return None
    
    # 处理嵌套的评论数据，先展开
    flattened_posts = []
    for post in posts:
        post_copy = post.copy()
        if "top_comments" in post_copy:
            # 将评论数据转换为字符串（用于 CSV 导出）
            comments_text = "\n---\n".join([f"[{c['author']}] {c['body']}" for c in post_copy["top_comments"]])
            post_copy["comments_text"] = comments_text
            # 保留原始评论数据用于 JSON
        flattened_posts.append(post_copy)
    
    df = pd.DataFrame(flattened_posts)
    
    # 去重（基于 post_id）
    df = df.drop_duplicates(subset=["post_id"], keep="first")
    print(f"\n去重后剩余 {len(df)} 条帖子")
    
    # 1. 按关键词出现频率统计
    print("\n" + "=" * 60)
    print("关键词出现频率统计（Top 10）")
    print("=" * 60)
    keyword_counter = Counter()
    for keywords_str in df["keywords_found"]:
        if keywords_str:
            for kw in keywords_str.split(", "):
                keyword_counter[kw.strip()] += 1
    
    top_keywords = keyword_counter.most_common(10)
    for kw, count in top_keywords:
        print(f"  {kw:20s}: {count:4d} 次")
    
    # 2. 按 subreddit 统计
    print("\n" + "=" * 60)
    print("按 Subreddit 统计")
    print("=" * 60)
    subreddit_stats = df.groupby("subreddit").agg({
        "post_id": "count",
        "score": "mean",
        "num_comments": "mean",
    }).round(2)
    subreddit_stats.columns = ["帖子数", "平均点赞", "平均评论数"]
    subreddit_stats = subreddit_stats.sort_values("帖子数", ascending=False)
    print(subreddit_stats.to_string())
    
    # 3. 按时间统计（年度）
    print("\n" + "=" * 60)
    print("按年度统计")
    print("=" * 60)
    df["year"] = df["created_date"].apply(lambda x: x.year)
    year_stats = df.groupby("year").agg({
        "post_id": "count",
        "score": "mean",
    }).round(2)
    year_stats.columns = ["帖子数", "平均点赞"]
    print(year_stats.to_string())
    
    # 4. 最热门的帖子（按点赞数）
    print("\n" + "=" * 60)
    print("最热门的帖子（Top 10，按点赞数）")
    print("=" * 60)
    top_posts = df.nlargest(10, "score")[
        ["title", "subreddit", "score", "num_comments", "created_date", "keywords_found"]
    ]
    for idx, row in top_posts.iterrows():
        print(f"\n[{row['subreddit']}] {row['title'][:60]}...")
        print(f"  点赞: {row['score']}, 评论: {row['num_comments']}, 日期: {row['created_date']}")
        print(f"  关键词: {row['keywords_found']}")
    
    # 5. 最受讨论的帖子（按评论数）
    print("\n" + "=" * 60)
    print("最受讨论的帖子（Top 10，按评论数）")
    print("=" * 60)
    top_discussed = df.nlargest(10, "num_comments")[
        ["title", "subreddit", "score", "num_comments", "created_date", "keywords_found"]
    ]
    for idx, row in top_discussed.iterrows():
        print(f"\n[{row['subreddit']}] {row['title'][:60]}...")
        print(f"  点赞: {row['score']}, 评论: {row['num_comments']}, 日期: {row['created_date']}")
        print(f"  关键词: {row['keywords_found']}")
    
    # 6. 按关键词组合统计
    print("\n" + "=" * 60)
    print("关键词组合出现频率（Top 10）")
    print("=" * 60)
    keyword_combo_counter = Counter()
    for keywords_str in df["keywords_found"]:
        if keywords_str:
            keywords_list = [kw.strip() for kw in keywords_str.split(", ")]
            if len(keywords_list) > 1:
                # 生成两两组合
                for i in range(len(keywords_list)):
                    for j in range(i + 1, len(keywords_list)):
                        combo = f"{keywords_list[i]} + {keywords_list[j]}"
                        keyword_combo_counter[combo] += 1
    
    top_combos = keyword_combo_counter.most_common(10)
    for combo, count in top_combos:
        print(f"  {combo:40s}: {count:4d} 次")
    
    # 7. 抱怨相关统计
    if "is_complaint" in df.columns:
        print("\n" + "=" * 60)
        print("抱怨相关统计")
        print("=" * 60)
        complaint_df = df[df["is_complaint"] == True]
        print(f"包含抱怨的帖子数：{len(complaint_df)}")
        print(f"抱怨帖子占比：{len(complaint_df)/len(df)*100:.1f}%")
        
        if len(complaint_df) > 0:
            print(f"\n抱怨帖子平均点赞数：{complaint_df['score'].mean():.2f}")
            print(f"抱怨帖子平均评论数：{complaint_df['num_comments'].mean():.2f}")
            
            # 抱怨关键词频率
            complaint_kw_counter = Counter()
            for kw_str in complaint_df["complaint_keywords"]:
                if kw_str:
                    for kw in kw_str.split(", "):
                        complaint_kw_counter[kw.strip()] += 1
            
            print(f"\n抱怨关键词频率（Top 10）：")
            for kw, count in complaint_kw_counter.most_common(10):
                print(f"  {kw:20s}: {count:4d} 次")
    
    # 8. 最热门的抱怨帖子
    if "is_complaint" in df.columns and len(df[df["is_complaint"] == True]) > 0:
        print("\n" + "=" * 60)
        print("最热门的抱怨帖子（Top 5，按点赞数）")
        print("=" * 60)
        top_complaints = df[df["is_complaint"] == True].nlargest(5, "score")[
            ["title", "subreddit", "score", "num_comments", "created_date", "complaint_keywords"]
        ]
        for idx, row in top_complaints.iterrows():
            print(f"\n[{row['subreddit']}] {row['title'][:60]}...")
            print(f"  点赞: {row['score']}, 评论: {row['num_comments']}, 日期: {row['created_date']}")
            print(f"  抱怨关键词: {row['complaint_keywords']}")
    
    return df


def save_results(df, posts):
    """保存结果到文件"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 保存完整数据到 CSV
    csv_file = f"reddit_posts_{timestamp}.csv"
    df.to_csv(csv_file, index=False, encoding="utf-8-sig")
    print(f"\n✓ 完整数据已保存到：{csv_file}")
    
    # 保存 JSON 格式（便于后续处理）
    json_file = f"reddit_posts_{timestamp}.json"
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(posts, f, ensure_ascii=False, indent=2, default=str)
    print(f"✓ JSON 数据已保存到：{json_file}")
    
    # 生成简要报告
    report_file = f"reddit_analysis_report_{timestamp}.txt"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write("Reddit 美甲师排单相关帖子分析报告\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"抓取时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"时间范围：{START_DATE.date()} 至 {END_DATE.date()}\n")
        f.write(f"总帖子数：{len(df)}\n\n")
        
        f.write("关键词列表：\n")
        for kw in KEYWORDS:
            f.write(f"  - {kw}\n")
        f.write("\n")
        
        f.write("Subreddits 搜索：\n")
        for sub in SUBREDDITS:
            f.write(f"  - r/{sub}\n")
        f.write("\n")
        
        # 统计摘要
        f.write("统计摘要：\n")
        f.write(f"  平均点赞数：{df['score'].mean():.2f}\n")
        f.write(f"  平均评论数：{df['num_comments'].mean():.2f}\n")
        f.write(f"  总点赞数：{df['score'].sum():.0f}\n")
        f.write(f"  总评论数：{df['num_comments'].sum():.0f}\n")
    
    print(f"✓ 分析报告已保存到：{report_file}")


def main():
    """主函数"""
    print("=" * 60)
    print("Reddit 美甲师排单相关帖子抓取与分析工具")
    print("=" * 60)
    
    # 初始化 Reddit
    reddit = init_reddit()
    if not reddit:
        return
    
    # 抓取帖子（包含评论）
    posts = scrape_posts(reddit, limit_per_sub=200, include_comments=True)
    
    if not posts:
        print("\n未找到匹配的帖子")
        return
    
    # 分析和统计
    df = analyze_and_summarize(posts)
    
    if df is not None:
        # 保存结果
        save_results(df, posts)
        
        print("\n" + "=" * 60)
        print("完成！所有结果已保存到文件")
        print("=" * 60)


if __name__ == "__main__":
    main()
