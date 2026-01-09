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
    if not items: return
    
    # 构建 HTML 内容
    rows = ""
    for item in items:
        rows += f"""
        <tr>
            <td style="padding:10px; border-bottom:1px solid #ddd;"><b>{item['tag']}</b></td>
            <td style="padding:10px; border-bottom:1px solid #ddd;">{item['name']}</td>
            <td style="padding:10px; border-bottom:1px solid #ddd; color:red;">¥{item['price']} (原价¥{item['origin']})</td>
            <td style="padding:10px; border-bottom:1px solid #ddd;"><a href="{item['link']}">立即查看</a></td>
        </tr>"""
    
    html = f"<h3>优衣库折扣监控日报</h3><table border='1' style='border-collapse:collapse;'>{rows}</table>"
    msg = MIMEText(html, 'html', 'utf-8')
    msg['From'] = EMAIL_SENDER
    msg['To'] = EMAIL_RECEIVER
    msg['Subject'] = Header(f"🔥 发现 {len(items)} 件优衣库新折扣！", 'utf-8')

    server = smtplib.SMTP_SSL(SMTP_SERVER, 465)
    server.login(EMAIL_SENDER, EMAIL_PASSWORD)
    server.sendmail(EMAIL_SENDER, [EMAIL_RECEIVER], msg.as_string())
    server.quit()

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