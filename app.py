from flask import Flask, render_template, jsonify, request, redirect, url_for
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool import ThreadPoolExecutor
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from requests.auth import HTTPBasicAuth
import atexit
import requests
import json
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize SQLAlchemy without the app
db = SQLAlchemy()

# Load secrets
try:
    with open('secrets.json') as secrets_file:
        secrets = json.load(secrets_file)
except FileNotFoundError:
    logger.error("secrets.json file not found.")
    secrets = {}

def create_app():
    app = Flask(__name__)

    # Database configuration
    app.config['SQLALCHEMY_DATABASE_URI'] = secrets.get(
        "SQLALCHEMY_DATABASE_URI", "postgresql://nano:pw@bootstrap_db:5432/bootstrap"
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Initialize SQLAlchemy with the app
    db.init_app(app)

    # Define the Node model
    class Node(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        environment = db.Column(db.String)  # Field to distinguish environments
        block_count = db.Column(db.Integer)
        cemented_count = db.Column(db.Integer)
        address = db.Column(db.String)
        node_id = db.Column(db.String)
        major_version = db.Column(db.String)
        minor_version = db.Column(db.String)
        patch_version = db.Column(db.String)
        pre_release_version = db.Column(db.String)
        timestamp = db.Column(db.DateTime, default=datetime.utcnow)

        def __repr__(self):
            return f'Node {self.node_id} ({self.environment})'

    # Make the Node model accessible globally
    app.Node = Node

    # Scheduler setup with ThreadPoolExecutor
    scheduler = BackgroundScheduler(executors={'default': ThreadPoolExecutor(1)})

    # Schedule job every 30 minutes
    scheduler.add_job(
        func=get_metrics_background,
        args=[app],
        trigger="interval",
        minutes=30
    )

    # Do not start the scheduler here
    # scheduler.start()

    # Shut down the scheduler when exiting the app
    atexit.register(lambda: scheduler.shutdown())

    # Expose the scheduler
    app.scheduler = scheduler

    # Define routes
    @app.route('/')
    def root():
        return redirect(url_for('index', environment='beta'))

    @app.route('/<environment>')
    def index(environment):
        if environment not in ['beta', 'live']:
            return "Invalid environment", 404
        return render_template('index.html', environment=environment)

    @app.route('/node_chart/<node_id>', methods=['GET'])
    def node_chart(node_id):
        return render_template('node_chart.html', node_id=node_id)

    @app.route('/node_data/<node_id>', methods=['GET'])
    def node_data(node_id):
        try:
            Node = app.Node
            one_week_ago = datetime.utcnow() - timedelta(weeks=1)
            nodes = Node.query.filter(
                Node.node_id == node_id,
                Node.timestamp >= one_week_ago
            ).order_by(Node.timestamp.asc()).all()

            result = []
            for node in nodes:
                # Assuming the version is stored as major.minor.patch format
                major_version =  node.major_version 
                minor_version =node.minor_version 
                patch_version = node.patch_version 

                formatted_version = f"{major_version}.{minor_version}.{patch_version}"

                result.append({
                    'block_count': node.block_count,
                    'cemented_count': node.cemented_count,
                    'timestamp': node.timestamp.isoformat(),
                    'version': formatted_version
                })

            return jsonify(result)
        except Exception as e:
            logger.error(f"Error fetching node data: {e}")
            return jsonify({"error": "Error fetching node data"}), 500

    @app.route('/get_metrics', methods=['POST'])
    def get_metrics():
        try:
            Node = app.Node
            environment = request.form.get('environment')
            if environment not in ['beta', 'live']:
                return "Invalid environment", 404

            # Fetch latest telemetry data via RPC call (without storing in the database)
            url = 'https://rpcproxy.bnano.info/proxy' if environment == 'beta' else 'https://proxy.nanobrowse.com/rpc'
            data = {"action": "telemetry", "raw": "true"}  # Use 'telemetry' to get data from all peers
            headers = {'Content-Type': 'application/json'}

            auth = None
            if environment == 'live':
                username = secrets.get("LIVE_USER")
                password = secrets.get("LIVE_PW")
                if not username or not password:
                    logger.error("LIVE_USER or LIVE_PW not found in secrets.json.")
                    return jsonify({"error": "Authentication required"}), 500
                auth = HTTPBasicAuth(username, password)

            response = requests.post(url, data=json.dumps(data), headers=headers, auth=auth, timeout=60)
            response.raise_for_status()
            latest_metrics = response.json().get('metrics', [])
     

            # Prepare data for response
            now = datetime.utcnow()
            one_hour_ago = now - timedelta(hours=1)
            one_day_ago = now - timedelta(days=1)

            # Fetch historical data from the database
            nodes_past_hour = Node.query.filter(
                Node.timestamp <= one_hour_ago,
                Node.environment == environment
            ).order_by(Node.timestamp.desc()).all()

            nodes_past_day = Node.query.filter(
                Node.timestamp <= one_day_ago,
                Node.environment == environment
            ).order_by(Node.timestamp.desc()).all()

            nodes_past_hour_dict = {node.node_id: node for node in nodes_past_hour}
            nodes_past_day_dict = {node.node_id: node for node in nodes_past_day}

            # Calculate max block and cemented counts from latest metrics
            max_block_count = max([int(metric.get('block_count', 0)) for metric in latest_metrics]) if latest_metrics else 0
            max_cemented_count = max([int(metric.get('cemented_count', 0)) for metric in latest_metrics]) if latest_metrics else 0

            metrics_response = []
            for metric in latest_metrics:
                node_id = metric.get('node_id', '')
                timestamp = datetime.utcnow()  # Current time

                metric_response = {
                    'block_count': int(metric.get('block_count', 0)),
                    'cemented_count': int(metric.get('cemented_count', 0)),
                    'address': metric.get('address', ''),
                    'node_id': node_id,
                    'major_version': metric.get('major_version', ''),
                    'minor_version': metric.get('minor_version', ''),
                    'patch_version': metric.get('patch_version', ''),
                    'pre_release_version': metric.get('pre_release_version', '')
                }

                # Fetch historical data for this node
                node_past_hour = nodes_past_hour_dict.get(node_id)
                node_past_day = nodes_past_day_dict.get(node_id)

                if node_past_hour:
                    delta_blocks = metric_response['block_count'] - node_past_hour.block_count
                    delta_cemented = metric_response['cemented_count'] - node_past_hour.cemented_count
                    delta_time_hours = (timestamp - node_past_hour.timestamp).total_seconds() / 3600
                    if delta_time_hours > 0:
                        metric_response['hourly_blocks'] = delta_blocks / delta_time_hours
                        metric_response['hourly_cemented'] = delta_cemented / delta_time_hours

                if node_past_day:
                    delta_blocks = metric_response['block_count'] - node_past_day.block_count
                    delta_cemented = metric_response['cemented_count'] - node_past_day.cemented_count
                    delta_time_hours = (timestamp - node_past_day.timestamp).total_seconds() / 3600
                    if delta_time_hours > 0:
                        metric_response['daily_blocks'] = delta_blocks / delta_time_hours * 24
                        metric_response['daily_cemented'] = delta_cemented / delta_time_hours * 24

                metrics_response.append(metric_response)

            return jsonify(metrics=metrics_response, max_block_count=max_block_count, max_cemented_count=max_cemented_count)
        except Exception as e:
            logger.error(f"Error in /get_metrics: {e}")
            return jsonify({"error": "Error fetching metrics"}), 500

    return app

# Define get_metrics_background at module level
def get_metrics_background(app):
    with app.app_context():
        Node = app.Node
        for environment in ['beta', 'live']:
            logger.info(f"Fetching telemetry data for {environment} environment.")
            try:
                url = 'https://rpcproxy.bnano.info/proxy' if environment == 'beta' else 'https://proxy.nanobrowse.com/rpc'
                data = {"action": "telemetry", "raw": "true"}  # Use 'telemetry' to get data from all peers
                headers = {'Content-Type': 'application/json'}

                auth = None
                if environment == 'live':
                    username = secrets.get("LIVE_USER")
                    password = secrets.get("LIVE_PW")
                    if not username or not password:
                        logger.error("LIVE_USER or LIVE_PW not found in secrets.json.")
                        continue
                    auth = HTTPBasicAuth(username, password)

                response = requests.post(url, data=json.dumps(data), headers=headers, auth=auth, timeout=60)
                response.raise_for_status()
                metrics = response.json().get('metrics', [])

                timestamp = datetime.utcnow()
                for metric in metrics:
                    node = Node(
                        environment=environment,  # Store the environment
                        block_count=int(metric.get('block_count', 0)),
                        cemented_count=int(metric.get('cemented_count', 0)),
                        address=metric.get('address', ''),
                        node_id=metric.get('node_id', ''),
                        major_version=metric.get('major_version', ''),
                        minor_version=metric.get('minor_version', ''),
                        patch_version=metric.get('patch_version', ''),
                        pre_release_version=metric.get('pre_release_version', ''),
                        timestamp=timestamp
                    )
                    db.session.add(node)
                db.session.commit()
                logger.info(f"Telemetry data for {environment} environment fetched and stored successfully.")
            except Exception as e:
                logger.error(f"Error fetching telemetry data for {environment}: {e}")
                db.session.rollback()

app = create_app()

if __name__ == '__main__':
    with app.app_context():
        try:
            logger.info("Creating database tables if they don't exist...")
            db.create_all()
            logger.info("Database tables created or already exist.")

            # Start the scheduler after tables are created
            app.scheduler.start()
            # Optionally, perform an initial data fetch
            # get_metrics_background(app)
        except Exception as e:
            logger.error(f"Error during initial setup: {e}")
    app.run(host='0.0.0.0', port=5000)
