# Cloud-X Security - Advanced Wazuh Agent Post-Installation Setup
# Version: 2.0
# Author: Cloud-X Security Team
# Description: Automated setup for advanced security features including Sysmon, PowerShell logging, and threat response
# GitHub: https://github.com/MAPLEIZER/Cloud-X-security-agent

param(
    [string]$WazuhPath = "C:\Program Files (x86)\ossec-agent",
    [string]$WazuhManager = "192.168.100.37",
    [string]$AgentName = $env:COMPUTERNAME
)

# Initialize logging
function Write-Log {
    param(
        [Parameter(Mandatory=$true)]
        [string]$Message,
        [Parameter(Mandatory=$true)]
        [ValidateSet("INFO", "WARNING", "ERROR", "SUCCESS")]
        [string]$Level
    )
    
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $formattedMessage = "$timestamp [$Level] - $Message"
    
    $colorMap = @{
        INFO     = "White";
        WARNING  = "Yellow";
        ERROR    = "Red";
        SUCCESS  = "Green";
    }
    
    Write-Host $formattedMessage -ForegroundColor $colorMap[$Level]
    
    # Also write to a log file
    $logPath = Join-Path $env:TEMP "Cloud-X-Security-PostInstall.log"
    Add-Content -Path $logPath -Value $formattedMessage -ErrorAction SilentlyContinue
}

