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

# 无容器直接部署在Ubuntu虚拟机上
ECS 的安全组开放入站 5000 端口

https://zhuanlan.zhihu.com/p/22320388002
Ubuntu 24 默认安装了 Python 3.12和 pip 。
阿里云 ECS 访问 github 不行，修改 hosts 本地解析
```sh
echo "140.82.112.3 github.com" >> /etc/hosts
```

设置 Python 应用运行依赖的环境变量
```sh
# 为手动执行 Flask 应用设置环境变量
sudo vi /etc/environment
# 在文件末尾添加以下内容
FLASK_ENV=development # 开发环境，或者阿里云环境需要，所有不开启SSL连接MySQL的都要设置
AZURE_API_ENDPOINT="https://<your-endpoint>.cognitiveservices.azure.com/"
AZURE_API_KEY="<your-api-key>"
AZURE_MODEL_NAME="gpt-4o"
MYSQL_HOST="<your-mysql-host>"
MYSQL_USER="<your-mysql-user>"
MYSQL_PASSWORD="<your-mysql-password>"
MYSQL_DATABASE="<your-mysql-database>"
```

安装 Python 3.12 的 venv 模块
```sh
apt install python3.12-venv
mkdir /var/local/aifun
cd /var/local/aifun
python3.12 -m venv venv
# 安装完成后激活虚拟环境，如果系统重启或者手动启动 Flask 应用，从这步开始
source venv/bin/activate
pip install --upgrade pip
# 安装 Gunicorn 作为 WSGI 服务器
pip install gunicorn
git clone https://github.com/xfsnow/aifun.git
cd aifun
pip install -r requirements.txt
# 手动测试运行
gunicorn app:app -b 0.0.0.0:5000
```
找到 ECS 外网 IP 地址，手机浏览器访问 `http://<your-ecs-ip>:5000`，如果能看到上传页面，则说明 Flask 应用运行正常。

## 设置为系统服务，所有环境变量在这里再设置一遍，以便让 Flask 应用在系统服务中运行时也能获取到这些环境变量
```sh
sudo vi /etc/systemd/system/aifun.service
# 添加以下
[Unit]
Description=Aifun Service
After=network.target

[Service]
User=www-data
Group=www-data
Environment="AZURE_API_ENDPOINT=https://<your-endpoint>.cognitiveservices.azure.com/"
Environment="AZURE_API_KEY=<your-api-key>"
Environment="AZURE_MODEL_NAME=<your-api-model>"
Environment="MYSQL_HOST=<rds-internal-endpoint>"
Environment="MYSQL_USER=<mysql-username>"
Environment="MYSQL_PASSWORD=<mysql-password>"
Environment="MYSQL_DATABASE=<mysql-database>"
Environment="FLASK_ENV=development"
WorkingDirectory=/var/local/aifun/aifun
# 使用 Gunicorn 启动 Flask 应用。这里 -w 2 表示使用几个工作进程，-k gthread 表示使用线程池工作模式，--threads 2 表示每个工作进程使用2个线程。
ExecStart=/var/local/aifun/venv/bin/gunicorn -w 2 -k gthread --threads 2 -b 0.0.0.0:5000 app:app

Restart=always

[Install]
WantedBy=multi-user.target
# 保存退出

sudo systemctl enable aifun.service
sudo systemctl start aifun.service
sudo systemctl stop aifun.service
# 查看服务状态
sudo systemctl status aifun.service

# 修改服务配置后，需要重新加载服务配置
sudo systemctl daemon-reload
sudo systemctl restart aifun.service
# 查看日志
sudo journalctl -u aifun.service -f

```

前面加个 nginx 内部转发到 Python 服务的 5000 端口，对外统一用 SSL 的 433 端口了。

nginx 配置文件保存到文件中，这样 nginx 程序配置可以软链接到相应的文件， nginx 配置文件也可以通过源码进行版本管理了。

[nginx 配置文件](aifun.nginx.conf)


TODO
- [X] 列表展示已保存的收支记录。
- [X] 编辑已有记录。
- [X] 把数据表操作封装到单独的类中，以简化表操作的代码。
- [ ] 样式调整成适配手机端的灵活样式，现在手机打开字体太小。
- [ ] 改进前端交互成为 SPA，主要是更友好的等待和进度显示。