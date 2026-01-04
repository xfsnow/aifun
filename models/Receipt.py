from io import BytesIO
from PIL import Image
from .LlmQwen import LlmQwen
from .Table import Table
from .Model import Model

import base64
import json
import time

class Receipt(Table):
    IMAGE_FORMAT = 'png'
    
    def __init__(self):
        super().__init__('accounting', debug=True)

    # 按ID编辑1条记录
    def editReceipt(self, id: str, receipt: dict) -> int:
        # 更新数据表
        return self.where('id', '=', id).update(receipt)

    # 按记录ID读取1条记录
    def getReceipt(self, id) -> dict:
        res = self.select('*').where('id', '=', id).get()
        return res[0] if res else {}

    # 按时间倒序读取多条记录
    def listReceipts(self, page: int = 1) -> list:
        # 每页条数为 Model.PAGE_EACH，转换为limit() 参数为 page * Model.PAGE_EACH
        pe = Model.PAGE_EACH
        res = self.select('*').order_by('transaction_time', 'DESC').limit((page - 1) * pe, pe).get()
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
        b64_image = base64.b64encode(image_bytes).decode("utf-8")

        prompt = """
这是交易截图，请识别消费/收入信息，识别出的文字内容应严格遵循图片上原有内容，不要转换来翻译成其它语言。请返回仅 JSON 格式的数据，不要输出任何其他内容。
提取字段:
交易时间：如2025-02-15 12:30:00，使用时间格式表示
收入金额：如99.99，使用数字表示，如果没有收入则为空
支出金额：如99.99，使用数字表示，如果没有支出则为空
消费的应用：提取项目"交易场所"，如沃尔玛、拼多多、线下商店、公交473路等
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

        time_start = time.time()
        
        # 创建LlmQwen实例并调用图像识别功能
        llm = LlmQwen()
        strContent = llm.chat(prompt, b64_image, self.IMAGE_FORMAT)
        
        time_end = time.time()
        print(f"Qwen model: {llm.model}, Time taken for completion: {time_end - time_start} seconds")
        
        # 即使在提示语中加上"仅返回JSON"，还是有可能返回形如  ```json {  "transaction_time": "2025-02-17 08:30:11",}``` 带markdown的字符串，需要去掉。
        strContent = strContent.strip().replace("```json", "").replace("```", "").strip()
        # 尝试使用 json.loads() 解析，它比 eval 更安全
        try:
            jsonContent = json.loads(strContent)
        except json.JSONDecodeError as e:
            print(f"JSON解析错误: {e}")
            print(f"尝试解析的内容: {strContent}")
            jsonContent = {}
        # 读取到的图片文件内容输出成可以显示在 HTML 中的图片格式
        jsonContent['preview_image'] = 'data:image/'+self.IMAGE_FORMAT+';base64,' + b64_image
        return jsonContent

    # 保存识别结果
    def save(self, receipt: dict) -> int:
        # 保存到数据库
        tableAccount = Table('accounting', debug=True)
        res = tableAccount.add(receipt)
        return res

if __name__ == '__main__':
    receipt = Receipt()
    # 读取测试图片
    with open('j.jpg', 'rb') as f:
        image_bytes = f.read()
    # 重置图片大小
    resized_image = receipt.resize(image_bytes)
    # 识别图片内容
    result = receipt.recognize(resized_image)
    print("识别结果:", result)    