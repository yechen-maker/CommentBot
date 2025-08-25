import os
import requests
import time
from random import randint
from bs4 import BeautifulSoup
import json
import smtplib
from email.mime.text import MIMEText
from email.header import Header
from datetime import datetime, timezone, timedelta

# ------------------ 配置 ------------------
NUM_REPEATS = 5000
POST_ID = "9081"

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

# 邮件发送配置
EMAIL_SENDER = os.environ.get("EMAIL_SENDER")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")
EMAIL_RECEIVER = os.environ.get("EMAIL_RECEIVER")

# ------------------ 功能函数 ------------------

def send_email(subject, body):
    if not all([EMAIL_SENDER, EMAIL_PASSWORD, EMAIL_RECEIVER]):
        print("邮件配置不完整，跳过发送邮件。")
        return
        
    msg = MIMEText(body, 'plain', 'utf-8')
    msg['From'] = Header(f"自动化任务 <{EMAIL_SENDER}>", 'utf-8')
    msg['To'] = Header(f"管理员 <{EMAIL_RECEIVER}>", 'utf-8')
    msg['Subject'] = Header(subject, 'utf-8')

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, [EMAIL_RECEIVER], msg.as_string())
        print("日志邮件发送成功")
    except Exception as e:
        print(f"日志邮件发送失败: {e}")

def post_and_delete_comment(session, post_id):
    """为一个会话执行一次发表并删除评论的操作"""
    try:
        print("  > 正在发表评论...")
        comment_payload = {"content": COMMENT_TEXT, "postId": post_id}
        resp_post = session.post(COMMENT_ADD_URL, data=comment_payload)
        resp_post.raise_for_status()
        response_data = resp_post.json()

        comment_id = response_data.get("comment", {}).get("id")
        if not comment_id:
            print(f"  > 发表评论后未能获取到 commentId，服务器响应: {response_data}")
            return False

        print(f"  > 评论发表成功, 获得 Comment ID: {comment_id}")
        # time.sleep(randint(1, 2))

        delete_url = COMMENT_DELETE_URL_TEMPLATE.format(comment_id)
        print(f"  > 正在删除评论 (ID: {comment_id})...")
        resp_delete = session.post(delete_url)
        resp_delete.raise_for_status()

        if resp_delete.json().get("success"):
            print("  > 评论删除成功。")
            return True
        else:
            print(f"  > 评论删除失败: {resp_delete.text}")
            return False
            
    except Exception as e:
        print(f"  > 操作出现异常: {e}")
        return False

def get_account_status(session):
    """获取并返回当前账号的币数"""
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

# ------------------ 主执行逻辑 ------------------

def main():
    # 【修改】创建一个专门用于邮件内容的摘要列表
    email_summary_list = []
    
    beijing_tz = timezone(timedelta(hours=8))
    beijing_time_str = datetime.now(beijing_tz).strftime('%Y-%m-%d %H:%M:%S')
    
    print(f"任务开始时间: {beijing_time_str} (北京时间)")
    email_summary_list.append(f"报告生成时间: {beijing_time_str} (北京时间)\n")

    if not ACCOUNTS:
        print("未找到任何账号配置。")
        email_summary_list.append("错误：未配置任何账号信息。")
    
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
                email_summary_list.append(f"账号: {email} - 状态: 登录失败")
                continue # 处理下一个账号
            print("登录成功。")
        except Exception as e:
            print(f"登录异常: {e}")
            email_summary_list.append(f"账号: {email} - 状态: 登录异常")
            continue
            
        # 执行评论循环，这部分的详细日志只打印在控制台
        for i in range(NUM_REPEATS):
            print(f"  第 {i + 1}/{NUM_REPEATS} 次操作...")
            post_and_delete_comment(session, POST_ID)
            # if i < NUM_REPEATS - 1:
            #     time.sleep(randint(1, 2))
                
        # 获取最终币数用于摘要
        coin_balance = get_account_status(session)
        summary_line = f"账号: {email} - 当前币数: {coin_balance}"
        
        # 打印最终总结并添加到邮件摘要列表
        print(f"--- 账号: {email} 处理完毕。{summary_line} ---")
        email_summary_list.append(summary_line)

    # 【修改】使用摘要列表生成邮件内容并发送
    email_body = "\n".join(email_summary_list)
    send_email("每日币数状态报告", email_body)

if __name__ == "__main__":
    main()
