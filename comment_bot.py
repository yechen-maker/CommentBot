import os
import requests
import time
from random import randint
from bs4 import BeautifulSoup
import json # 【新增】导入 json 库用于处理可能的错误

# ------------------ 配置 ------------------
NUM_REPEATS = 10 # 和你的日志保持一致
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

# 网站 URL 配置
LOGIN_URL = "https://navix.site/login"
COMMENT_ADD_URL = "https://navix.site/comment/add"
COMMENT_DELETE_URL_TEMPLATE = "https://navix.site/comment/delete/{}"
STATUS_URL = "https://navix.site/sign_in"
COMMENT_TEXT = "学习一下"

# ------------------ 核心功能函数 ------------------

def post_and_delete_comment(session, post_id):
    """为一个会话执行一次发表并删除评论的操作"""
    try:
        print("  > 正在发表评论...")
        comment_payload = {"content": COMMENT_TEXT, "postId": post_id}
        
        resp_post = session.post(COMMENT_ADD_URL, json=comment_payload)
        resp_post.raise_for_status()

        # 【重要修改】在这里加入调试代码来捕获错误
        try:
            response_data = resp_post.json()
        except json.JSONDecodeError:
            print("  > [调试信息] 服务器返回的不是有效的JSON。")
            print(f"  > [调试信息] 状态码: {resp_post.status_code}")
            print(f"  > [调试信息] 响应内容: {resp_post.text[:500]}") # 打印前500个字符
            return False # 提前返回，不再继续执行

        comment_id = response_data.get("data", {}).get("id")
        if not comment_id:
            print(f"  > 发表评论后未能获取到 commentId，服务器响应: {response_data}")
            return False

        print(f"  > 评论发表成功, 获得 Comment ID: {comment_id}")
        time.sleep(randint(2, 5))

        delete_url = COMMENT_DELETE_URL_TEMPLATE.format(comment_id)
        print(f"  > 正在删除评论 (URL: {delete_url})...")
        resp_delete = session.post(delete_url)
        resp_delete.raise_for_status()

        if resp_delete.json().get("success"):
            print("  > 评论删除成功。")
            return True
        else:
            print(f"  > 评论删除失败: {resp_delete.text}")
            return False
            
    # 【修改】将通用的 Exception 捕获放在最外层
    except Exception as e:
        print(f"  > 操作出现异常: {e}")
        return False

# (get_account_status 和 main 函数保持不变)
def get_account_status(session):
    try:
        print("  > 正在获取当前币数...")
        resp = session.get(STATUS_URL)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        exp_elem = soup.find(id="expValue")
        if exp_elem:
            return exp_elem.text.strip()
        else:
            return "未能找到币数信息"
    except Exception as e:
        print(f"  > 获取币数时发生错误: {e}")
        return "获取失败"

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
        try:
            resp = session.post(LOGIN_URL, json=login_payload)
            if not (resp.status_code == 200 and resp.json().get("success")):
                print(f"登录失败: {resp.text}")
                continue
            print("登录成功。")
        except Exception as e:
            print(f"登录异常: {e}")
            continue
        success_count = 0
        for i in range(NUM_REPEATS):
            print(f"  第 {i + 1}/{NUM_REPEATS} 次操作...")
            if post_and_delete_comment(session, POST_ID):
                success_count += 1
            if i < NUM_REPEATS - 1:
                time.sleep(randint(5, 10))
        coin_balance = get_account_status(session)
        print(f"--- 账号: {email} 处理完毕，成功 {success_count}/{NUM_REPEATS} 次。当前币数: {coin_balance} ---")

if __name__ == "__main__":
    main()
