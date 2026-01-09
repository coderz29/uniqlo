import requests
import smtplib
import json
import os
from email.mime.text import MIMEText
from email.header import Header

# --- 配置区 ---
# 建议在 GitHub Secrets 中设置
EMAIL_SENDER = os.environ.get('EMAIL_SENDER')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD')
EMAIL_RECEIVER = os.environ.get('EMAIL_RECEIVER')
SMTP_SERVER = "smtp.qq.com"  # 如果用Gmail或163请更换地址
DB_FILE = "sent_products.json"

def get_uniqlo_data():
    url = "https://www.uniqlo.cn/data/pages/timelimit.html.json"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        res = requests.get(url, headers=headers, timeout=15)
        data = res.json()
        items = []
        
        # 遍历所有键值对
        for key, section_val in data.items():
            # 关键：只有当 key 以 section 开头，且内容确实是【字典】时才处理
            if key.startswith('section') and isinstance(section_val, dict):
                
                # 按照截图路径：sectionXX -> props -> items
                props = section_val.get('props')
                
                # 再次确保 props 也是字典
                if isinstance(props, dict):
                    raw_list = props.get('items', [])
                    
                    if isinstance(raw_list, list):
                        for row in raw_list:
                            p_code = row.get('productCode')
                            if p_code:
                                items.append({
                                    "productCode": str(p_code),
                                    "name": row.get('productName', '优衣库单品'),
                                    "price": float(row.get('price', 0)),
                                    "origin": row.get('originPrice', row.get('price')),
                                    "link": f"https://www.uniqlo.cn/product-detail.html?productCode={p_code}",
                                    "tag": "🔥限时特优"
                                })
        
        print(f"DEBUG: 接口解析成功，有效商品数: {len(items)}")
        return items
    except Exception as e:
        print(f"DEBUG: 解析异常: {e}")
        return []

def load_history():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def send_email(items):
    # smtp_server = os.environ.get('SMTP_SERVER')
    smtp_server = "smtp.163.com"
    # 强制尝试 465 端口 + SSL
    smtp_port = 465 
    sender = os.environ.get('EMAIL_SENDER')
    password = os.environ.get('EMAIL_PASSWORD') # 必须是 16 位授权码
    receiver = os.environ.get('EMAIL_RECEIVER')
    
    print(f"DEBUG: 正在尝试连接服务器: {smtp_server}")
    # 构造简单的邮件正文
    content = "发现以下优衣库折扣：\n\n"
    for item in items:
        content += f"【{item['tag']}】{item['name']}\n价格：{item['price']} (原价：{item['origin']})\n链接：{item['link']}\n\n"

    msg = MIMEText(content, 'plain', 'utf-8')
    msg['From'] = sender
    msg['To'] = receiver
    msg['Subject'] = Header('优衣库折扣监控提醒', 'utf-8')

    # 【关键修改点】使用 SMTP_SSL 建立连接
    try:
        print(f"DEBUG: 正在连接 {smtp_server}:{smtp_port}...")
        server = smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=20) 
        server.login(sender, password)
        server.sendmail(sender, [receiver], msg.as_string())
        server.quit()
        print("邮件发送成功！")
    except Exception as e:
        print(f"邮件发送失败的具体原因: {e}")
        raise e

def main():
    raw_items = get_uniqlo_data()
    history = load_history()
    to_push = []
    
    print(f"DEBUG: 开始对比 {len(raw_items)} 件商品与历史记录")
    
    for item in raw_items:
        p_id = str(item['productCode'])
        # 注意：这里改用 get_uniqlo_data 函数中定义的键名 'price'
        price = float(item['price'])
        
        # 只要抓取到了，就默认它是折扣商品（因为接口本身就是限时特优）
        # 状态对比：如果是新商品，或者价格比上次推送时更低
        if p_id not in history or price < history[p_id]:
            to_push.append({
                "tag": item.get('tag', '🔥限时特优'),
                "name": item.get('name', '优衣库单品'),
                "price": price,
                "origin": item.get('origin', price),
                "link": item.get('link', f"https://www.uniqlo.cn/product-detail.html?productCode={p_id}")
            })
            history[p_id] = price # 更新记忆

    if to_push:
        # to_push = to_push[:5]  # 👈 临时加这一行，只发前5个，看看能不能成功
        print(f"准备推送 {len(to_push)} 件商品")
        # 尝试发送邮件
        try:
            send_email(to_push)
            # 只有邮件发送成功后，才更新本地历史记录
            with open(DB_FILE, 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=4)
            print("历史记录已更新")
        except Exception as e:
            print(f"邮件发送失败，不更新历史记录，下次将重试: {e}")
    else:
        print("没有新折扣，无需发送。")

if __name__ == "__main__":
    main()