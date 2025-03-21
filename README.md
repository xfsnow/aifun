做一个简单的手机工具程序，用来记录日常消费和收入。想要的功能是
在手机上把收支的截图发到服务端程序
服务端程序收到截图后智能识别出支出的地所、支付平台、费用、时间，最后统一保存起来。
不用微信小程序，直接用Python做一个简单的HTML页面，用于图片上传，整合到Python的服务端程序中，用浏览器打开，首次打开是一个供上传图片的HTML页，图片上传后显示解析出的收支内容，每栏都可以修改，确认无误后，点击确认，最后再保存到数据库中。



# 移动端消费记录系统开发方案

## 系统架构

```
手机浏览器 → 访问HTML页面 → Flask服务端 → Azure OpenAI 识别 → SQLite数据库
          (上传/编辑页面)       (路由处理)      (文本解析)      (数据持久化)


```

## 技术选型
| 模块         | 技术方案                                                                 | 版本要求          |
|--------------|--------------------------------------------------------------------------|-------------------|
| 服务端框架   | Flask                                                                   | 2.0+             |
| OCR识别     | Azure OpenAI                                                              | Python SDK 4.16+ |
| 前端界面     | HTML5 + VanillaJS                                                        | -                |
| 数据库       | SQLite                                                                  | 3.30+            |

## 实现步骤

### 服务端搭建
```mysql
CREATE TABLE IF NOT EXISTS `accounting` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `transaction_time` DATETIME NOT NULL,
  `income_amount` DECIMAL(10,2),
  `expense_amount` DECIMAL(10,2),
  `transaction_app` VARCHAR(50),
  `payment_platform` VARCHAR(50),
  `financial_terminal` VARCHAR(50),
  `memo` TEXT,
  `category` VARCHAR(50)
);
```

1. 服务端搭建（app.py）
```python
from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import os
from datetime import datetime


app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'

# Azure OpenAI GPT-4o配置




def init_db():
    conn = sqlite3.connect('finance.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS transactions
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  platform VARCHAR(50),
                  amount DECIMAL(10,2),
                  time DATETIME,
                  location TEXT,
                  note TEXT)''')
    conn.commit()
    conn.close()

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # 处理图片上传
        file = request.files['receipt']
        if file:
            filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            # OCR识别
            with open(filepath, 'rb') as f:
                image = f.read()
            result = ocr_client.basicGeneral(image)
            text_data = '\n'.join([item['words'] for item in result['words_result']])

            # 解析关键信息（示例解析逻辑）
            parsed_data = {
                'platform': '微信支付' if '微信支付' in text_data else '支付宝',
                'amount': extract_amount(text_data),
                'time': extract_time(text_data),
                'location': extract_location(text_data),
                'note': ''
            }
            return render_template('edit.html',
                                 data=parsed_data,
                                 image_url=filename)

    return render_template('upload.html')

@app.route('/save', methods=['POST'])
def save_record():
    record = {
        'platform': request.form.get('platform'),
        'amount': float(request.form.get('amount')),
        'time': datetime.strptime(request.form.get('time'), '%Y-%m-%d %H:%M:%S'),
        'location': request.form.get('location'),
        'note': request.form.get('note')
    }

    conn = sqlite3.connect('finance.db')
    c = conn.cursor()
    c.execute('''INSERT INTO transactions
                 (platform, amount, time, location, note)
                 VALUES (?,?,?,?,?)''',
              (record['platform'], record['amount'],
               record['time'], record['location'], record['note']))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)
```

2. 前端页面（templates/upload.html）

```html
<!DOCTYPE html>
<html>
<head>
    <title>消费记录上传</title>
    <style>
        .container { max-width: 600px; margin: 20px auto; padding: 20px; }
        .upload-box { border: 2px dashed #ccc; padding: 30px; text-align: center; }
        #preview { max-width: 100%; margin-top: 20px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>上传消费凭证</h1>
        <form method="post" enctype="multipart/form-data">
            <div class="upload-box">
                <input type="file" name="receipt" accept="image/*"
                       onchange="previewImage(this)">
                <img id="preview" src="#" alt="图片预览">
            </div>
            <button type="submit">开始识别</button>
        </form>
    </div>

    <script>
        function previewImage(input) {
            const preview = document.getElementById('preview');
            const file = input.files[0];
            const reader = new FileReader();

            reader.onload = function(e) {
                preview.src = e.target.result;
            }

            if (file) {
                reader.readAsDataURL(file);
            }
        }
    </script>
</body>
</html>

```

