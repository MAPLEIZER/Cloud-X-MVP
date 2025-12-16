
import logging
import os
import time

import paramiko
import winrm

logger = logging.getLogger(__name__)

class AgentDeployer:
    def __init__(self, scripts_dir):
        self.scripts_dir = scripts_dir


    def deploy_linux(self, target, username, password, manager_ip, agent_name, group):
        files_to_transfer = [
            (os.path.join(self.scripts_dir, 'linux', 'cloudx-agent-install.sh'), 'cloudx-agent-install.sh'),
            (os.path.join(self.scripts_dir, 'linux', 'cloudx-agent-setup.sh'), 'cloudx-agent-setup.sh'),
            (os.path.join(self.scripts_dir, 'linux', 'remove-threat.py'), 'remove-threat.py'),
            (os.path.join(self.scripts_dir, 'linux', 'requirements.txt'), 'requirements.txt')
        ]
        return self._execute_ssh_bundle(target, username, password, files_to_transfer, 'cloudx-agent-install.sh', manager_ip, agent_name, group)

    def deploy_windows(self, target, username, password, manager_ip, agent_name, group):
        script_path = os.path.join(self.scripts_dir, 'windows', 'cloudx-agent-installer.psm1')
        cert_path = os.path.join(self.scripts_dir, 'windows', 'cloudx-code-signing.cer')
        
        # We need to construct a PowerShell command that loads this module and runs Install-CloudXAgent
        # Since we are using WinRM/SSH, we can transfer the file or paste content.
        # Transferring is safer for large files.
        
        try:
            with open(script_path, 'r') as f:
                script_content = f.read()
                
            # Read certificate content to embed
            import base64
            with open(cert_path, 'rb') as f:
                cert_content_b64 = base64.b64encode(f.read()).decode('utf-8')

        except FileNotFoundError as e:
            logger.exception("File not found during deploy_windows")
            return {'status': 'error', 'error': 'An internal error occurred during agent deployment.'}

        # ... (WinRM logic implementation details omitted for MVP brevity, assuming existing logic)
        # In a real impl, we would use pywinrm to copy the script and execute:
        # Import-Module .\cloudx-agent-installer.psm1
        # Install-CloudXAgent -ManagerIP ...
        
        # Using a simplified command construction for the example:
        # We'll use a wrapper script or just encode the command.
        
        # For this mock/MVP, let's assume we copy the content to a temp file on target and run it.
        
        ps_script = f"""
        # 1. Install Code Signing Certificate
        $certB64 = "{cert_content_b64}"
        $certBytes = [System.Convert]::FromBase64String($certB64)
        $certPath = "$env:TEMP\\cloudx-code-signing.cer"
        [System.IO.File]::WriteAllBytes($certPath, $certBytes)
        
        try {{
            Import-Certificate -FilePath $certPath -CertStoreLocation Cert:\\LocalMachine\\Root
            Write-Host "Certificate installed successfully."
        }} catch {{
            Write-Warning "Failed to install certificate: $_"
        }}

        # 2. Deploy and Run Agent Installer
        $env:TEMP\\cloudx-agent-installer.psm1
        $moduleContent = @'
{script_content}
'@
        $moduleContent | Out-File -FilePath "$env:TEMP\\cloudx-agent-installer.psm1" -Encoding UTF8
        
        # Import-Module should now work if "AllSigned" or "RemoteSigned" is enforced
        Import-Module "$env:TEMP\\cloudx-agent-installer.psm1" -Force
        Install-CloudXAgent -ManagerIP "{manager_ip}" -AgentName "{agent_name}" -AgentGroup "{group}"
        """
        
        # ... Execute via WinRM ...
        return self._execute_winrm(target, username, password, ps_script)

    def deploy_mac(self, target, username, password, manager_ip, agent_name, group):
        # reuse linux python scripts for mac if they are compatible, or expect them in mac dir
        # Assuming we will copy them to mac dir or reference linux dir for shared files.
        # For simplicity, I will reference them from linux dir for shared ones if missing in mac, 
        # but let's assume I will populate the mac dir.
        files_to_transfer = [
            (os.path.join(self.scripts_dir, 'mac', 'cloudx-agent-install.sh'), 'cloudx-agent-install.sh'),
            (os.path.join(self.scripts_dir, 'mac', 'cloudx-agent-setup.sh'), 'cloudx-agent-setup.sh'),
            (os.path.join(self.scripts_dir, 'linux', 'remove-threat.py'), 'remove-threat.py'), # Shared
            (os.path.join(self.scripts_dir, 'linux', 'requirements.txt'), 'requirements.txt')  # Shared
        ]
        return self._execute_ssh_bundle(target, username, password, files_to_transfer, 'cloudx-agent-install.sh', manager_ip, agent_name, group)

    # Helper method for SSH script execution (assuming it will be added elsewhere or is implicit)
    def _execute_ssh_bundle(self, host, username, password, files, main_script_name, manager_ip, agent_name, group):
        remote_dir = f'/tmp/cloudx_deploy_{int(time.time())}'
        
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.RejectPolicy())
            ssh.connect(host, username=username, password=password)

            sftp = ssh.open_sftp()
            try:
                sftp.mkdir(remote_dir)
            except IOError:
                pass # Directory might exist

            # Upload all files
            for local_path, remote_name in files:
                remote_path = f"{remote_dir}/{remote_name}"
                sftp.put(local_path, remote_path)
                sftp.chmod(remote_path, 0o755) # Make everything executable/readable

            sftp.close()

            # Run the main script
            # Note: We cd to the directory so relative paths in script work
            cmd = f"cd {remote_dir} && sudo ./{main_script_name} {manager_ip} {agent_name} {group}"
            
            stdin, stdout, stderr = ssh.exec_command(cmd, get_pty=True) # get_pty for sudo if needed, though we use -S usually
            
            if password:
                stdin.write(password + '\n')
                stdin.flush()

            exit_status = stdout.channel.recv_exit_status()
            out = stdout.read().decode().strip()
            err = stderr.read().decode().strip()
            
            # Cleanup
            ssh.exec_command(f"sudo rm -rf {remote_dir}")
            
            ssh.close()

            if exit_status == 0:
                return {'status': 'success', 'output': out}
            else:
                return {'status': 'error', 'output': out, 'error': err}

        except Exception as e:
            logger.exception("Exception during SSH bundle deployment")
            return {'status': 'error', 'error': 'An internal error occurred during agent deployment.'}

    # Helper method for WinRM script execution (assuming it will be added elsewhere or is implicit)
    def _execute_winrm(self, host, username, password, ps_script):
        try:
            session = winrm.Session(host, auth=(username, password), transport='ntlm')
            result = session.run_ps(ps_script)
            
            if result.status_code == 0:
                return {'status': 'success', 'output': result.std_out.decode()}
            else:
                return {'status': 'error', 'error': result.std_err.decode(), 'output': result.std_out.decode()}

        except Exception:
            logger.exception("Exception during WinRM execution")
            return {'status': 'error', 'error': 'An internal error occurred during agent deployment.'}
