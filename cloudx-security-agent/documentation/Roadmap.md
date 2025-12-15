# Project Roadmap: Future Enhancements

This document outlines the planned improvements and future features for the NixGuard-Wazuh-Installer project.

## Q3 2025: Cross-Platform Support
- [ ] Develop and test installer scripts for Linux agents (`wazuh-configs/scripts/linux/`).
- [ ] Develop and test installer scripts for macOS agents (`wazuh-configs/scripts/mac/`).
- [ ] Create a unified `ossec.conf` template for cross-platform compatibility.

## Q4 2025: Enhanced Active Response & Telemetry
- [x] Integrate osquery for advanced endpoint telemetry and threat hunting.
- [ ] Develop custom osquery query packs tailored to specific threats (e.g., ransomware, persistence).
- [ ] Correlate osquery results with FIM and log events to create high-fidelity alerts.
- [ ] Add more sophisticated active response scripts for different types of threats.
- [ ] Implement a mechanism for script self-updates from the central repository.
- [ ] Integrate with third-party threat intelligence feeds.
- [ ] Add more sophisticated active response scripts for different types of threats.
- [ ] Implement a mechanism for script self-updates from the central repository.
- [ ] Integrate with third-party threat intelligence feeds.

## Q1 2026: Configuration and Usability
- [ ] Develop a centralized configuration management system (e.g., using JSON or YAML config files).
- [ ] Improve parameter validation and error handling in installer scripts.
- [ ] Create a comprehensive test suite to validate installer and script functionality across all supported platforms.

## Ongoing Improvements
- [ ] Regularly update Wazuh agent version and dependency hashes.
- [ ] Refine and expand the custom rulesets for threat detection.
- [ ] Improve logging and reporting capabilities.
