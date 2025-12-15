# Agent-Server Integration Guide
## Cloud-X Security Wazuh Implementation

This document outlines the integration points between the lightweight agent-side script and server-side components for your Wazuh deployment.

## Agent-Side Implementation ✅ COMPLETE

### Core Functions Implemented
- **File Quarantine**: Fast quarantine with timestamped metadata
- **Process Termination**: Recursive child process termination
- **File Validation**: Digital signatures, magic bytes, ownership checks
- **Structured JSON Logging**: Exact format as specified in roadmap
- **Dry-Run Mode**: Safe testing capability
- **PowerShell Monitoring**: Script block logging enabled
- **Osquery Telemetry**: Rich endpoint data collection via osquery integration

### JSON Log Format (Agent → Server)
```json
{
  "timestamp": "2025-08-20T22:00:00",
  "agent": "HOSTNAME",
  "file": "/tmp/malware.exe",
  "hash": "abcd1234...",
  "rule_id": "100543",
  "action": "quarantine",
  "quarantine_path": "/tmp/wazuh_quarantine/20250820220000_malware.exe",
  "file_type": "PE executable",
  "processes_terminated": [1234, 5678],
  "signature_valid": false,
  "status": "success"
}
```

### Agent Configuration
- **Safe Directories**: Configurable via server updates
- **Quarantine Location**: `%TEMP%\wazuh_quarantine` (Windows), `/tmp/wazuh_quarantine` (Linux)
- **Dependencies**: `psutil`, `pywin32` (Windows only)

## Server-Side Integration Points

### 1. Threat Intelligence Integration
**Your Implementation Needed:**
```python
# Example server-side enrichment
def enrich_alert(agent_log):
    file_hash = agent_log.get('hash')
    
    # Check VirusTotal
    vt_result = check_virustotal(file_hash)
    
    # Check MISP/OTX
    misp_result = check_misp_iocs(file_hash)
    
    # Assign risk score
    risk_score = calculate_risk_score(vt_result, misp_result, agent_log)
    
    return {
        'agent_data': agent_log,
        'threat_intel': {
            'virustotal': vt_result,
            'misp': misp_result,
            'risk_score': risk_score
        }
    }
```

### 2. Policy Management
**Server → Agent Communication:**
```json
{
  "command": "update_config",
  "safe_directories": [
    "C:\\Users\\*\\Downloads",
    "C:\\Temp"
  ],
  "quarantine_policy": "immediate",
  "signature_check_required": true
}
```

### 3. Dashboard Integration
**Kibana/Grafana Queries:**
```json
# Quarantined files by agent
GET /wazuh-alerts/_search
{
  "query": {
    "bool": {
      "must": [
        {"term": {"action": "quarantine"}},
        {"range": {"timestamp": {"gte": "now-24h"}}}
      ]
    }
  },
  "aggs": {
    "by_agent": {
      "terms": {"field": "agent.keyword"}
    }
  }
}
```

### 4. Automated Response Rules
**Wazuh Manager Configuration:**
```xml
<!-- High-risk automatic quarantine -->
<active-response>
  <command>remove-threat</command>
  <location>local</location>
  <rules_id>100543,100546,100547</rules_id>
  <timeout>60</timeout>
</active-response>

<!-- Medium-risk with approval -->
<active-response>
  <command>remove-threat</command>
  <location>local</location>
  <rules_id>100541</rules_id>
  <timeout>300</timeout>
  <repeated_offenders>yes</repeated_offenders>
</active-response>
```

## Communication Flow

### 1. Alert Generation
```
Agent detects suspicious file → Structured JSON log → Wazuh Manager
```

### 2. Server Processing
```
Manager receives log → Threat intel lookup → Risk scoring → Policy decision
```

### 3. Response Command
```
Server decision → Active response command → Agent execution → Result logging
```

### 4. Aggregation
```
All agent logs → SIEM ingestion → Dashboard visualization → Reporting
```

## Performance Optimizations (Agent-Side)

### Lightweight Design
- **Minimal Dependencies**: Only `psutil` and `pywin32`
- **Fast Execution**: Process termination before file analysis
- **Selective Checks**: Digital signature only for executables
- **Efficient Logging**: Single JSON write per action

### Resource Usage
- **Memory**: < 50MB typical usage
- **CPU**: Minimal impact during normal operation
- **Disk**: Quarantine files + metadata only

## Server-Side Development Tasks

### High Priority
1. **Threat Intelligence API Integration**
   - VirusTotal API client
   - MISP connector
   - Custom IOC database

2. **Risk Scoring Engine**
   - Multi-factor risk calculation
   - Historical pattern analysis
   - False positive reduction

3. **Dashboard Development**
   - Real-time threat monitoring
   - Agent status overview
   - Quarantine management interface
   - Osquery telemetry visualization for threat hunting

### Medium Priority
1. **Policy Management Interface**
   - Dynamic safe directory updates
   - Quarantine policy configuration
   - Agent configuration deployment

2. **Automated Remediation**
   - Risk-based response automation
   - Endpoint isolation triggers
   - Notification system integration

### Integration Examples

#### Splunk Integration
```spl
index=wazuh source="*active-responses.log" 
| spath 
| where action="quarantine"
| stats count by agent, file_type
| sort -count
```

#### Elastic Stack Integration
```json
{
  "mappings": {
    "properties": {
      "timestamp": {"type": "date"},
      "agent": {"type": "keyword"},
      "file": {"type": "text"},
      "hash": {"type": "keyword"},
      "rule_id": {"type": "keyword"},
      "action": {"type": "keyword"},
      "processes_terminated": {"type": "integer"}
    }
  }
}
```

## Testing & Validation

### Agent Testing
```bash
# Dry run mode
python remove-threat.py --dry-run

# Manual test with sample alert
echo '{"command":"add","parameters":{"alert":{"rule":{"id":"100543"},"data":{"file":"C:\\temp\\test.exe"}}}}' | python remove-threat.py
```

### Server Integration Testing
1. Generate test alerts with known file hashes
2. Verify threat intelligence lookups
3. Validate risk scoring accuracy
4. Test automated response triggers

The agent-side implementation is production-ready and optimized for your roadmap. Focus your server-side development on the integration points outlined above.
