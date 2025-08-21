import os
import requests
import time
from random import randint
from bs4 import BeautifulSoup
import json
import smtplib  # 【新增】邮件库
from email.mime.text import MIMEText  # 【新增】邮件库
from email.header import Header  # 【新增】邮件库
from datetime import datetime, timezone, timedelta # 【新增】时间库

# ------------------ 配置 ------------------
NUM_REPEATS = 5
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

# 【新增】邮件发送配置
EMAIL_SENDER = os.environ.get("EMAIL_SENDER")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")
EMAIL_RECEIVER = os.environ.get("EMAIL_RECEIVER")

# ------------------ 功能函数 ------------------

# 【新增】邮件发送函数
def send_email(subject, body):
    if not all([EMAIL_SENDER, EMAIL_PASSWORD, EMAIL_RECEIVER]):
        print("邮件配置不完整，跳过发送邮件。")
        return
        
    msg = MIMEText(body, 'plain', 'utf-8')
    msg['From'] = Header(f"自动化任务 <{EMAIL_SENDER}>", 'utf-8')
    msg['To'] = Header(f"管理员 <{EMAIL_RECEIVER}>", 'utf-8')
    msg['Subject'] = Header(subject, 'utf-8')

    try:
        # 假设使用 Gmail 发送
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, [EMAIL_RECEIVER], msg.as_string())
        print("日志邮件发送成功")
    except Exception as e:
        print(f"日志邮件发送失败: {e}")

def post_and_delete_comment(session, post_id, log_list):
    """为一个会话执行一次发表并删除评论的操作，并将日志存入列表"""
    def log_message(msg):
        print(msg)
        log_list.append(msg)

    try:
        log_message("  > 正在发表评论...")
        comment_payload = {"content": COMMENT_TEXT, "postId": post_id}
        resp_post = session.post(COMMENT_ADD_URL, data=comment_payload)
        resp_post.raise_for_status()
        response_data = resp_post.json()

        comment_id = response_data.get("comment", {}).get("id")
        if not comment_id:
            log_message(f"  > 发表评论后未能获取到 commentId，服务器响应: {response_data}")
            return False

        log_message(f"  > 评论发表成功, 获得 Comment ID: {comment_id}")
        # time.sleep(randint(2, 5))

        delete_url = COMMENT_DELETE_URL_TEMPLATE.format(comment_id)
        log_message(f"  > 正在删除评论 (ID: {comment_id})...")
        resp_delete = session.post(delete_url)
        resp_delete.raise_for_status()

        if resp_delete.json().get("success"):
            log_message("  > 评论删除成功。")
            return True
        else:
            log_message(f"  > 评论删除失败: {resp_delete.text}")
            return False
            
    except Exception as e:
        log_message(f"  > 操作出现异常: {e}")
        return False

def get_account_status(session, log_list):
    """获取并返回当前账号的币数"""
    def log_message(msg):
        print(msg)
        # 状态获取日志可以不加入邮件
    
    try:
        log_message("  > 正在获取当前币数...")
        resp = session.get(STATUS_URL)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        exp_elem = soup.find(id="expValue")
        if exp_elem:
            return exp_elem.text.strip()
        else:
            return "未能找到币数信息"
    except Exception as e:
        log_message(f"  > 获取币数时发生错误: {e}")
        return "获取失败"

# ------------------ 主执行逻辑 ------------------

def main():
    # 【修改】创建一个列表来收集所有日志
    full_log_list = []
    
    # 获取北京时间
    beijing_tz = timezone(timedelta(hours=8))
    beijing_time_str = datetime.now(beijing_tz).strftime('%Y-%m-%d %H:%M:%S')
    
    log_header = f"任务开始时间: {beijing_time_str} (北京时间)"
    print(log_header)
    full_log_list.append(log_header)

    if not ACCOUNTS:
        msg = "未找到任何账号配置，请检查仓库的 Secrets 设置。"
        print(msg)
        full_log_list.append(msg)
    
    for account in ACCOUNTS:
        email = account["email"]
        password = account["password"]
        
        account_header = f"\n--- 开始处理账号: {email} ---"
        print(account_header)
        full_log_list.append(account_header)
        
        session = requests.Session()
        login_payload = {"email": email, "password": password, "rememberMe": False}
        
        try:
            resp = session.post(LOGIN_URL, json=login_payload)
            if not (resp.status_code == 200 and resp.json().get("success")):
                msg = f"登录失败: {resp.text}"
                print(msg)
                full_log_list.append(msg)
                continue
            
            msg = "登录成功。"
            print(msg)
            full_log_list.append(msg)

        except Exception as e:
            msg = f"登录异常: {e}"
            print(msg)
            full_log_list.append(msg)
            continue
            
        success_count = 0
        for i in range(NUM_REPEATS):
            op_header = f"  第 {i + 1}/{NUM_REPEATS} 次操作..."
            print(op_header)
            full_log_list.append(op_header)
            
            if post_and_delete_comment(session, POST_ID, full_log_list):
                success_count += 1
            if i < NUM_REPEATS - 1:
                time.sleep(randint(5, 10))
                
        coin_balance = get_account_status(session, full_log_list)
        
        summary_msg = f"--- 账号: {email} 处理完毕，成功 {success_count}/{NUM_REPEATS} 次。当前币数: {coin_balance} ---"
        print(summary_msg)
        full_log_list.append(summary_msg)

    # 【修改】在所有任务结束后，发送包含日志的邮件
    final_log_str = "\n".join(full_log_list)
    send_email("每日自动评论任务报告", final_log_str)

if __name__ == "__main__":
    main()
