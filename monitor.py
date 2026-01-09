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

# def get_uniqlo_data():
#     url = "https://www.uniqlo.cn/data/pages/timelimit.html.json"
#     headers = {
#         "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
#     }
#     try:
#         res = requests.get(url, headers=headers, timeout=15)
#         data = res.json()
#         items = []
        
#         # 遍历所有键值对
#         for key, section_val in data.items():
#             # 关键：只有当 key 以 section 开头，且内容确实是【字典】时才处理
#             if key.startswith('section') and isinstance(section_val, dict):
                
#                 # 按照截图路径：sectionXX -> props -> items
#                 props = section_val.get('props')
                
#                 # 再次确保 props 也是字典
#                 if isinstance(props, dict):
#                     raw_list = props.get('items', [])
                    
#                     if isinstance(raw_list, list):
#                         for row in raw_list:
#                             p_code = row.get('productCode')
#                             if p_code:
#                                 items.append({
#                                     "productCode": str(p_code),
#                                     "name": row.get('productName', '优衣库单品'),
#                                     "price": float(row.get('price', 0)),
#                                     "origin": row.get('originPrice', row.get('price')),
#                                     "link": f"https://www.uniqlo.cn/product-detail.html?productCode={p_code}",
#                                     "tag": "🔥限时特优"
#                                 })
        
