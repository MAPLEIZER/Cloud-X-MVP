feat(windows): Add Sysmon installation and advanced log collection

This commit enhances the Windows agent's capabilities by automating the installation of Sysmon and enabling the collection of critical security event logs.

Key additions:

- **Automated Sysmon Deployment**:
  - The `post-install-setup.ps1` script now downloads and installs Sysmon using the widely-trusted SwiftOnSecurity configuration. This provides deep visibility into process creation, network connections, and other system activities.

- **Advanced Windows Auditing**:
  - The setup script now enables advanced audit policies (`auditpol`) for Object Access, Process Creation, and Logon events. This ensures that detailed "who did what" information is logged.

- **Expanded Log Collection**:
  - The `agent.conf` is now configured to collect logs from essential Windows event channels:
    - `Security`
    - `Microsoft-Windows-PowerShell/Operational`
    - `Microsoft-Windows-PowerShell/Analytic`
    - `Microsoft-Windows-Sysmon/Operational`

These changes significantly improve the agent's threat detection and forensic capabilities by providing a much richer stream of security data to the Wazuh manager.

---

### feat(agent): harden windows agent configuration

This commit hardens the Windows agent configuration by enabling `whodata` for critical system directories, adding the Security Configuration Assessment (SCA) module, implementing noise reduction with targeted ignores, hardening active response with timeouts, and enabling the client buffer for offline resilience. These changes collectively enhance visibility, reduce false positives, and improve agent stability.

---

### feat(agent): integrate osquery for advanced telemetry

This commit integrates osquery into the Windows agent configuration to provide deep endpoint telemetry for advanced threat hunting and compliance monitoring.

- **Agent Configuration (`agent.conf`)**: Enabled the `osquery` wodle to run the osquery daemon and collect logs.
- **Documentation Updates**:
  - Updated `README.md` and `Post-Install.md` to include osquery in the list of features.
  - Updated `Agent-Server-Integration.md` to reflect osquery as a new data source.
  - Updated `Roadmap.md` to mark osquery integration as complete and outline future work, such as creating custom query packs.
