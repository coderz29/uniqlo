import requests
import smtplib
import json
import os
import time
from email.mime.text import MIMEText
from email.header import Header
from email.mime.multipart import MIMEMultipart # 👈 需要新增这个导入

# --- 配置区 ---
# 建议在 GitHub Secrets 中设置
EMAIL_SENDER = os.environ.get('EMAIL_SENDER')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD')
EMAIL_RECEIVER = os.environ.get('EMAIL_RECEIVER')
SMTP_SERVER = "smtp.qq.com"  # 如果用Gmail或163请更换地址
DB_FILE = "sent_products.json"

def get_all_uniqlo_data():
    # 定义两个数据源
    urls = {
        "限时特优": "https://www.uniqlo.cn/data/pages/timelimit.html.json",
        "超值精选": "https://www.uniqlo.cn/data/pages/super-u.html.json"
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    all_items = []
    
    for channel_name, url in urls.items():
        try:
            res = requests.get(url, headers=headers, timeout=15)
            data = res.json()
            count = 0
            
            for key, section_val in data.items():
                if key.startswith('section') and isinstance(section_val, dict):
                    # 根据你的截图 image_027641.png，超值精选的结构也是 section -> props -> items
                    props = section_val.get('props', {})
                    raw_list = props.get('items', [])
                    
                    if isinstance(raw_list, list):
                        for row in raw_list:
                            p_code = row.get('productCode')
                            if p_code:
                                # all_items.append({
                                #     "productCode": str(p_code),
                                #     "name": row.get('productName', '优衣库单品'),
                                #     "price": float(row.get('price', 0)),
                                #     "origin": row.get('originPrice', row.get('price')),
                                #     "link": f"https://www.uniqlo.cn/product-detail.html?productCode={p_code}",
                                #     "tag": f"✨{channel_name}"  # 👈 这里区分标签
                                # })
                                # 在 get_all_uniqlo_data 函数的循环内修改
                                all_items.append({
                                    "productCode": str(p_code),
                                    "name": row.get('productName', '优衣库单品'),
                                    "price": float(row.get('price', 0)),
                                    "origin": row.get('originPrice', row.get('price')),
                                    "link": f"https://www.uniqlo.cn/product-detail.html?productCode={p_code}",
                                    "tag": f"✨{channel_name}",
                                    "img": f"https://www.uniqlo.cn{row.get('mainPic', '')}"  # 👈 新增图片链接拼接
                                })
                                count += 1
            print(f"DEBUG: 【{channel_name}】抓取成功，商品数: {count}")
        except Exception as e:
            print(f"DEBUG: 【{channel_name}】解析异常: {e}")
            
    return all_items

def load_history():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def send_email(items, subject_text):
    # 配置服务器信息
    smtp_server = "smtp.163.com"
    smtp_port = 587  # 👈 核心修改：改用 587 端口
    sender = os.environ.get('EMAIL_SENDER')
    password = os.environ.get('EMAIL_PASSWORD')
    receiver = os.environ.get('EMAIL_RECEIVER')

    # 构造文字内容
    content = f"【{subject_text}】\n"
    content += "===========================\n"
    for item in items:
        # 保持分类显示：女装/男装/童装/男女同款
        content += f"▶ {item.get('tag', '✨折扣')} | {item.get('name', '')}\n"
        content += f"   现价：¥{item.get('price')} (原价: ¥{item.get('origin')})\n"
        content += f"   链接：{item.get('link')}\n\n"
    content += "===========================\n"

    msg = MIMEText(content, 'plain', 'utf-8')
    msg['Subject'] = Header(subject_text, 'utf-8')
    msg['From'] = sender
    msg['To'] = receiver

    try:
        # 👈 核心修改：使用 STARTTLS 模式
        server = smtplib.SMTP(smtp_server, smtp_port, timeout=30)
        server.starttls() # 启动安全传输层
        server.login(sender, password)
        server.sendmail(sender, receiver.split(','), msg.as_string())
        server.quit()
        print(f"✅ {subject_text} 发送成功 (端口 587)")
    except Exception as e:
        print(f"❌ 端口 587 发送失败，尝试 465: {e}")
        # 如果 587 还不行，再自动退回到 465 试最后一次
        try:
            server_465 = smtplib.SMTP_SSL(smtp_server, 465, timeout=30)
            server_465.login(sender, password)
            server_465.sendmail(sender, receiver.split(','), msg.as_string())
            server_465.quit()
            print(f"✅ {subject_text} 在 465 端口成功发送")
        except Exception as e2:
            print(f"❌ 所有端口均失效: {e2}")
            raise e2

def main():
    # 1. 获取所有频道数据（限时+超值）
    raw_items = get_all_uniqlo_data()
    history = load_history()
    
    # 2. 定义分类容器
    categories = {}
    
    print(f"DEBUG: 开始对比 {len(raw_items)} 件商品与历史记录")
    
    for item in raw_items:
        p_id = str(item.get('productCode', ''))
        price = float(item.get('price', 0))
        name = item.get('name', '')
        channel_tag = item.get('tag', '✨折扣')
        
        if not p_id: continue

        # 逻辑：如果是新发现的 ID，或者价格降低了
        if p_id not in history or price < history[p_id]:
            # --- 精准识别性别与同款 ---
            assigned_genders = []
            is_child = any(k in name for k in ["童装", "幼儿", "婴儿", "初生儿", "内衣/长裤/其他(童装)"])
            is_woman = "女装" in name
            is_man = "男装" in name
            
            if is_child:
                assigned_genders.append("童装")
            
            # 判断是否为男女同款
            if is_woman and is_man:
                assigned_genders.append("男女同款")
            elif is_woman:
                assigned_genders.append("女装")
            elif is_man:
                assigned_genders.append("男装")
                
            if not assigned_genders:
                assigned_genders.append("其他")
            
            # 将商品放入对应的每一个分类中
            for g_tag in assigned_genders:
                cat_key = f"{channel_tag} - {g_tag}"
                if cat_key not in categories:
                    categories[cat_key] = []
                categories[cat_key].append(item)
            
            history[p_id] = price 

    # 3. 按分类循环发送邮件
    if categories:
        has_sent_any = False
        # 获取所有分类列表并排序，确保发送顺序整齐
        sorted_keys = sorted(categories.keys())
        total_cats = len(sorted_keys)
        
        for index, cat_title in enumerate(sorted_keys):
            items = categories[cat_title]
            print(f">>> 正在推送 ({index+1}/{total_cats}): 【{cat_title}】共 {len(items)} 件")
            
            try:
                subject = f"优衣库折扣提醒 - {cat_title}"
                # 调用你当前的 send_email 函数
                send_email(items, subject) 
                has_sent_any = True
                
                # 💡 关键修复：每发完一类，强制休息 15 秒，彻底规避服务器断开连接
                if index < total_cats - 1:
                    print(f"等待 15 秒后继续推送下一类...")
                    time.sleep(15)
                    
            except Exception as e:
                print(f"❌ 【{cat_title}】推送失败: {e}")
                time.sleep(5) # 失败后也稍微休息

        # 4. 只有发送成功后才同步历史记录
        if has_sent_any:
            with open(DB_FILE, 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=4)
            print("✅ 监控任务完成，历史记录已更新")
    else:
        print("☕ 本次运行未发现价格变动，无需发送邮件。")

if __name__ == "__main__":
    main()