3. 编辑页面（templates/edit.html）
```html
<!DOCTYPE html>
<html>
<head>
    <title>确认消费信息</title>
    <style>
        .edit-form { max-width: 600px; margin: 20px auto; }
        .form-group { margin-bottom: 15px; }
        label { display: block; margin-bottom: 5px; }
        input, textarea { width: 100%; padding: 8px; }
        .preview-img { max-width: 300px; margin-bottom: 20px; }
    </style>
</head>
<body>
    <div class="edit-form">
        <h2>请核对消费信息</h2>
        <img class="preview-img" src="{{ url_for('static', filename='uploads/'+image_url) }}">

        <form action="/save" method="post">
            <div class="form-group">
                <label>支付平台：</label>
                <input type="text" name="platform" value="{{ data.platform }}">
            </div>

            <div class="form-group">
                <label>金额（元）：</label>
                <input type="number" step="0.01" name="amount" value="{{ data.amount }}">
            </div>

            <div class="form-group">
                <label>交易时间：</label>
                <input type="datetime-local" name="time"
                       value="{{ data.time.strftime('%Y-%m-%dT%H:%M:%S') }}">
            </div>

            <div class="form-group">
                <label>消费地点：</label>
                <input type="text" name="location" value="{{ data.location }}">
            </div>

            <div class="form-group">
                <label>备注：</label>
                <textarea name="note" rows="3">{{ data.note }}</textarea>
            </div>

            <button type="submit">保存记录</button>
        </form>
    </div>
</body>
</html>

```

## 部署说明
1. 安装依赖：
```bash
pip install flask

```

2. 配置GPT-4o：
- 确保你有可用的API密钥
- 替换app.py中的对应配置

3. 创建所需目录：
```bash
mkdir -p uploads

```

4. 启动服务：
```bash
cd accounting
python app.py
```
在手机浏览器打开 `http://<服务器IP>:5000`

效果演示
（截图演示：上传图片 → 自动识别 → 编辑确认 → 保存成功）

扩展建议
1. 识别优化：针对不同支付平台建立特征词库
2. 数据展示：添加消费统计图表功能
3. 用户系统：增加多用户支持
4. 移动优化：使用响应式框架如Bootstrap

## 部署到 Azure App Service
1. 创建Azure Web App
已经通过控制台创建了一个Azure Web App，名为`<your-app-name>`。

2. 配置环境变量
```bash
az webapp config appsettings set -g <your-region> -n <your-app-name> --settings SCM_DO_BUILD_DURING_DEPLOYMENT="true" AZURE_API_ENDPOINT="https://<your-endpoint>.cognitiveservices.azure.com/" AZURE_API_KEY="<your-api-key>" MYSQL_HOST="<your-mysql-host>" MYSQL_USER="<your-mysql-user>" MYSQL_PASSWORD="<your-mysql-password>" MYSQL_DATABASE="<your-mysql-database>"
```
3. 部署代码
使用命令行把代码部署上去
```bash
zip -r deploy.zip .
az webapp deploy -g <resource-group> -n <app-name> --src-path deploy.zip --type zip
```
4. 访问Web App URL

环境变量和Python依赖库的问题都解决了，但是保存数据库时还是报 500 错，并且在日志中又不显示错误信息。
目前是创建一个Ubuntu的虚拟机，然后在虚拟机上部署Flask应用，这样就可以更好的控制环境和调试问题。
推测是 Python 连接 Azure Database for MySQL 的奇怪问题。
实测确实是 Azure Database for MySQL 的问题，require_secure_transport 选项导致的。Python 连接数据库时加上 Azure 给的证书即可。注意官方文档建议的 2 个证书，目前只有 [DigiCertGlobalRootCA.crt.pem](https://learn.microsoft.com/en-us/azure/mysql/flexible-server/how-to-connect-tls-ssl#download-the-public-ssl-certificate) 可以正常用于 Azure 北3区的 MySQL 服务。



TODO
- [X] 列表展示已保存的收支记录。
- [X] 编辑已有记录。
- [X] 把数据表操作封装到单独的类中，以简化表操作的代码。
- [ ] 样式调整成适配手机端的灵活样式，现在手机打开字体太小。
- [ ] 改进前端交互成为 SPA，主要是更友好的等待和进度显示。