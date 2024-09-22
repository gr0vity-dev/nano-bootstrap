from flask import Flask, render_template, jsonify, request, redirect, url_for
from apscheduler.schedulers.background import BackgroundScheduler
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from requests.auth import HTTPBasicAuth
import atexit
import requests
import json

app = Flask(__name__)
with open('secrets.json') as secrets_file:
    secrets = json.load(secrets_file)

scheduler = BackgroundScheduler()
scheduler.add_executor('processpool')

app.config['SQLALCHEMY_DATABASE_URI'] = secrets["SQLALCHEMY_DATABASE_URI"]
db = SQLAlchemy(app)


class Node(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    block_count = db.Column(db.Integer)
    cemented_count = db.Column(db.Integer)
    address = db.Column(db.String)
    node_id = db.Column(db.String)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'Node {self.node_id}'


def get_metrics_background():
    for environment in ['beta', 'live']:
        print(f"EXEC get_metrics_background {environment}")
        url = 'https://rpcproxy.bnano.info/proxy' if environment == 'beta' else 'https://proxy.nanobrowse.com/rpc'
        data = {"action": "telemetry", "raw": "true"}
        headers = {'Content-Type': 'application/json'}

        auth = None
        if environment == 'live':
            username = secrets["LIVE_USER"]
            password = secrets["LIVE_PW"]
            auth = HTTPBasicAuth(username, password)

        response = requests.post(url,
                                 data=json.dumps(data),
                                 headers=headers,
                                 auth=auth)
        metrics = response.json()['metrics']

        for metric in metrics:
            node = Node(block_count=int(metric['block_count']),
                        cemented_count=int(metric['cemented_count']),
                        address=metric['address'],
                        node_id=metric['node_id'])
            db.session.add(node)
        db.session.commit()


# Schedule job every 30 minutes
scheduler.add_job(func=get_metrics_background, trigger="interval", minutes=30)
scheduler.start()

# Shut down the scheduler when exiting the app
atexit.register(lambda: scheduler.shutdown())


@app.route('/')
def root():
    return redirect(url_for('index', environment='beta'))


# @app.route('/node/<address>')
# def node_page(address):
#     return render_template('node_data.html')


# @app.route('/node_chart', methods=['GET'])
# def node_chart():
#     node_id = request.args.get('node_id')
#     return render_template('node_chart.html', node_id=node_id)

@app.route('/node_chart/<node_id>', methods=['GET'])
def node_chart(node_id):
    return render_template('node_chart.html', node_id=node_id)



@app.route('/<environment>')
def index(environment):
    if environment not in ['beta', 'live']:
        return "Invalid environment", 404
    return render_template('index.html', environment=environment)


@app.route('/node_data/<node_id>', methods=['GET'])
def node_data(node_id):
    one_week_ago = datetime.utcnow() - timedelta(weeks=1)

    nodes = Node.query.filter(Node.node_id == node_id,
                              Node.timestamp >= one_week_ago).order_by(
                                  Node.timestamp.asc()).all()

    result = []
    for node in nodes:
        result.append({
            'block_count': node.block_count,
            'cemented_count': node.cemented_count,
            'timestamp': node.timestamp.isoformat()  # convert to string format
        })

    return jsonify(result)


@app.route('/get_metrics', methods=['POST'])
def get_metrics():
    environment = request.form.get('environment')
    if environment not in ['beta', 'live']:
        return "Invalid environment", 404

    url = 'https://rpcproxy.bnano.info/proxy' if environment == 'beta' else 'https://proxy.nanobrowse.com/rpc'
    data = {"action": "telemetry", "raw": "true"}
    headers = {'Content-Type': 'application/json'}

    auth = None
    if environment == 'live':
        username = secrets["LIVE_USER"]
        password = secrets["LIVE_PW"]
        auth = HTTPBasicAuth(username, password)

    response = requests.post(url,
                             data=json.dumps(data),
                             headers=headers,
                             auth=auth)
    metrics = response.json()['metrics']

    max_block_count = max([int(metric['block_count']) for metric in metrics])
    max_cemented_count = max(
        [int(metric['cemented_count']) for metric in metrics])

    now = datetime.utcnow()
    one_hour_ago = now - timedelta(hours=1)
    one_day_ago = now - timedelta(days=1)

    # Pull all necessary data from the database at once
    nodes_past_day = Node.query.filter(Node.timestamp.between(
        one_day_ago, now)).all()

    # Transform data into a form that is easier to work with
    nodes_by_node_id = {node.node_id: node for node in nodes_past_day}

    for metric in metrics:
        if not ("node_id" in metric and metric["node_id"]): continue

        node_past_hour = node_past_day = nodes_by_node_id.get(
            metric['node_id'])
        if node_past_hour and node_past_hour.timestamp < one_hour_ago:
            node_past_hour = None

        for time_period in [(node_past_hour, 60, 'hourly'),
                            (node_past_day, 24, 'daily')]:
            node, time_multiplier, label_prefix = time_period
            if node:
                delta_time = (
                    now - node.timestamp).total_seconds() / 3600  # in hours
                for count_type in [('block_count', 'blocks'),
                                   ('cemented_count', 'cemented')]:
                    metric_key, label_suffix = count_type
                    metric_value = (int(metric[metric_key]) - getattr(
                        node, metric_key)) * time_multiplier / delta_time
                    metric[
                        f'{label_prefix}_{label_suffix}'] = metric_value if metric_value >= 0 else None

    return jsonify(metrics=metrics,
                   max_block_count=max_block_count,
                   max_cemented_count=max_cemented_count)


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    # get_metrics_background()
    app.run(host='0.0.0.0', port=5000)