#         print(f"DEBUG: 接口解析成功，有效商品数: {len(items)}")
#         return items
#     except Exception as e:
#         print(f"DEBUG: 解析异常: {e}")
#         return []
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
                                all_items.append({
                                    "productCode": str(p_code),
                                    "name": row.get('productName', '优衣库单品'),
                                    "price": float(row.get('price', 0)),
                                    "origin": row.get('originPrice', row.get('price')),
                                    "link": f"https://www.uniqlo.cn/product-detail.html?productCode={p_code}",
                                    "tag": f"✨{channel_name}"  # 👈 这里区分标签
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

def send_email(items, subject_text="优衣库折扣监控提醒"):
    """
    修正版发送函数：
    1. 支持两个参数，解决 'takes 1 positional argument but 2 were given' 报错。
    2. 硬编码 SMTP 服务器为 smtp.qq.com，解决 'None:465' 连接失败问题。
    3. 动态设置邮件标题。
    """
    # 配置信息
    smtp_server = "smtp.163.com"  # 确保这里是字符串
    smtp_port = 465
    sender = os.environ.get('EMAIL_SENDER')
    password = os.environ.get('EMAIL_PASSWORD')
    receiver = os.environ.get('EMAIL_RECEIVER')

    print(f"DEBUG: 正在尝试连接服务器: {smtp_server}:{smtp_port}")

    # 1. 构造邮件正文
    content = f"为您发现以下优衣库【{subject_text}】相关折扣单品：\n\n"
    for item in items:
        content += f"---------------------------\n"
        content += f"【{item.get('tag', '限时特优')}】{item.get('name')}\n"
        content += f"当前价格：¥{item.get('price')} (原价：¥{item.get('origin')})\n"
        content += f"直达链接：{item.get('link')}\n\n"

    # 2. 构造邮件对象
    msg = MIMEText(content, 'plain', 'utf-8')
    msg['From'] = sender
    msg['To'] = receiver
    # 关键：这里使用传入的参数 subject_text
    msg['Subject'] = Header(subject_text, 'utf-8')

    # 3. 执行发送
    try:
        # 使用 SSL 建立安全连接
        server = smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=20)
        server.login(sender, password)
        server.sendmail(sender, [receiver], msg.as_string())
        server.quit()
        print(f"✅ 邮件【{subject_text}】发送成功！")
    except Exception as e:
        print(f"❌ 邮件【{subject_text}】发送失败: {e}")
        # 抛出异常让 main 函数知道，从而不更新 history 文件
        raise e

# def main():
#     raw_items = get_uniqlo_data()
#     history = load_history()
    
#     # 1. 定义分类容器，确保所有商品都有归属
#     categories = {
#         "女装": [],
#         "男装": [],
#         "童装": []
#     }
    
#     print(f"DEBUG: 开始对比 {len(raw_items)} 件商品与历史记录")
    
#     for item in raw_items:
#         p_id = str(item['productCode'])
#         price = float(item['price'])
#         name = item.get('name', '')
        
#         # 状态对比：如果是新商品，或者价格比上次推送时更低
#         if p_id not in history or price < history[p_id]:
#             product_data = {
#                 "tag": item.get('tag', '🔥限时特优'),
#                 "name": name,
#                 "price": price,
#                 "origin": item.get('origin', price),
#                 "link": item.get('link', f"https://www.uniqlo.cn/product-detail.html?productCode={p_id}")
#             }
            
#             # 2. 根据名称自动分类（优衣库名称通常自带分类标签）
#             if "童装" in name or "幼儿" in name or "婴儿" in name:
#                 categories["童装"].append(product_data)
#             elif "女装" in name:
#                 categories["女装"].append(product_data)
#             elif "男装" in name:
#                 categories["男装"].append(product_data)
#             else:
#                 # 无法识别的暂时放入男装分类
#                 categories["男装"].append(product_data)
                
#             history[p_id] = price # 更新本地记忆

#     # 3. 分类别发送邮件（对应你之前看到的错误，这里现在传两个参数）
#     has_sent_any = False
#     for cat_name, items in categories.items():
#         if items:
#             print(f"准备推送【{cat_name}】共 {len(items)} 件商品")
#             try:
#                 # 构造分类标题，例如：优衣库折扣提醒 - 女装
#                 subject = f"优衣库折扣提醒 - {cat_name}"
#                 # 调用你刚才修改好的支持两个参数的 send_email
#                 send_email(items, subject) 
#                 has_sent_any = True
#             except Exception as e:
#                 print(f"【{cat_name}】邮件发送失败: {e}")

#     # 4. 只要有任何一封邮件发成功了，就更新历史记录防止重复
#     if has_sent_any:
#         with open(DB_FILE, 'w', encoding='utf-8') as f:
#             json.dump(history, f, ensure_ascii=False, indent=4)
#         print("✅ 历史记录已更新")
#     else:
#         print("没有新折扣，无需发送。")
def main():
    # 1. 调用支持多频道抓取的函数 (获取限时特优+超值精选)
    raw_items = get_all_uniqlo_data()
    history = load_history()
    
    # 2. 定义分类容器：按“频道-性别”动态分类
    # 结果会像这样：categories["✨限时特优 - 女装"] = [...]
    categories = {}
    
    print(f"DEBUG: 开始对比 {len(raw_items)} 件商品与历史记录")
    
    for item in raw_items:
        p_id = str(item['productCode'])
        price = float(item['price'])
        name = item.get('name', '')
        channel_tag = item.get('tag', '✨折扣单品') # 区分是限时特优还是超值精选
        
        # 状态对比：如果是新商品，或者价格比上次推送时更低
        if p_id not in history or price < history[p_id]:
            # 自动识别性别
            gender = "其他"
            if "童装" in name or "幼儿" in name or "婴儿" in name:
                gender = "童装"
            elif "女装" in name:
                gender = "女装"
            elif "男装" in name:
                gender = "男装"
            
            # 构造唯一的分类 Key
            cat_key = f"{channel_tag} - {gender}"
            
            if cat_key not in categories:
                categories[cat_key] = []
            
            categories[cat_key].append(item)
            history[p_id] = price # 更新本地记忆

    # 3. 分类别发送邮件
    has_sent_any = False
    for cat_title, items in categories.items():
        if items:
            print(f"准备推送【{cat_title}】共 {len(items)} 件商品")
            try:
                # 邮件标题会自动变为：优衣库折扣提醒 - ✨限时特优 - 女装
                subject = f"优衣库折扣提醒 - {cat_title}"
                # 确保你的 send_email 已经改成了支持两个参数的版本
                send_email(items, subject) 
                has_sent_any = True
            except Exception as e:
                print(f"【{cat_title}】邮件发送失败: {e}")

    # 4. 只要有任何一封邮件发成功了，就更新历史记录
    if has_sent_any:
        with open(DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=4)
        print("✅ 历史记录已更新")
    else:
        print("没有新折扣，无需发送。")

if __name__ == "__main__":
    main()