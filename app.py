from datetime import datetime
from models.Receipt import Receipt
import os

from flask import (Flask, render_template, request, send_from_directory)

app = Flask(__name__)

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(
        os.path.join(app.root_path, 'static'),
        'favicon.ico',
        mimetype='image/vnd.microsoft.icon')

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # 处理图片上传
        file = request.files['receipt']
        if file:
            # 不保存上传的文件，而是直接获取文件内容 image_bytes，调用 ChatGPT 时传参数，再输出给信息确认页。
            image_bytes = file.read()
            receipt = Receipt()
            img = receipt.resize(image_bytes)
            parsed_data = receipt.recognize(img)
            # print(parsed_data)
            return render_template('edit.html', data=parsed_data)
    else:
        # 调试用，直接解析图片
        # filePath = os.path.join(current_app.config['UPLOAD_FOLDER'], 'receipt.jpg')
        # print(filePath)
        # with open(filePath, 'rb') as f:
        #     image = f.read()
        #     receipt = Receipt()
        #     img = receipt.resize(image)
        #     # 写出调试图片
        #     with open('static/uploads/resized.jpg', 'wb') as f:
        #         f.write(img)
        #     parsed_data = receipt.recognize(img)
#         strContent = """
# {
#                 "transaction_time": "2025-02-14 09:17:58",
#                 "income_amount": None,
#                 "expense_amount": 10.28,
#                 "transaction_app": "美团App",
#                 "payment_platform": "",
#                 "financial_terminal": "浦发银行信用卡 (0673)",
#                 "memo": "骑行套餐",
#                 "category": "交通"
#             }
# """
#         data= eval(strContent)
        receipt = Receipt()
        res = receipt.listReceipts(10)
        data = {'records': res}
        print(res)
        return render_template('upload.html', data=data)


@app.route('/save', methods=['POST'])
def save_record():
    record = {
    'transaction_time': datetime.strptime(request.form.get('transaction_time'), '%Y-%m-%dT%H:%M:%S') if request.form.get('transaction_time') else None,
    'income_amount': float(request.form.get('income_amount')) if request.form.get('income_amount') else None,
    'expense_amount': float(request.form.get('expense_amount')) if request.form.get('expense_amount') else None,
    'transaction_app': request.form.get('transaction_app') if request.form.get('transaction_app') else None,
    'payment_platform': request.form.get('payment_platform') if request.form.get('payment_platform') else None,
    'financial_terminal': request.form.get('financial_terminal') if request.form.get('financial_terminal') else None,
    'memo': request.form.get('memo') if request.form.get('memo') else None,
    'category': request.form.get('category') if request.form.get('category') else None,
    }

    receipt = Receipt()
    res = receipt.save(record)
    print(res)
    dictHint = {
        'message': '保存成功',
        'url' : '/',
        'link': '返回首页'
    }
    return render_template('hint.html', hint=dictHint)

if __name__ == '__main__':
   app.run(host='0.0.0.0', port=5000, debug=True)
