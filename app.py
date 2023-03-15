from flask import Flask, render_template, jsonify
import requests
import json

app = Flask(__name__)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/get_metrics')
def get_metrics():
    url = 'https://rpcproxy.bnano.info/proxy'
    data = {"action": "telemetry", "raw": "true"}
    headers = {'Content-Type': 'application/json'}

    response = requests.post(url, data=json.dumps(data), headers=headers)
    metrics = response.json()['metrics']

    max_block_count = max([int(metric['block_count']) for metric in metrics])
    max_cemented_count = max(
        [int(metric['cemented_count']) for metric in metrics])

    return jsonify(metrics=metrics,
                   max_block_count=max_block_count,
                   max_cemented_count=max_cemented_count)


if __name__ == '__main__':
    app.run(host="0.0.0.0", port="5000")
