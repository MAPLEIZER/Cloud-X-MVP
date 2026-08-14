import base64
import logging
import os
import secrets
import shlex

import paramiko
import winrm

from security_utils import is_valid_host, is_valid_identifier

logger = logging.getLogger(__name__)


class AgentDeployer:
    def __init__(self, scripts_dir):
        self.scripts_dir = scripts_dir

    @staticmethod
    def _valid_parameters(target, manager_ip, agent_name, group):
        return (
            is_valid_host(target)
            and is_valid_host(manager_ip)
            and is_valid_identifier(agent_name)
            and is_valid_identifier(group)
        )

    def deploy_linux(
        self, target, username, password, manager_ip, agent_name, group
    ):
        if not self._valid_parameters(target, manager_ip, agent_name, group):
            return {"status": "error", "error": "Invalid deployment parameters."}

        files_to_transfer = [
            (os.path.join(self.scripts_dir, "linux", "cloudx-agent-install.sh"), "cloudx-agent-install.sh"),
            (os.path.join(self.scripts_dir, "linux", "cloudx-agent-setup.sh"), "cloudx-agent-setup.sh"),
            (os.path.join(self.scripts_dir, "linux", "remove-threat.py"), "remove-threat.py"),
            (os.path.join(self.scripts_dir, "linux", "requirements.txt"), "requirements.txt"),
        ]
        return self._execute_ssh_bundle(
            target,
            username,
            password,
            files_to_transfer,
            "cloudx-agent-install.sh",
            manager_ip,
            agent_name,
            group,
        )

    def deploy_windows(
        self, target, username, password, manager_ip, agent_name, group
    ):
        if not self._valid_parameters(target, manager_ip, agent_name, group):
            return {"status": "error", "error": "Invalid deployment parameters."}

        script_path = os.path.join(self.scripts_dir, "windows", "cloudx-agent-installer.psm1")
        cert_path = os.path.join(self.scripts_dir, "windows", "cloudx-code-signing.cer")

        try:
            with open(script_path, "r", encoding="utf-8") as script_file:
                script_content = script_file.read()
            with open(cert_path, "rb") as cert_file:
                cert_content_b64 = base64.b64encode(cert_file.read()).decode("ascii")
        except OSError:
            logger.exception("Required Windows deployment file is missing")
            return {
                "status": "error",
                "message": "Required deployment file is missing on the server.",
            }

        ps_script = f"""
        $ErrorActionPreference = "Stop"

        $certB64 = "{cert_content_b64}"
        $certBytes = [System.Convert]::FromBase64String($certB64)
        $certPath = "$env:TEMP\\cloudx-code-signing.cer"
        [System.IO.File]::WriteAllBytes($certPath, $certBytes)

        Import-Certificate -FilePath $certPath -CertStoreLocation Cert:\\LocalMachine\\Root | Out-Null

        $moduleContent = @'
{script_content}
'@
        $modulePath = "$env:TEMP\\cloudx-agent-installer.psm1"
        $moduleContent | Out-File -FilePath $modulePath -Encoding UTF8

        Import-Module $modulePath -Force
        Install-CloudXAgent -ManagerIP "{manager_ip}" -AgentName "{agent_name}" -AgentGroup "{group}"
        """

        return self._execute_winrm(target, username, password, ps_script)

    def deploy_mac(
        self, target, username, password, manager_ip, agent_name, group
    ):
        if not self._valid_parameters(target, manager_ip, agent_name, group):
            return {"status": "error", "error": "Invalid deployment parameters."}

        files_to_transfer = [
            (os.path.join(self.scripts_dir, "mac", "cloudx-agent-install.sh"), "cloudx-agent-install.sh"),
            (os.path.join(self.scripts_dir, "mac", "cloudx-agent-setup.sh"), "cloudx-agent-setup.sh"),
            (os.path.join(self.scripts_dir, "linux", "remove-threat.py"), "remove-threat.py"),
            (os.path.join(self.scripts_dir, "linux", "requirements.txt"), "requirements.txt"),
        ]
        return self._execute_ssh_bundle(
            target,
            username,
            password,
            files_to_transfer,
            "cloudx-agent-install.sh",
            manager_ip,
            agent_name,
            group,
        )

    def _execute_ssh_bundle(
        self,
        host,
        username,
        password,
        files,
        main_script_name,
        manager_ip,
        agent_name,
        group,
    ):
        if not self._valid_parameters(host, manager_ip, agent_name, group):
            return {"status": "error", "error": "Invalid deployment parameters."}

        remote_dir = f"/tmp/cloudx_deploy_{secrets.token_hex(16)}"
        ssh = None
        sftp = None

        try:
            ssh = paramiko.SSHClient()
            ssh.load_system_host_keys()
            ssh.set_missing_host_key_policy(paramiko.RejectPolicy())
            ssh.connect(
                host,
                username=username,
                password=password,
                timeout=10,
                banner_timeout=10,
                auth_timeout=10,
                look_for_keys=False,
                allow_agent=False,
            )

            sftp = ssh.open_sftp()
            sftp.mkdir(remote_dir, mode=0o700)

            for local_path, remote_name in files:
                if "/" in remote_name or "\\" in remote_name:
                    raise ValueError("Invalid deployment filename")

                remote_path = f"{remote_dir}/{remote_name}"
                sftp.put(local_path, remote_path)
                mode = 0o700 if remote_name.endswith((".sh", ".py")) else 0o600
                sftp.chmod(remote_path, mode)

            sftp.close()
            sftp = None

            command_parts = [
                f"cd {shlex.quote(remote_dir)}",
                (
                    "sudo -- "
                    f"./{shlex.quote(main_script_name)} "
                    f"{shlex.quote(manager_ip)} "
                    f"{shlex.quote(agent_name)} "
                    f"{shlex.quote(group)}"
                ),
            ]
            command = " && ".join(command_parts)

            stdin, stdout, stderr = ssh.exec_command(
                command,
                get_pty=True,
                timeout=180,
            )

            if password:
                stdin.write(password + "\n")
                stdin.flush()

            exit_status = stdout.channel.recv_exit_status()
            out = stdout.read().decode(errors="replace").strip()
            err = stderr.read().decode(errors="replace").strip()

            if exit_status == 0:
                return {"status": "success", "output": out}

            logger.warning(
                "Agent deployment failed on %s with status %s: stdout=%r stderr=%r",
                host,
                exit_status,
                out[-1000:],
                err[-1000:],
            )
            return {
                "status": "error",
                "error": "Remote installer returned a non-zero status.",
            }

        except Exception:
            logger.exception("Exception during SSH bundle deployment")
            return {
                "status": "error",
                "error": "An internal error occurred during agent deployment.",
            }
        finally:
            if sftp is not None:
                try:
                    sftp.close()
                except Exception:
                    logger.debug("Failed to close SFTP session", exc_info=True)

            if ssh is not None:
                try:
                    ssh.exec_command(
                        f"rm -rf -- {shlex.quote(remote_dir)}",
                        timeout=10,
                    )
                except Exception:
                    logger.debug(
                        "Failed to clean remote deployment directory",
                        exc_info=True,
                    )
                ssh.close()

    def _execute_winrm(self, host, username, password, ps_script):
        if not is_valid_host(host):
            return {"status": "error", "error": "Invalid deployment host."}

        try:
            session = winrm.Session(
                host,
                auth=(username, password),
                transport="ntlm",
            )
            result = session.run_ps(ps_script)

            if result.status_code == 0:
                return {
                    "status": "success",
                    "output": result.std_out.decode(errors="replace"),
                }

            logger.warning(
                "WinRM deployment failed on %s: %r",
                host,
                result.std_err.decode(errors="replace")[-1000:],
            )
            return {
                "status": "error",
                "error": "Remote PowerShell returned a non-zero status.",
            }
        except Exception:
            logger.exception("Exception during WinRM execution")
            return {
                "status": "error",
                "error": "An internal error occurred during agent deployment.",
            }
