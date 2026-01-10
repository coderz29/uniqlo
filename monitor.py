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

# def send_email(items, subject_text="优衣库折扣监控提醒"):
#     """
#     修正版发送函数：
#     1. 支持两个参数，解决 'takes 1 positional argument but 2 were given' 报错。
#     2. 硬编码 SMTP 服务器为 smtp.qq.com，解决 'None:465' 连接失败问题。
#     3. 动态设置邮件标题。
#     """
#     # 配置信息
#     smtp_server = "smtp.163.com"  # 确保这里是字符串
#     smtp_port = 465
#     sender = os.environ.get('EMAIL_SENDER')
#     password = os.environ.get('EMAIL_PASSWORD')
#     receiver = os.environ.get('EMAIL_RECEIVER')

#     print(f"DEBUG: 正在尝试连接服务器: {smtp_server}:{smtp_port}")

#     # 1. 构造邮件正文
#     content = f"为您发现以下优衣库【{subject_text}】相关折扣单品：\n\n"
#     for item in items:
#         content += f"---------------------------\n"
#         content += f"【{item.get('tag', '限时特优')}】{item.get('name')}\n"
#         content += f"当前价格：¥{item.get('price')} (原价：¥{item.get('origin')})\n"
#         content += f"直达链接：{item.get('link')}\n\n"

#     # 2. 构造邮件对象
#     msg = MIMEText(content, 'plain', 'utf-8')
#     msg['From'] = sender
#     msg['To'] = receiver
#     # 关键：这里使用传入的参数 subject_text
#     msg['Subject'] = Header(subject_text, 'utf-8')

#     # 3. 执行发送
#     try:
#         # 使用 SSL 建立安全连接
#         server = smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=20)
#         server.login(sender, password)
#         server.sendmail(sender, [receiver], msg.as_string())
#         server.quit()
#         print(f"✅ 邮件【{subject_text}】发送成功！")
#     except Exception as e:
#         print(f"❌ 邮件【{subject_text}】发送失败: {e}")
#         # 抛出异常让 main 函数知道，从而不更新 history 文件
#         raise e
def send_email(items, subject_text="优衣库折扣监控提醒"):
    smtp_server = "smtp.qq.com" 
    smtp_port = 465
    sender = os.environ.get('EMAIL_SENDER')
    password = os.environ.get('EMAIL_PASSWORD')
    receiver = os.environ.get('EMAIL_RECEIVER')

    # 1. 构造 HTML 格式的正文
    html_content = f"""
    <html>
    <body>
        <h2 style="color: #ff4444;">{subject_text}</h2>
        <p>为您发现以下优衣库特惠单品：</p>
        <table border="0" cellpadding="10" cellspacing="0" style="width: 100%; max-width: 600px;">
    """
    
    for item in items:
        html_content += f"""
        <tr style="border-bottom: 1px solid #eee;">
            <td style="width: 120px;">
                <img src="{item['img']}" width="100" style="border-radius: 5px;">
            </td>
            <td>
                <b style="font-size: 16px;">【{item['tag']}】{item['name']}</b><br>
                <span style="color: red; font-size: 18px;">现价：¥{item['price']}</span> 
                <del style="color: #999;">原价：¥{item['origin']}</del><br><br>
                <a href="{item['link']}" style="background: #ff4444; color: white; padding: 5px 10px; text-decoration: none; border-radius: 3px;">立即前往购买</a>
            </td>
        </tr>
        """
    
    html_content += "</table></body></html>"

    try:
        # 每次发送都重新创建对象，确保连接新鲜
        server = smtplib.SMTP_SSL("smtp.qq.com", 465, timeout=30) # 增加超时时间到 30s
        server.login(sender, password)
        server.sendmail(sender, receiver.split(','), msg.as_string())
        server.quit() 
        print(f"✅ 【{subject_text}】已成功送达")
    except Exception as e:
        # 如果是连接被关闭，打印更详细的提示
        print(f"连接异常详情: {e}")
        raise e

    # 2. 构造邮件对象（注意这里改用 MIMEMultipart）
    msg = MIMEMultipart()
    msg['From'] = sender
    msg['To'] = receiver
    msg['Subject'] = Header(subject_text, 'utf-8')
    
    # 将 HTML 内容附加到邮件中
    msg.attach(MIMEText(html_content, 'html', 'utf-8'))

    # 3. 发送
    try:
        server = smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=20)
        server.login(sender, password)
        server.sendmail(sender, receiver.split(','), msg.as_string())
        server.quit()
        print(f"✅ 邮件【{subject_text}】(含图片)发送成功！")
    except Exception as e:
        print(f"❌ 发送失败: {e}")
        raise e

