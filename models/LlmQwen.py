import base64
import json
import os 
import requests
from typing import List, Optional, Dict, Any


class LlmQwen:
    """
    阿里云通义千问大语言模型调用类
    """
    def __init__(self):
        """
        初始化客户端
        :param api_key: 阿里云DashScope API密钥（从控制台获取）
        """
        self.api_key = os.getenv('QWEN_KEY')
        if not self.api_key:
            raise ValueError("环境变量 QWEN_KEY 未设置，请在环境中配置API密钥")
        
        self.base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        self.model = "qwen3-vl-plus"

    def image_to_base64(self, image_path: str) -> str:
        """
        将本地图片转换为base64编码
        :param image_path: 本地图片路径
        :return: base64编码字符串
        """
        try:
            with open(image_path, "rb") as f:
                base64_data = base64.b64encode(f.read()).decode("utf-8")
            return base64_data
        except Exception as e:
            raise ValueError(f"图片转换base64失败: {str(e)}")

    def get_image_from_url(self, image_url: str) -> str:
        """
        从网络URL获取图片并转换为base64编码
        :param image_url: 图片网络地址
        :return: base64编码字符串
        """
        try:
            response = requests.get(image_url, timeout=10)
            response.raise_for_status()
            base64_data = base64.b64encode(response.content).decode("utf-8")
            return base64_data
        except Exception as e:
            raise ValueError(f"从URL获取图片失败: {str(e)}")

    def chat(self, question: str, image_base64: str = '', image_type: str = "png", stream: bool = False,
                       temperature: float = 0,
                       max_tokens: int = 1024) -> str:
        """
        发送带图片或仅文本的问答请求
        :param question: 问题文本
        :param image_base64: 图片的base64编码（可选，如果为空则只进行文本问答）
        :param image_type: 图片类型，默认为"png"
        :param temperature: 生成温度（0-1，越高越随机）
        :param max_tokens: 最大生成token数
        :return: 回答的文本
        """
        # 构建消息内容
        # 定义元素类型：值可以是字符串 或 嵌套字典（str->str）
        content: List[Dict[str, Any]]  = [
            # 文本问题
            {"type": "text", "text": question}
        ]
        
        # 如果提供了图片，则添加到内容中
        if image_base64:
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/{image_type};base64,{image_base64}"
                }
            })
        
        # 构建请求体
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": content
                }
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False  # 非流式响应
        }

        # 发送请求
        response = requests.post(
                url=self.base_url,
                headers=self.headers,
                json=payload,
                timeout=30
        )
        response.raise_for_status()  # 抛出HTTP错误
        result = response.json()
        answer = self.extract_answer(result)
        return answer

    def extract_answer(self, result) -> str:
        """
        从响应结果中提取回答文本
        :param result: 接口返回的字典结果
        :return: 回答文本
        """
        if not result:
            return ""
        try:
            return result["choices"][0]["message"]["content"]
        except KeyError:
            print("响应格式异常，无法提取回答")
            return json.dumps(result, ensure_ascii=False)


# 使用示例
if __name__ == "__main__":
    # 1. 配置你的API密钥（必填）
    
    # 2. 初始化客户端
    client = LlmQwen()

    # 示例：使用纯文本问答
    QUESTION = "你是谁？"
    # result = client.chat(
    #         question=QUESTION
    #     )

    # # 提取并打印回答
    # # print(result)



    # 示例1：使用本地图片
    try:
        # 读取本地图片并转换为base64
        LOCAL_IMAGE_PATH = "j.jpg"  # 替换为你的本地图片路径
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
        
        # 将图片转换为base64编码
        with open(LOCAL_IMAGE_PATH, "rb") as f:
            image_base64 = base64.b64encode(f.read()).decode("utf-8")
        image_type = LOCAL_IMAGE_PATH.split(".")[-1]  # 获取图片类型，如jpg, png等

        # 发送请求
        result = client.chat(
            question=prompt,
            image_base64=image_base64,
            image_type=image_type
        )

        # 提取并打印回答
        print(result)

    except Exception as e:
        print(f"本地图片问答失败: {str(e)}")

    # 示例2：使用网络图片
    # try:
    #     # 配置网络图片URL和问题
    #     IMAGE_URL = "https://img-s.msn.cn/tenant/amp/entityid/AA1TuJdi.img"  # 替换为有效的图片URL
    #     QUESTION = "这张图片里有什么？请详细说明"

    #     # 从网络获取图片并转换为base64
    #     response = requests.get(IMAGE_URL)
    #     image_base64 = base64.b64encode(response.content).decode("utf-8")
    #     image_type = "jpeg"  # 假设网络图片是jpeg格式

    #     # 发送请求
    #     result = client.chat(
    #         question=QUESTION,
    #         image_base64=image_base64,
    #         image_type=image_type,
    #         temperature=0.5
    #     )
    #     print(result)
    #     # 提取并打印回答
    #     # answer = client.extract_answer(result)
    #     # print("\n=== 网络图片问答结果 ===")
    #     # print(answer)

    # except Exception as e:
    #     print(f"网络图片问答失败: {str(e)}")