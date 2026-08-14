import base64
import tempfile
import unittest
from pathlib import Path

from deployer import AgentDeployer


class WindowsDeploymentScriptTests(unittest.TestCase):
    def test_user_values_are_encoded_as_data_not_embedded_in_powershell(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            scripts_dir = Path(temporary_directory)
            windows_dir = scripts_dir / "windows"
            windows_dir.mkdir()
            (windows_dir / "cloudx-agent-installer.psm1").write_text(
                "function Install-CloudXAgent {}", encoding="utf-8"
            )
            (windows_dir / "cloudx-agent-setup.ps1").write_text(
                "Write-Output setup", encoding="utf-8"
            )
            (windows_dir / "remove-threat.py").write_text(
                "print('threat')", encoding="utf-8"
            )

            deployer = AgentDeployer(str(scripts_dir))
            captured = {}

            def capture_winrm(host, username, password, ps_script):
                captured.update(
                    host=host,
                    username=username,
                    password=password,
                    ps_script=ps_script,
                )
                return {"status": "success", "output": "ok"}

            deployer._execute_winrm = capture_winrm

            manager_ip = "192.0.2.10"
            agent_name = "agent-01"
            group = "prod-group"
            password = "correct-horse-battery-staple"
            result = deployer.deploy_windows(
                "winhost.example.com",
                "Administrator",
                password,
                manager_ip,
                agent_name,
                group,
            )

            self.assertEqual(result["status"], "success")
            script = captured["ps_script"]
            for raw_value in (manager_ip, agent_name, group, password):
                self.assertNotIn(raw_value, script)

            for value in (manager_ip, agent_name, group):
                encoded = base64.b64encode(value.encode("utf-8")).decode("ascii")
                self.assertIn(encoded, script)

            self.assertIn("-ManagerIP $managerIP", script)
            self.assertIn("-AgentName $agentName", script)
            self.assertIn("-AgentGroup $agentGroup", script)


if __name__ == "__main__":
    unittest.main()
