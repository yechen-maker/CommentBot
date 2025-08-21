import os
import requests
import time
from random import randint

# ------------------ 配置 ------------------
# 【在这里修改】每个账号重复操作的次数
NUM_REPEATS = 5

# 【在这里修改】目标帖子的 ID
POST_ID = "7561"

# 账号信息 (自动从 GitHub Secrets 读取)
ACCOUNTS = []
base_email = os.environ.get("NAVIX_EMAIL")
base_password = os.environ.get("NAVIX_PASSWORD")
if base_email and base_password:
    ACCOUNTS.append({"email": base_email, "password": base_password})
i = 2
while True:
    email = os.environ.get(f"NAVIX_EMAIL{i}")
    password = os.environ.get(f"NAVIX_PASSWORD{i}")
    if email and password:
        ACCOUNTS.append({"email": email, "password": password})
        i += 1
    else:
        break

# 网站 URL 配置 (根据你提供的信息填充)
LOGIN_URL = "https://navix.site/login"
COMMENT_ADD_URL = "https://navix.site/comment/add"
COMMENT_DELETE_URL_TEMPLATE = "https://navix.site/comment/delete/{}" # 用于格式化的模板
COMMENT_TEXT = "学习一下"

# ------------------ 核心功能函数 ------------------

def post_and_delete_comment(session, post_id):
    """为一个会话执行一次发表并删除评论的操作"""
    try:
        # 1. 发表评论
        print("  > 正在发表评论...")
        
        # 【重要假设】根据经验推测发表评论的 Payload 结构。
        # 如果此步骤失败，很可能是这里的字段名（如 "content", "postId"）需要调整。
        comment_payload = {
            "content": COMMENT_TEXT,
            "postId": post_id 
        }
        
        resp_post = session.post(COMMENT_ADD_URL, json=comment_payload)
        resp_post.raise_for_status() # 如果请求失败则抛出异常
        response_data = resp_post.json()
        
        # 2. 从发表成功的返回信息中获取 commentId
        # 根据常见的 API 设计，ID 可能在 'data' -> 'id' 中
        comment_id = response_data.get("data", {}).get("id")
        
        if not comment_id:
            print(f"  > 发表评论后未能获取到 commentId，服务器响应: {response_data}")
            return False

        print(f"  > 评论发表成功, 获得 Comment ID: {comment_id}")
        # 随机等待2-5秒，模拟真人操作，避免操作过快
        time.sleep(randint(2, 5)) 

        # 3. 删除评论 (使用获取到的 commentId)
        delete_url = COMMENT_DELETE_URL_TEMPLATE.format(comment_id)
        print(f"  > 正在删除评论 (URL: {delete_url})...")
        
        # 删除操作的 URL 包含了ID，通常不需要再发送 payload
        resp_delete = session.post(delete_url)
        resp_delete.raise_for_status()
        
        # 假设成功的响应里有 "success": true
        if resp_delete.json().get("success"): 
            print("  > 评论删除成功。")
            return True
        else:
            print(f"  > 评论删除失败: {resp_delete.text}")
            return False

    except Exception as e:
        print(f"  > 操作出现异常: {e}")
        return False

# ------------------ 主执行逻辑 ------------------

def main():
    if not ACCOUNTS:
        print("未找到任何账号配置，请检查仓库的 Secrets 设置。")
        return

    for account in ACCOUNTS:
        email = account["email"]
        password = account["password"]
        
        print(f"\n--- 开始处理账号: {email} ---")
        
        session = requests.Session()
        login_payload = {"email": email, "password": password, "rememberMe": False}

        # 登录
        try:
            resp = session.post(LOGIN_URL, json=login_payload)
            if not (resp.status_code == 200 and resp.json().get("success")):
                print(f"登录失败: {resp.text}")
                continue # 登录失败，跳过此账号，处理下一个
            print("登录成功。")
        except Exception as e:
            print(f"登录异常: {e}")
            continue

        # 循环执行发表和删除操作
        success_count = 0
        for i in range(NUM_REPEATS):
            print(f"  第 {i + 1}/{NUM_REPEATS} 次操作...")
            if post_and_delete_comment(session, POST_ID):
                success_count += 1
            # 每次完整操作之间随机停顿一下，防止请求过于频繁
            if i < NUM_REPEATS - 1:
                time.sleep(randint(5, 10)) 

        print(f"--- 账号: {email} 处理完毕，成功 {success_count}/{NUM_REPEATS} 次 ---")

if __name__ == "__main__":
    main()
