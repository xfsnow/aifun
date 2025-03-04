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
        # 展示最近记录的条数，如果有请求参数 num，展示 num 条记录，默认为10条
        num = request.args.get('num')
        num = int(num) if num and num.isdigit() else 10
        receipt = Receipt()
        res = receipt.listReceipts(num)
        data = {'records': res}
        # print(res)
        return render_template('index.html', data=data)

@app.route('/edit', methods=['GET', 'POST'])
def edit():
    if request.method == 'POST':
        id = request.form.get('id')
        data = {
            'transaction_time': request.form.get('transaction_time'),
            'income_amount': request.form.get('income_amount'),
            'expense_amount': request.form.get('expense_amount'),
            'transaction_app': request.form.get('transaction_app'),
            'payment_platform': request.form.get('payment_platform'),
            'financial_terminal': request.form.get('financial_terminal'),
            'memo': request.form.get('memo'),
            'category': request.form.get('category')
        }
        receipt = Receipt()
        res = receipt.editReceipt(id, data)
        print(res)
        dictHint = {
            'message': '编辑成功',
            'url' : '/',
            'link': '返回首页'
        }
        return render_template('hint.html', hint=dictHint)
    else:
        # 读取一条记录，ID 为 request.args.get('id')
        receipt = Receipt()
        record_id = request.args.get('id')
        # 如果 id 不是大于0的整数形式，返回错误提示
        if not record_id.isdigit() or int(record_id) <= 0:
            dictHint = {
                'message': 'ID 格式错误',
                'url' : '/',
                'link': '返回首页'
            }
            return render_template('hint.html', hint=dictHint)
        res = receipt.getReceipt(record_id)
        # 如果没有记录，返回错误提示
        if not res:
            dictHint = {
                'message': '没有查到相关记录',
                'url' : '/',
                'link': '返回首页'
            }
            return render_template('hint.html', hint=dictHint)
        print(res)
        return render_template('edit.html', data=res)

@app.route('/save', methods=['POST'])
def save():
    record = {
    'transaction_time': request.form.get('transaction_time') if request.form.get('transaction_time') else None,
    'income_amount': request.form.get('income_amount') if request.form.get('income_amount') else None,
    'expense_amount': request.form.get('expense_amount') if request.form.get('expense_amount') else None,
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
