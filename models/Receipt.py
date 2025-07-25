from io import BytesIO
from PIL import Image
from models.Model import Model
from models.Table import Table

import base64
import json
import openai
import os
import time

# 在环境变量或配置中设置以下参数：
#   AZURE_API_KEY        Azure OpenAI 的API密钥
#   AZURE_API_ENDPOINT   Azure OpenAI 的API端点，比如 https://xxx.openai.azure.com/
#   AZURE_API_VERSION    Azure OpenAI API版本号，比如 2025-04-01-preview
#   AZURE_MODEL_NAME     GPT-4o部署的模型名称

openai.azure_endpoint = os.getenv("AZURE_API_ENDPOINT", "")
openai.api_key = os.getenv("AZURE_API_KEY", "")
openai.api_type = "azure"
openai.api_version = os.getenv("AZURE_API_VERSION", "2025-04-01-preview")
# GPT‑4o‑mini 适用于图像和文本的多模态模型，深入推理稍弱，但处理速度更快，适合固定场景需要及时响应的应用。实测感觉 gpt-4.1 比 gpt-4o‑mini 速度还快。
openai.model = os.getenv("AZURE_MODEL_NAME")

class Receipt(Model):
    IMAGE_FORMAT = 'png'
    # 按ID编辑1条记录
    def editReceipt(self, id: int, receipt: dict) -> int:
        # 更新数据表
        tableAccount = Table('accounting')
        res = tableAccount.where('id', '=', id).update(receipt)
        return res

    # 按记录ID读取1条记录
    def getReceipt(self, id) -> dict:
        tableAccount = Table('accounting')
        res = tableAccount.select('*').where('id', '=', id).get()
        return res[0]

    # 按时间倒序读取多条记录
    def listReceipts(self, page: int = 1) -> list:
        tableAccount = Table('accounting', debug=True)
        # 每页条数为 Model.PAGE_EACH，转换为limit() 参数为 page * Model.PAGE_EACH
        pe = Model.PAGE_EACH
        res = tableAccount.select('*').order_by('transaction_time', 'DESC').limit((page - 1) * pe, pe).get()
        return res

    # 重置图片大小
    # 手机截图尺寸比较大，缩小成宽最大600像素
    # param image_bytes: 图片的字节流
    # param max_width: 图片的最大宽度，默认值为200
    # return: 处理后的图片的字节流
    def resize(self, image_bytes: bytes, max_width: int = 300) -> bytes:
        image = Image.open(BytesIO(image_bytes))
        if image.width <= max_width:
            return image_bytes

        new_height = int(max_width * image.height / image.width)
        resized_image = image.resize((max_width, new_height))
        with BytesIO() as output:
            resized_image.save(output, format=self.IMAGE_FORMAT)
            return output.getvalue()

    # 注意传图片体积太大时API会报错 {'error': {'code': '429', 'message': 'Rate limit is exceeded. Try again in 86400 seconds.'}}
    # 虽说文档说文体体积最大512MB，实际200多KB的图片都会报错。换成小点的图片。
    # 识别图片内容
    def recognize(self, image_bytes: bytes) -> dict:
        img_type = "image/"+self.IMAGE_FORMAT
        b64_image = base64.b64encode(image_bytes).decode("utf-8")

        prompt = """
这是交易截图，请识别消费/收入信息，识别出的文字内容应严格遵循图片上原有内容，不要转换来翻译成其它语言。请返回仅 JSON 格式的数据，不要输出任何其他内容。
提取字段:
交易时间：如2025-02-15 12:30:00，使用时间格式表示
收入金额：如99.99，使用数字表示，如果没有收入则为空
支出金额：如99.99，使用数字表示，如果没有支出则为空
消费的应用：提取项目“交易场所”，如沃尔玛、拼多多、线下商店、公交473路等
支付平台：如微信、支付宝、美团支付等
金融终端：如某银行银行卡、信用卡、微信零钱，支付宝花呗等
说明：如小票备注、商品名称、交易号等
类别：如餐饮、交通、购物、医疗等。水、电、燃气分类到生活缴费。

返回示例格式:
{
  "transaction_time": "2025-02-15 12:30:00",
  "income_amount": "",
  "expense_amount": 99.99,
  "transaction_app": "拼多多",
  "payment_platform": "微信",
  "financial_terminal": "信用卡",
  "memo": "订单号：987654321",
  "category": "餐饮"
}
如果无法识别，返回空。
"""
        jsonMessages = [
        {"role": "system","content": "你是一个善于提取结构化信息的助手。"},
        {"role": "user", "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:{img_type};base64,{b64_image}"},},
            ],
        }
        ]
        time_start = time.time()
        completion = openai.chat.completions.create(model=openai.model, messages=jsonMessages)
        time_end = time.time()
        print(f"GPT model: {openai.model}, Time taken for completion: {time_end - time_start} seconds")
        jsonResponse = completion.to_json()
        parsed_response = json.loads(jsonResponse)
        #  message.content。如果存在 ["choices"][0]["message"]["content"] 则继续，否则返回失败提示信息
        if "choices" not in parsed_response or len(parsed_response["choices"]) == 0:
            return {"error": "No response from GPT-4o."}

        strContent = parsed_response["choices"][0]["message"]["content"]
        # 即使在提示语中加上“仅返回JSON”，还是有可能返回形如  ```json {  "transaction_time": "2025-02-17 08:30:11",}``` 带markdown的字符串，需要去掉。
        strContent = strContent.replace("```json", "").replace("```", "")
        # strContent 转换成 Dict。json.loads() 会报错，因为字符串中的未转义的中文，需要用 eval() 来处理。
        print(strContent)
        jsonContent = eval(strContent)
        # 读取到的图片文件内容输出成可以显示在 HTML 中的图片格式
        jsonContent['preview_image'] = 'data:image/'+self.IMAGE_FORMAT+';base64,' + b64_image
        return jsonContent

    # 保存识别结果
    def save(self, receipt: dict) -> int:
        # 保存到数据库
        tableAccount = Table('accounting', debug=True)
        res = tableAccount.add(receipt)
        return res