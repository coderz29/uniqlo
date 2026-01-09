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
    """抓取优衣库数据（此处逻辑需根据实际API微调）"""
    # 示例 API 地址（建议通过小程序抓包获得最准确的接口）
    url = "https://d.uniqlo.cn/p/search/render/limited-promotion"
    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148"
    }
    try:
        res = requests.get(url, headers=headers, timeout=15)
        # 假设返回结构中包含商品列表
        items = res.json().get('resp', [{}])[0].get('productList', [])
        return items
    except Exception as e:
        print(f"抓取失败: {e}")
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
    
    for item in raw_items:
        tags = str(item.get('identity_tags', []))
        is_limited = "限时特优" in tags
        is_value = "超值精选" in tags
        
        if is_limited or is_value:
            p_id = str(item['productCode'])
            price = float(item['minPrice'])
            
            # 状态对比：如果是新商品，或者价格比上次推送时更低
            if p_id not in history or price < history[p_id]:
                to_push.append({
                    "tag": "🔥限时特优" if is_limited else "💰超值精选",
                    "name": item['productName'],
                    "price": price,
                    "origin": item['originPrice'],
                    "link": f"https://www.uniqlo.cn/product-detail.html?productCode={p_id}"
                })
                history[p_id] = price # 更新记忆

    if to_push:
        print(f"准备推送 {len(to_push)} 件商品")
        send_email(to_push)
        with open(DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=4)
    else:
        print("没有新折扣，无需发送。")

if __name__ == "__main__":
    main()