# def main():
#     # 1. 获取所有数据（自动包含限时和超值两个频道）
#     raw_items = get_all_uniqlo_data()
#     history = load_history()
    
#     categories = {}
    
#     for item in raw_items:
#         p_id = str(item.get('productCode'))
#         name = item.get('name', '')
#         channel_tag = item.get('tag', '✨折扣') # 这里的 tag 会是 ✨限时特优 或 ✨超值精选
        
#         # 检查是否需要推送
#         if p_id not in history or float(item['price']) < history[p_id]:
            
#             # --- 识别性别（多重判定逻辑） ---
#             is_woman = "女装" in name
#             is_man = "男装" in name
#             is_child = any(k in name for k in ["童装", "幼儿", "婴儿", "初生儿"])
            
#             gender_tags = []
#             if is_child:
#                 gender_tags.append("童装")
            
#             # 核心修改：如果同时包含男和女，强制分入“男女同款”
#             if is_woman and is_man:
#                 gender_tags.append("男女同款")
#             else:
#                 if is_woman: gender_tags.append("女装")
#                 if is_man: gender_tags.append("男装")
            
#             if not gender_tags:
#                 gender_tags.append("其他")
            
#             # --- 按照 (频道 + 性别) 进行归类 ---
#             for g_tag in gender_tags:
#                 # 这样生成的标题会是：✨限时特优 - 男女同款
#                 cat_key = f"{channel_tag} - {g_tag}"
#                 if cat_key not in categories:
#                     categories[cat_key] = []
#                 categories[cat_key].append(item)
            
#             history[p_id] = float(item['price'])

#     # 3. 发送邮件逻辑
#     # 分类别发送邮件
#     has_sent_any = False
#     for cat_title, items in categories.items():
#         if items:
#             print(f">>> 正在推送分类：【{cat_title}】...")
#             try:
#                 subject = f"优衣库折扣提醒 - {cat_title}"
#                 send_email(items, subject) 
#                 has_sent_any = True
                
#                 # --- 💡 必须加在这里！每成功发送一类，强制休息 10 秒 ---
#                 print(f"防止频率过快，强制等待 10 秒...")
#                 time.sleep(10) 
#                 # -----------------------------------------------
                
#             except Exception as e:
#                 print(f"❌ 【{cat_title}】推送中途失败: {e}")
#                 # 如果失败了，也建议休息一下再试下一个分类
#                 time.sleep(5)

#     if has_sent_any:
#         with open(DB_FILE, 'w', encoding='utf-8') as f:
#             json.dump(history, f, ensure_ascii=False, indent=4)
#         print("✅ 监控完成，历史记录已更新")
#     else:
#         print("☕ 没有新折扣。")
def main():
    raw_items = get_all_uniqlo_data()
    history = load_history()
    new_discounts = []
    
    print(f"DEBUG: 开始对比 {len(raw_items)} 件商品")
    for item in raw_items:
        p_id = str(item.get('productCode'))
        price = float(item.get('price', 0))
        if p_id not in history or price < history[p_id]:
            new_discounts.append(item)
            history[p_id] = price 

    if new_discounts:
        # 1. 排序：按频道和性别排序，让内容更有序
        new_discounts.sort(key=lambda x: (x.get('tag', ''), x.get('name', '')))
        
        # 2. 分页逻辑：每 50 个商品分成一组
        chunk_size = 50
        chunks = [new_discounts[i:i + chunk_size] for i in range(0, len(new_discounts), chunk_size)]
        
        total_chunks = len(chunks)
        print(f"🚀 发现 {len(new_discounts)} 件新折扣，将分 {total_chunks} 封邮件发出...")
        
        has_sent_any = False
        for index, chunk in enumerate(chunks):
            try:
                # 标题加上序号，方便识别
                subject = f"优衣库折扣快报 ({index+1}/{total_chunks}) - 发现 {len(chunk)} 件单品"
                send_email(chunk, subject) 
                has_sent_any = True
                
                # 3. 每发完一小包，休息 10 秒，非常重要！
                if index < total_chunks - 1:
                    print(f"已发送第 {index+1} 份，休息 10 秒防止封禁...")
                    time.sleep(10)
            except Exception as e:
                print(f"❌ 第 {index+1} 封邮件发送失败: {e}")

        if has_sent_any:
            with open(DB_FILE, 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=4)
            print("✅ 历史记录同步完成")
    else:
        print("☕ 没有发现新价格变动。")

if __name__ == "__main__":
    main()