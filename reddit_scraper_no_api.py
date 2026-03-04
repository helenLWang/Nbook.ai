"""
Reddit 爬虫：无需 API Key 版本
直接使用 Reddit 的公开 JSON 接口抓取数据
时间范围：2023-2026年
关键词：reschedule, communication, cancel, no time 等
"""

import requests
import pandas as pd
from datetime import datetime, timezone
import json
from collections import Counter
import time
import random

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

# 抱怨相关关键词
COMPLAINT_KEYWORDS = [
    "frustrated", "frustrating", "annoying", "annoyed",
    "problem", "issue", "difficult", "hard",
    "hate", "complaint", "complain",
    "mess", "chaos", "confusion",
    "late", "delay", "missed",
    "forgot", "forget", "mistake",
    "wrong", "error", "failed",
]

# 要搜索的 subreddit
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

# User-Agent（模拟浏览器）
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
]


def get_random_headers():
    """获取随机请求头"""
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.9",
    }


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


def fetch_subreddit_posts(subreddit_name, limit=100, sort="relevance", time_filter="all"):
    """
    从 subreddit 抓取帖子（使用 Reddit JSON API，无需认证）
    
    :param subreddit_name: subreddit 名称
    :param limit: 获取数量
    :param sort: 排序方式 (relevance, hot, new, top, comments)
    :param time_filter: 时间过滤 (all, year, month, week, day, hour)
    """
    all_posts = []
    after = None
    fetched = 0
    
    while fetched < limit:
        # 构建 URL
        if sort == "relevance":
            # 搜索功能需要关键词，这里先获取热门帖子
            url = f"https://www.reddit.com/r/{subreddit_name}/hot.json"
        elif sort == "new":
            url = f"https://www.reddit.com/r/{subreddit_name}/new.json"
        elif sort == "top":
            url = f"https://www.reddit.com/r/{subreddit_name}/top.json?t={time_filter}"
        else:
            url = f"https://www.reddit.com/r/{subreddit_name}/hot.json"
        
        if after:
            url += f"?after={after}"
        
        try:
            response = requests.get(url, headers=get_random_headers(), timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if "data" not in data or "children" not in data["data"]:
                break
            
            posts = data["data"]["children"]
            if not posts:
                break
            
            for post_data in posts:
                if fetched >= limit:
                    break
                
                post = post_data["data"]
                post_date = datetime.fromtimestamp(post["created_utc"], tz=timezone.utc)
                
                # 检查时间范围
                if not is_in_date_range(post_date):
                    continue
                
                title = post.get("title", "")
                selftext = post.get("selftext", "")
                combined_text = f"{title} {selftext}"
                
                # 检查是否包含关键词
                if contains_keywords(combined_text, KEYWORDS):
                    keywords_found = extract_keywords_found(combined_text, KEYWORDS)
                    is_complaint = contains_keywords(combined_text, COMPLAINT_KEYWORDS)
                    complaint_keywords_found = extract_keywords_found(combined_text, COMPLAINT_KEYWORDS) if is_complaint else []
                    
                    all_posts.append({
                        "subreddit": subreddit_name,
                        "keywords_found": ", ".join(keywords_found),
                        "is_complaint": is_complaint,
                        "complaint_keywords": ", ".join(complaint_keywords_found) if complaint_keywords_found else "",
                        "post_id": post["id"],
                        "title": title,
                        "selftext": selftext[:500] if selftext else "",
                        "score": post.get("score", 0),
                        "num_comments": post.get("num_comments", 0),
                        "created_utc": post_date,
                        "created_date": post_date.date(),
                        "url": post.get("url", ""),
                        "permalink": f"https://www.reddit.com{post.get('permalink', '')}",
                        "author": post.get("author", "[deleted]"),
                        "upvote_ratio": post.get("upvote_ratio", 0),
                    })
                    fetched += 1
            
            # 获取下一页的标识
            after = data["data"].get("after")
            if not after:
                break
            
            # 避免请求过快
            time.sleep(random.uniform(1, 3))
        
        except requests.exceptions.RequestException as e:
            print(f"  请求 r/{subreddit_name} 时出错：{e}")
            break
        except Exception as e:
            print(f"  处理 r/{subreddit_name} 时出错：{e}")
            break
    
    return all_posts


def search_subreddit(subreddit_name, keyword, limit=100):
    """
    在 subreddit 中搜索关键词（使用 Reddit 搜索 API）
    """
    all_posts = []
    after = None
    fetched = 0
    
    while fetched < limit:
        url = f"https://www.reddit.com/r/{subreddit_name}/search.json"
        params = {
            "q": keyword,
            "restrict_sr": "true",
            "sort": "relevance",
            "limit": min(100, limit - fetched),
        }
        
        if after:
            params["after"] = after
        
        try:
            response = requests.get(url, headers=get_random_headers(), params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if "data" not in data or "children" not in data["data"]:
                break
            
            posts = data["data"]["children"]
            if not posts:
                break
            
            for post_data in posts:
                if fetched >= limit:
                    break
                
                post = post_data["data"]
                post_date = datetime.fromtimestamp(post["created_utc"], tz=timezone.utc)
                
                # 检查时间范围
                if not is_in_date_range(post_date):
                    continue
                
                title = post.get("title", "")
                selftext = post.get("selftext", "")
                combined_text = f"{title} {selftext}"
                
                # 检查是否包含关键词
                if contains_keywords(combined_text, KEYWORDS):
                    keywords_found = extract_keywords_found(combined_text, KEYWORDS)
                    is_complaint = contains_keywords(combined_text, COMPLAINT_KEYWORDS)
                    complaint_keywords_found = extract_keywords_found(combined_text, COMPLAINT_KEYWORDS) if is_complaint else []
                    
                    all_posts.append({
                        "subreddit": subreddit_name,
                        "keyword_searched": keyword,
                        "keywords_found": ", ".join(keywords_found),
                        "is_complaint": is_complaint,
                        "complaint_keywords": ", ".join(complaint_keywords_found) if complaint_keywords_found else "",
                        "post_id": post["id"],
                        "title": title,
                        "selftext": selftext[:500] if selftext else "",
                        "score": post.get("score", 0),
                        "num_comments": post.get("num_comments", 0),
                        "created_utc": post_date,
                        "created_date": post_date.date(),
                        "url": post.get("url", ""),
                        "permalink": f"https://www.reddit.com{post.get('permalink', '')}",
                        "author": post.get("author", "[deleted]"),
                        "upvote_ratio": post.get("upvote_ratio", 0),
                    })
                    fetched += 1
            
            after = data["data"].get("after")
            if not after:
                break
            
            time.sleep(random.uniform(1, 3))
        
        except requests.exceptions.RequestException as e:
            print(f"  搜索 r/{subreddit_name} 关键词 '{keyword}' 时出错：{e}")
            break
        except Exception as e:
            print(f"  处理 r/{subreddit_name} 关键词 '{keyword}' 时出错：{e}")
            break
    
    return all_posts


def scrape_posts(limit_per_sub=200):
    """抓取帖子（无需 API Key）"""
    all_posts = []
    
    print(f"\n开始抓取数据（无需 API Key）...")
    print(f"时间范围：{START_DATE.date()} 至 {END_DATE.date()}")
    print(f"关键词：{', '.join(KEYWORDS[:5])}... (共 {len(KEYWORDS)} 个)")
    print(f"抱怨关键词：{', '.join(COMPLAINT_KEYWORDS[:5])}... (共 {len(COMPLAINT_KEYWORDS)} 个)")
    print(f"Subreddits：{', '.join(SUBREDDITS)}")
    print("-" * 60)
    
    for subreddit_name in SUBREDDITS:
        print(f"\n正在搜索 r/{subreddit_name}...")
        
        # 对每个关键词进行搜索
        for keyword in KEYWORDS:
            try:
                print(f"  搜索关键词 '{keyword}'...", end="\r")
                posts = search_subreddit(subreddit_name, keyword, limit=limit_per_sub)
                
                if posts:
                    all_posts.extend(posts)
                    print(f"  关键词 '{keyword}': 找到 {len(posts)} 条")
                else:
                    print(f"  关键词 '{keyword}': 未找到匹配帖子")
            
            except Exception as e:
                print(f"  搜索关键词 '{keyword}' 时出错：{e}")
                continue
        
        print(f"  r/{subreddit_name} 总计：{len([p for p in all_posts if p['subreddit'] == subreddit_name])} 条")
    
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
    
    df = pd.DataFrame(posts)
    
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
    
    # 4. 最热门的帖子
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
    
    # 5. 抱怨相关统计
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
    
    return df


def save_results(df, posts):
    """保存结果到文件"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 保存完整数据到 CSV
    csv_file = f"reddit_posts_no_api_{timestamp}.csv"
    df.to_csv(csv_file, index=False, encoding="utf-8-sig")
    print(f"\n✓ 完整数据已保存到：{csv_file}")
    
    # 保存 JSON 格式
    json_file = f"reddit_posts_no_api_{timestamp}.json"
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(posts, f, ensure_ascii=False, indent=2, default=str)
    print(f"✓ JSON 数据已保存到：{json_file}")
    
    # 生成简要报告
    report_file = f"reddit_analysis_report_no_api_{timestamp}.txt"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write("Reddit 美甲师排单相关帖子分析报告（无需 API Key）\n")
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
    print("Reddit 美甲师排单相关帖子抓取与分析工具（无需 API Key）")
    print("=" * 60)
    
    # 抓取帖子
    posts = scrape_posts(limit_per_sub=100)
    
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