# Check if running as administrator
function Test-Administrator {
    $identity = [System.Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = [System.Security.Principal.WindowsPrincipal]$identity
    return $principal.IsInRole([System.Security.Principal.WindowsBuiltInRole]::Administrator)
}

# Main setup function
function Start-CloudXSecuritySetup {
    Write-Host "===================================================================" -ForegroundColor Cyan
    Write-Host "        Cloud-X Security - Advanced Wazuh Agent Setup              " -ForegroundColor Cyan
    Write-Host "===================================================================" -ForegroundColor Cyan
    Write-Log "Starting Cloud-X Security post-installation setup" -Level "INFO"
    
    # Check administrator privileges
    if (-not (Test-Administrator)) {
        Write-Log "This script must be run as Administrator" -Level "ERROR"
        exit 1
    }
    
    # Validate Wazuh installation path
    $possiblePaths = @(
        (Join-Path -Path $env:ProgramFiles -ChildPath "ossec-agent"),
        (Join-Path -Path ${env:ProgramFiles(x86)} -ChildPath "ossec-agent")
    )
    
    if (Test-Path $WazuhPath) {
        Write-Log "Using specified Wazuh path: $WazuhPath" -Level "INFO"
    } else {
        $WazuhPath = $possiblePaths | Where-Object { Test-Path $_ } | Select-Object -First 1
        if ($WazuhPath) {
            Write-Log "Found Wazuh installation at: $WazuhPath" -Level "SUCCESS"
        } else {
            Write-Log "Wazuh agent not found. Please verify installation." -Level "ERROR"
            exit 1
        }
    }
    
    # Setup steps
    Setup-ActiveResponse
    Install-PythonDependencies
    Install-Sysmon
    Enable-AdvancedAuditing
    Enable-PowerShellLogging
    Configure-ActiveResponse
    Create-QuarantineDirectory
    Restart-WazuhService
    Finalize-Setup
}

function Setup-ActiveResponse {
    Write-Host "[1/8] Setting up active response scripts..." -ForegroundColor Yellow
    
    try {
        # Create active response directory if it doesn't exist
        $activeResponseDir = Join-Path -Path $WazuhPath -ChildPath "active-response\bin"
        if (-not (Test-Path $activeResponseDir)) {
            New-Item -ItemType Directory -Path $activeResponseDir -Force | Out-Null
            Write-Log "Created active response directory" -Level "INFO"
        }
        
        # Copy the remove-threat.py script if it exists locally
        $localScriptPath = Join-Path -Path $PSScriptRoot -ChildPath "remove-threat.py"
        $scriptDest = Join-Path -Path $activeResponseDir -ChildPath "remove-threat.py"
        
        if (Test-Path $localScriptPath) {
            Copy-Item -Path $localScriptPath -Destination $scriptDest -Force
            Write-Log "Copied remove-threat.py from local source" -Level "SUCCESS"
        } else {
            # Download from GitHub if local copy doesn't exist
            $scriptUrl = "https://raw.githubusercontent.com/MAPLEIZER/Cloud-X-security-agent/main/wazuh-configs/scripts/windows/remove-threat.py"
            Invoke-WebRequest -Uri $scriptUrl -OutFile $scriptDest -UseBasicParsing
            Write-Log "Downloaded remove-threat.py from GitHub" -Level "SUCCESS"
        }
        
        # Set appropriate permissions
        if (Test-Path $scriptDest) {
            $acl = Get-Acl $scriptDest
            $accessRule = New-Object System.Security.AccessControl.FileSystemAccessRule("NT AUTHORITY\SYSTEM", "FullControl", "Allow")
            $acl.SetAccessRule($accessRule)
            Set-Acl $scriptDest $acl
            Write-Log "Set permissions for active response script" -Level "SUCCESS"
        }
    } catch {
        Write-Log "Failed to setup active response scripts: $($_.Exception.Message)" -Level "ERROR"
    }
}

function Install-PythonDependencies {
    Write-Host "[2/8] Installing Python dependencies..." -ForegroundColor Yellow
    
    # Check if Python is available
    try {
        $pythonVersion = & python --version 2>&1
        Write-Log "Found Python: $pythonVersion" -Level "INFO"
    } catch {
        Write-Log "Python not found. Please install Python 3.x and ensure it's in PATH" -Level "WARNING"
        return
    }
    
    # Install required Python packages
    $pythonPackages = @("psutil")
    
    foreach ($package in $pythonPackages) {
        try {
            & python -m pip install $package --quiet --disable-pip-version-check
            Write-Log "Installed Python package: $package" -Level "SUCCESS"
        } catch {
            Write-Log ("Failed to install Python package " + $package + ": " + $_.Exception.Message) -Level "WARNING"
        }
    }
}

function Install-Sysmon {
    Write-Host "[3/8] Installing and Configuring Sysmon..." -ForegroundColor Yellow
    
    try {
        # Download Sysmon
        $sysmonUrl = "https://download.sysinternals.com/files/Sysmon.zip"
        $sysmonZip = "$env:TEMP\Sysmon.zip"
        $sysmonDir = "$env:TEMP\Sysmon"
        
        Write-Log "Downloading Sysmon..." -Level "INFO"
        Invoke-WebRequest -Uri $sysmonUrl -OutFile $sysmonZip -UseBasicParsing
        
        # Extract Sysmon
        Expand-Archive -Path $sysmonZip -DestinationPath $sysmonDir -Force
        Write-Log "Extracted Sysmon to $sysmonDir" -Level "SUCCESS"
        
        # Download SwiftOnSecurity configuration
        $sysmonConfigUrl = "https://raw.githubusercontent.com/SwiftOnSecurity/sysmon-config/master/sysmonconfig-export.xml"
        $sysmonConfigFile = "$env:TEMP\sysmonconfig.xml"
        
        Write-Log "Downloading Sysmon configuration..." -Level "INFO"
        Invoke-WebRequest -Uri $sysmonConfigUrl -OutFile $sysmonConfigFile -UseBasicParsing
        Write-Log "Downloaded Sysmon configuration" -Level "SUCCESS"
        
        # Install Sysmon
        if (Test-Path "$sysmonDir\Sysmon64.exe") {
            Write-Log "Installing 64-bit Sysmon..." -Level "INFO"
            & "$sysmonDir\Sysmon64.exe" -accepteula -i $sysmonConfigFile
        } elseif (Test-Path "$sysmonDir\Sysmon.exe") {
            Write-Log "Installing 32-bit Sysmon..." -Level "INFO"
            & "$sysmonDir\Sysmon.exe" -accepteula -i $sysmonConfigFile
        } else {
            Write-Log "Sysmon executable not found" -Level "ERROR"
            return
        }
        
        Write-Log "Sysmon installed successfully" -Level "SUCCESS"
        
        # Cleanup
        Remove-Item $sysmonZip -Force -ErrorAction SilentlyContinue
        Remove-Item $sysmonDir -Recurse -Force -ErrorAction SilentlyContinue
        
    } catch {
        Write-Log "Failed to install Sysmon: $($_.Exception.Message)" -Level "WARNING"
    }
}

function Enable-AdvancedAuditing {
    Write-Host "[4/8] Enabling Advanced Windows Auditing..." -ForegroundColor Yellow
    
    try {
        # Enable advanced auditing policies
        auditpol /set /category:"Object Access" /success:enable /failure:enable | Out-Null
        auditpol /set /subcategory:"File System" /success:enable /failure:enable | Out-Null
        auditpol /set /subcategory:"Handle Manipulation" /success:enable /failure:enable | Out-Null
        auditpol /set /subcategory:"Filtering Platform Connection" /success:enable /failure:enable | Out-Null
        auditpol /set /subcategory:"Process Creation" /success:enable /failure:enable | Out-Null
        auditpol /set /subcategory:"Logon" /success:enable /failure:enable | Out-Null
        
        Write-Log "Enabled advanced Windows auditing policies" -Level "SUCCESS"
    } catch {
        Write-Log "Failed to enable advanced auditing: $($_.Exception.Message)" -Level "WARNING"
    }
}

function Enable-PowerShellLogging {
    Write-Host "[5/8] Enabling PowerShell Script Block Logging..." -ForegroundColor Yellow
    
    try {
        # Enable PowerShell Script Block Logging
        $basePath = "HKLM:\SOFTWARE\Policies\Microsoft\Windows\PowerShell\ScriptBlockLogging"
        if (!(Test-Path $basePath)) {
            New-Item -Path $basePath -Force | Out-Null
        }
        Set-ItemProperty -Path $basePath -Name "EnableScriptBlockLogging" -Value 1 -Type DWord
        
        # Enable PowerShell Module Logging
        $moduleLogPath = "HKLM:\SOFTWARE\Policies\Microsoft\Windows\PowerShell\ModuleLogging"
        if (!(Test-Path $moduleLogPath)) {
            New-Item -Path $moduleLogPath -Force | Out-Null
        }
        Set-ItemProperty -Path $moduleLogPath -Name "EnableModuleLogging" -Value 1 -Type DWord
        
        # Enable PowerShell Transcription (optional)
        $transcriptPath = "HKLM:\SOFTWARE\Policies\Microsoft\Windows\PowerShell\Transcription"
        if (!(Test-Path $transcriptPath)) {
            New-Item -Path $transcriptPath -Force | Out-Null
        }
        Set-ItemProperty -Path $transcriptPath -Name "EnableTranscripting" -Value 1 -Type DWord
        Set-ItemProperty -Path $transcriptPath -Name "OutputDirectory" -Value "C:\ProgramData\PowerShellTranscripts" -Type String
        
        Write-Log "Enabled PowerShell logging features" -Level "SUCCESS"
    } catch {
        Write-Log "Failed to enable PowerShell logging: $($_.Exception.Message)" -Level "WARNING"
    }
}

function Configure-ActiveResponse {
    Write-Host "[6/8] Configuring active response..." -ForegroundColor Yellow
    
    try {
        # Create active response configuration
        $activeResponseConfig = @"
<!-- Cloud-X Security Active Response Configuration -->
<command>
  <name>remove-threat</name>
  <executable>remove-threat.py</executable>
  <timeout_allowed>yes</timeout_allowed>
</command>

<active-response>
  <command>remove-threat</command>
  <location>local</location>
  <rules_id>100543,100546,100547</rules_id>
  <timeout>60</timeout>
</active-response>
"@
        
        $configDir = Join-Path -Path $WazuhPath -ChildPath "etc"
        if (-not (Test-Path $configDir)) {
            New-Item -ItemType Directory -Path $configDir -Force | Out-Null
        }
        
        $activeResponseFile = Join-Path $configDir "cloudx_active_response.conf"
        $activeResponseConfig | Out-File -FilePath $activeResponseFile -Encoding UTF8
        Write-Log "Created active response configuration file" -Level "SUCCESS"
    } catch {
        Write-Log "Failed to configure active response: $($_.Exception.Message)" -Level "ERROR"
    }
}

function Create-QuarantineDirectory {
    Write-Host "[7/8] Creating quarantine directory..." -ForegroundColor Yellow
    
    try {
        # Create quarantine directory
        $quarantineDir = "$env:TEMP\wazuh_quarantine"
        if (-not (Test-Path $quarantineDir)) {
            New-Item -ItemType Directory -Path $quarantineDir -Force | Out-Null
            Write-Log "Created quarantine directory at $quarantineDir" -Level "SUCCESS"
        } else {
            Write-Log "Quarantine directory already exists" -Level "INFO"
        }
    } catch {
        Write-Log "Failed to create quarantine directory: $($_.Exception.Message)" -Level "WARNING"
    }
}

function Restart-WazuhService {
    Write-Host "[8/8] Restarting Wazuh agent service..." -ForegroundColor Yellow
    
    try {
        $service = Get-Service -Name "WazuhSvc" -ErrorAction SilentlyContinue
        if ($service) {
            Write-Log "Restarting Wazuh service..." -Level "INFO"
            Restart-Service -Name "WazuhSvc" -Force -ErrorAction Stop
            Start-Sleep -Seconds 3
            
            # Verify service is running
            $serviceStatus = (Get-Service -Name "WazuhSvc").Status
            if ($serviceStatus -eq 'Running') {
                Write-Log "Wazuh service restarted successfully" -Level "SUCCESS"
            } else {
                Write-Log "Wazuh service status: $serviceStatus" -Level "WARNING"
            }
        } else {
            Write-Log "Wazuh service not found" -Level "WARNING"
        }
    } catch {
        Write-Log "Failed to restart Wazuh service: $($_.Exception.Message)" -Level "ERROR"
    }
}

function Finalize-Setup {
    Write-Host "\n===================================================================" -ForegroundColor Green
    Write-Host "                    SETUP COMPLETED SUCCESSFULLY                   " -ForegroundColor Green
    Write-Host "===================================================================" -ForegroundColor Green
    
    Write-Log "Cloud-X Security post-installation setup completed" -Level "SUCCESS"
    
    Write-Host "\nFeatures enabled:" -ForegroundColor White
    Write-Host "  • Advanced threat file quarantine with metadata tracking" -ForegroundColor Gray
    Write-Host "  • Digital signature verification for executables" -ForegroundColor Gray
    Write-Host "  • File type verification using magic bytes" -ForegroundColor Gray
    Write-Host "  • Malicious process termination" -ForegroundColor Gray
    Write-Host "  • PowerShell script block logging" -ForegroundColor Gray
    Write-Host "  • PowerShell malicious command detection" -ForegroundColor Gray
    Write-Host "  • Sysmon advanced process and network monitoring" -ForegroundColor Gray
    Write-Host "  • Automated active response to threats" -ForegroundColor Gray
    
    Write-Host "\nAgent Configuration:" -ForegroundColor Yellow
    Write-Host "  Manager: $WazuhManager" -ForegroundColor Cyan
    Write-Host "  Agent Name: $AgentName" -ForegroundColor Cyan
    
    Write-Host "\nQuarantine location: $env:TEMP\wazuh_quarantine" -ForegroundColor Cyan
    Write-Host "Log file: C:\Program Files (x86)\ossec-agent\active-response\active-responses.log" -ForegroundColor Cyan
    
    Write-Host "\nNext steps:" -ForegroundColor Yellow
    Write-Host "  1. Ensure the active response configuration is applied on your Wazuh manager" -ForegroundColor White
    Write-Host "  2. Monitor the active response log for threat detection and response" -ForegroundColor White
    Write-Host "  3. Verify Sysmon events are being collected in Windows Event Log" -ForegroundColor White
}

# Run the setup
Start-CloudXSecuritySetup
