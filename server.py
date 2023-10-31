from flask import Flask, request, jsonify, abort

from db import DBManager, TransactionLockedException

app = Flask(__name__)

db_manager = DBManager


@app.route('/get/value_by_key/', methods=['GET'])
def GetValueByKey():
    key = request.args.get('q', '')
    result = db_manager.get(key=key)
    return jsonify(result)


@app.route('/get/keys_by_value/', methods=['GET'])
def GetKeysByValue():
    value = request.args.get('q', '')
    result = db_manager.get_keys_by_value(value=value)
    return jsonify(result)


@app.route('/edit/', methods=['POST'])
def Edit():
    content_type = request.headers.get('content-type')
    if content_type.lower() != 'application/json':
        return abort(400)

    data = request.json
    if not data:
        return abort(400)

    try:
        transaction = db_manager.bulk_create_or_update(data)
        return jsonify(transaction.__repr__())
    except TransactionLockedException:
        return abort(423)


@app.route('/delete/', methods=['POST'])
def Delete():
    content_type = request.headers.get('content-type')
    if content_type.lower() != 'application/json':
        return abort(400)

    data = request.json
    if not data:
        return abort(400)

    try:
        transaction = db_manager.bulk_delete(data)
        return jsonify(transaction.__repr__())
    except TransactionLockedException:
        return abort(423)


if __name__ == '__main__':
    app.run()
