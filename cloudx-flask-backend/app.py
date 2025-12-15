from flask import Flask, request, jsonify
import uuid
import threading
import json
import os
from datetime import datetime, timezone
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from scanners import network_scanners as scanners
import subprocess
import psutil
from ping3 import ping as ping_host
from deployer import AgentDeployer

# Initialize Deployer
SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scripts')
deployer = AgentDeployer(SCRIPTS_DIR)

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///scans.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
# In a real app, you'd want to restrict the origins.
# For development, '*' is fine.
CORS(app)

# A dictionary to keep track of running scan processes
active_scans = {} # { 'job_id': process_object }

# --- Database Model ---
class Scan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    tool = db.Column(db.String(50), nullable=False, default='nmap')
    target = db.Column(db.String(128), nullable=False)
    scan_type = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='submitted')
    progress = db.Column(db.Integer, default=0)
    results = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Scan {self.job_id}>'

def run_scan_in_background(app, job_id, tool, target, scan_type, port=None):
    with app.app_context():
        try:
            scan_generator = scanners.run_scan(tool, target, scan_type, port=port)

            # First, get the process object from the generator
            process_update = next(scan_generator)
            if process_update['type'] == 'process':
                active_scans[job_id] = process_update['value']
            else:
                raise Exception('Scanner did not yield process object first')

            scan = Scan.query.filter_by(job_id=job_id).first()
            if scan:
                scan.status = 'running'
                db.session.commit()

            # Now, process the rest of the updates
            for update in scan_generator:
                scan = Scan.query.filter_by(job_id=job_id).first()
                if not scan:
                    print(f"Scan {job_id} not found, aborting background task.")
                    return

                if update['type'] == 'progress':
                    scan.progress = update['value']
                    db.session.commit()
                elif update['type'] == 'result':
                    scan.results = json.dumps(update['value'])
                    scan.status = 'completed'
                    scan.progress = 100
                    db.session.commit()
                    break
                elif update['type'] == 'error':
                    scan.status = 'failed'
                    scan.results = json.dumps({'error': update['value']})
                    db.session.commit()
                    break

        except Exception as e:
            print(f"Error in background scan {job_id}: {e}")
            scan = Scan.query.filter_by(job_id=job_id).first()
            if scan:
                scan.status = 'failed'
                scan.progress = 0 # Reset progress on failure
                scan.results = json.dumps({'error': str(e)})
                db.session.commit()
        finally:
            # Clean up the active_scans dictionary to prevent memory leaks
            if job_id in active_scans:
                del active_scans[job_id]

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint to verify that the server is running."""
    return jsonify({'status': 'ok'}), 200

@app.route('/api/ping', methods=['GET'])
def ping():
    """A simple ping endpoint to check for connectivity from the UI."""
    return jsonify({'status': 'pong'}), 200

@app.route('/api/sync-status', methods=['GET'])
def sync_status():
    """Checks the status of the file synchronizer."""
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    HEARTBEAT_FILE_PATH = os.path.join(BASE_DIR, 'sync_heartbeat.json')
    sync_active_threshold_seconds = 30

    app.logger.info(f"Checking for heartbeat file at: {HEARTBEAT_FILE_PATH}")

    if not os.path.exists(HEARTBEAT_FILE_PATH):
        app.logger.warning("Heartbeat file not found.")
        return jsonify({'status': 'inactive', 'reason': 'Heartbeat file not found.'}), 200

    try:
        with open(HEARTBEAT_FILE_PATH, 'r') as f:
            data = json.load(f)
        
        last_heartbeat_str = data.get('timestamp')
        if not last_heartbeat_str:
            app.logger.warning("Invalid heartbeat format: timestamp not found.")
            return jsonify({'status': 'inactive', 'reason': 'Invalid heartbeat format.'}), 200

        last_heartbeat = datetime.fromisoformat(last_heartbeat_str)
        now = datetime.now(timezone.utc)
        
        if last_heartbeat.tzinfo is None:
            last_heartbeat = last_heartbeat.replace(tzinfo=timezone.utc)

        time_difference = (now - last_heartbeat).total_seconds()

        if time_difference <= sync_active_threshold_seconds:
            app.logger.info(f"Sync is active. Last heartbeat was {time_difference:.0f} seconds ago.")
            return jsonify({'status': 'active'}), 200
        else:
            app.logger.warning(f"Sync is inactive. Heartbeat is stale. Last seen {time_difference:.0f} seconds ago.")
            return jsonify({'status': 'inactive', 'reason': f'Heartbeat is stale. Last seen {time_difference:.0f} seconds ago.'}), 200

    except (json.JSONDecodeError, IOError) as e:
        app.logger.error(f"Error reading heartbeat file: {str(e)}")
        return jsonify({'status': 'error', 'reason': f'Error reading heartbeat file: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'status': 'error', 'reason': str(e)}), 500

@app.route('/api/scans', methods=['POST'])
def start_scan():
    data = request.get_json()
    target = data.get('target')
    tool = data.get('tool', 'nmap')
    scan_type = data.get('scan_type', 'default')
    port = data.get('port')

    if not target:
        return jsonify({'error': 'Target is required'}), 400

    new_scan = Scan(tool=tool, target=target, scan_type=scan_type, status='submitted')
    db.session.add(new_scan)
    db.session.commit()

    # Start the scan in a background thread
    thread = threading.Thread(target=run_scan_in_background, args=(app, new_scan.job_id, tool, target, scan_type, port))
    thread.start()


    return jsonify({'job_id': new_scan.job_id, 'status': 'submitted'}), 202


@app.route('/api/scans', methods=['GET'])
def get_scans():
    scans = Scan.query.order_by(Scan.created_at.desc()).all()
    return jsonify([{
        'job_id': scan.job_id,
        'tool': scan.tool,
        'target': scan.target,
        'scan_type': scan.scan_type,
        'status': scan.status,
        'progress': scan.progress,
        'results': json.loads(scan.results) if scan.results else None,
        'created_at': scan.created_at.isoformat()
    } for scan in scans])

@app.route('/api/scans/<job_id>/stop', methods=['POST'])
def stop_scan(job_id):
    proc = active_scans.get(job_id)
    if not proc:
        return jsonify({'error': 'Scan not found or already completed'}), 404

    try:
        proc.terminate() # Terminate the nmap process
        proc.wait() # Wait for the process to terminate
    except Exception as e:
        return jsonify({'error': f'Failed to stop scan: {str(e)}'}), 500
    finally:
        # Ensure cleanup happens even if termination fails
        if job_id in active_scans:
            del active_scans[job_id]

    scan = Scan.query.filter_by(job_id=job_id).first()
    if scan:
        scan.status = 'stopped'
        db.session.commit()

    return jsonify({'message': 'Scan stopped successfully'}), 200

@app.route('/api/scans/<job_id>', methods=['GET'])
def get_scan_status(job_id):
    scan = Scan.query.filter_by(job_id=job_id).first_or_404()
    
    response = {
        'job_id': scan.job_id,
        'tool': scan.tool,
        'target': scan.target,
        'scan_type': scan.scan_type,
        'status': scan.status,
        'created_at': scan.created_at.isoformat(),
        'results': json.loads(scan.results) if scan.results else None
    }
    return jsonify(response)

@app.route('/api/scans/<job_id>', methods=['DELETE'])
def delete_scan(job_id):
    # If running, stop it first
    if job_id in active_scans:
        stop_scan(job_id)

    scan = Scan.query.filter_by(job_id=job_id).first()
    if not scan:
        return jsonify({'error': 'Scan not found'}), 404

    try:
        db.session.delete(scan)
        db.session.commit()
        return jsonify({'message': 'Scan deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to delete scan: {str(e)}'}), 500


@app.route('/api/system-monitor', methods=['GET'])
def system_monitor():
    target = request.args.get('target', 'localhost')
    
    # Check if target is local
    is_local = target in ['localhost', '127.0.0.1', '0.0.0.0']
    
    data = {
        'cpu': [],
        'memory': [],
        'disk': [],
        'network': []
    }

    if is_local:
        # Local metrics via psutil
        cpu = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory().percent
        disk = psutil.disk_usage('/').percent
        # Network is cumulative, so we'd need delta, for now just returning 0 or generic
        # A real implementation would store valid previous state to calc rate
        
        data['cpu'] = [{'value': cpu, 'timestamp': datetime.now().timestamp() * 1000, 'isSpike': cpu > 80}]
        data['memory'] = [{'value': mem, 'timestamp': datetime.now().timestamp() * 1000, 'isSpike': mem > 80}]
        # ... others
        
        return jsonify(data)
    else:
        # Remote ping
        try:
            latency = ping_host(target, unit='ms')
            if latency is None:
                latency = 0
        except:
            latency = 0
            
        # For remote, we return the latency as "Network" value and simulated others
        # indicating it's agentless
        return jsonify({
            'network': [{'value': latency, 'timestamp': datetime.now().timestamp() * 1000}],
            'is_agentless': True
        })

@app.route('/api/deploy/agent', methods=['POST'])
def deploy_agent():
    data = request.json
    target = data.get('target')
    os_type = data.get('os_type') # linux, windows, mac
    username = data.get('username')
    password = data.get('password')
    agent_name = data.get('agent_name', f"agent-{target}")
    group = data.get('group', 'default')
    
    # My IP (Manager IP) - Try to detect or allow override
    manager_ip = data.get('manager_ip', request.host.split(':')[0])

    if not all([target, os_type, username, password]):
        return jsonify({'error': 'Missing required credentials'}), 400

    if os_type == 'linux':
        result = deployer.deploy_linux(target, username, password, manager_ip, agent_name, group)
    elif os_type == 'windows':
        result = deployer.deploy_windows(target, username, password, manager_ip, agent_name, group)
    elif os_type == 'mac':
        result = deployer.deploy_mac(target, username, password, manager_ip, agent_name, group)
    else:
        return jsonify({'error': 'Invalid OS type'}), 400

    if result['status'] == 'success':
        return jsonify({'message': 'Deployment successful', 'output': result.get('output')})
    else:
        return jsonify({'error': 'Deployment failed', 'details': result}), 500

@app.route('/api/deploy/node', methods=['POST'])
def deploy_node():
    """Deploys a new Backend Node (Docker) on a target server via SSH"""
    data = request.json
    target = data.get('target')
    username = data.get('username')
    password = data.get('password')
    
    if not all([target, username, password]):
        return jsonify({'error': 'Missing credentials'}), 400

    # Command to install docker and run container
    # Simplified: Assuming Docker exists or one-liner install
    # We will upload the docker-compose.yml content
    
    deploy_script = f"""
    if ! command -v docker &> /dev/null; then
        curl -fsSL https://get.docker.com | sh
    fi
    mkdir -p ~/cloudx-backend
    cd ~/cloudx-backend
    # We would actually grab the image from a repo, but for MVP we might need to build/load
    # For now, let's assume we pull from a registry (e.g. docker hub placeholder)
    # OR we just start a hello-world to prove concept
    docker run -d -p 5001:5001 --name cloudx-backend python:3.9-slim python -c "import http.server; http.server.test(Port=5001)"
    """
    
    # Use Paramiko to run this
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(target, username=username, password=password)
        
        stdin, stdout, stderr = ssh.exec_command(deploy_script)
        exit_status = stdout.channel.recv_exit_status()
        out = stdout.read().decode()
        
        ssh.close()
        
        if exit_status == 0:
             return jsonify({'message': 'Node deployed', 'node_url': f'http://{target}:5001'})
        else:
             return jsonify({'error': 'Node deployment failed', 'details': out}), 500
             
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def cleanup_stale_scans():
    # Scans that are 'running' or 'submitted' when the app starts are stale.
    stale_scans = Scan.query.filter(Scan.status.in_(['running', 'submitted'])).all()
    for scan in stale_scans:
        scan.status = 'failed'
        scan.results = json.dumps({'error': 'Scan was interrupted by a server restart.'})
    if stale_scans:
        db.session.commit()
        print(f'Cleaned up {len(stale_scans)} stale scans.')

if __name__ == '__main__':
    with app.app_context():
        db.create_all() # Create database tables if they don't exist
        cleanup_stale_scans()

    # Running on port 5001 to avoid conflict with the frontend's default port 3000
    # Bind to all interfaces to allow external connections
    app.run(host='0.0.0.0', debug=True, port=5001)
