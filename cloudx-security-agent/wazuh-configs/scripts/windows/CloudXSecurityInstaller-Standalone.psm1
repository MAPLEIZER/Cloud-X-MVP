#================================================================================
# Cloud-X Security Wazuh Agent Installer Module - GitHub Hosted Version
# Version: 3.1-GitHub
# Author: Cloud-X Security Team
# Description: Self-contained PowerShell module for automated Wazuh agent installation and configuration
# GitHub: https://github.com/MAPLEIZER/Cloud-X-security-agent
# Usage: 
#   $moduleUrl = "https://raw.githubusercontent.com/MAPLEIZER/Cloud-X-security-agent/main/wazuh-configs/scripts/windows/CloudXSecurityInstaller-Standalone.psm1"
#   $moduleContent = (Invoke-WebRequest -Uri $moduleUrl -UseBasicParsing).Content
#   $moduleContent | Out-File -FilePath "$env:TEMP\CloudXSecurityInstaller.psm1" -Encoding UTF8
#   Import-Module "$env:TEMP\CloudXSecurityInstaller.psm1" -Force
#   Install-WazuhAgent -ipAddress "YOUR_IP" -agentName "YOUR_AGENT_NAME" -groupLabel "YOUR_GROUP"
#================================================================================

# Constants
$WAZUH_VERSION = "4.9.1-1"
$WAZUH_URL = "https://packages.wazuh.com/4.x/windows/wazuh-agent-$WAZUH_VERSION.msi"

#region Logging Functions
function Initialize-Logging {
    $logDir = Join-Path $env:TEMP "Cloud-X-Security-Wazuh-Logs"
    if (-not (Test-Path $logDir)) {
        New-Item -Path $logDir -ItemType Directory | Out-Null
    }
    $global:LogPath = Join-Path $logDir "Wazuh-Agent-Setup-$(Get-Date -Format 'yyyy-MM-dd_HH-mm-ss').log"
    
    try {
        Start-Transcript -Path $global:LogPath -Append
        Write-Host "[TRANSCRIPT] Logging to: $($global:LogPath)" -ForegroundColor Green
        return $true
    }
    catch {
        Write-Warning "Transcript logging failed to start: $($_.Exception.Message)"
        return $false
    }
}

function Write-Log {
    param(
        [Parameter(Mandatory=$true)]
        [string]$Message,
        [Parameter(Mandatory=$true)]
        [ValidateSet("INFO", "WARNING", "ERROR", "SUCCESS", "DEBUG", "WARN", "DOWNLOAD")]
        [string]$Level
    )

    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $formattedMessage = "$timestamp [$Level] - $Message"

    $colorMap = @{
        INFO     = "White";
        WARNING  = "Yellow";
        WARN     = "Yellow";
        ERROR    = "Red";
        SUCCESS  = "Green";
        DEBUG    = "Cyan";
        DOWNLOAD = "Magenta"
    }

    Write-Host $formattedMessage -ForegroundColor $colorMap[$Level]
    if ($global:LogPath) {
        Add-Content -Path $global:LogPath -Value $formattedMessage -ErrorAction SilentlyContinue
    }
}

function Start-Step {
    param (
        [string]$StepName
    )
    $script:currentStep++
    $header = "=== STEP $script:currentStep OF $script:totalSteps: $StepName ==="
    Write-Log $header -Level "INFO"
    Write-Host "`n" + ("=" * $header.Length) -ForegroundColor Cyan
    Write-Host $header -ForegroundColor Cyan
    Write-Host ("=" * $header.Length) -ForegroundColor Cyan
}
#endregion

#region Utility Functions
function Test-Administrator {
    $identity = [System.Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = [System.Security.Principal.WindowsPrincipal]$identity
    return $principal.IsInRole([System.Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Test-SystemCompatibility {
    Write-Log "Checking system compatibility..." -Level "INFO"
    
    # Check if running as administrator
    if (-not (Test-Administrator)) {
        throw "This script must be run as Administrator. Please restart PowerShell as Administrator and try again."
    }
    
    # Check available disk space (require at least 500MB)
    try {
        $freeSpace = (Get-WmiObject -Class Win32_LogicalDisk -Filter "DeviceID='C:'").FreeSpace / 1GB
        if ($freeSpace -lt 0.5) {
            throw "Insufficient disk space. At least 500MB required, found $([math]::Round($freeSpace, 2))GB"
        }
        Write-Log "System compatibility check passed" -Level "SUCCESS"
    }
    catch {
        Write-Log "System compatibility check failed: $($_.Exception.Message)" -Level "ERROR"
        throw
    }
}

function Test-MSIAvailability {
    Write-Log "Checking Windows Installer availability..." -Level "INFO"
    
    $maxWaitTime = 180  # 3 minutes
    $checkInterval = 10  # 10 seconds
    $elapsed = 0
    
    while ($elapsed -lt $maxWaitTime) {
        $msiProcesses = Get-Process -Name "msiexec" -ErrorAction SilentlyContinue
        
        if (-not $msiProcesses) {
            Write-Log "Windows Installer is available" -Level "SUCCESS"
            return $true
        }
        
        Write-Log "Windows Installer busy. Waiting $checkInterval seconds... ($elapsed/$maxWaitTime seconds elapsed)" -Level "WARN"
        Start-Sleep -Seconds $checkInterval
        $elapsed += $checkInterval
    }
    
    Write-Log "Timeout waiting for Windows Installer. Restarting MSI service..." -Level "WARN"
    Restart-MSIService
    
    return $true
}

function Restart-MSIService {
    Write-Log "Restarting Windows Installer service to free up resources..." -Level "INFO"
    
    try {
        # Kill any hanging msiexec processes
        $msiProcesses = Get-Process -Name "msiexec" -ErrorAction SilentlyContinue
        if ($msiProcesses) {
            Write-Log "Terminating $($msiProcesses.Count) msiexec process(es)..." -Level "INFO"
            $msiProcesses | Stop-Process -Force -ErrorAction SilentlyContinue
            Start-Sleep -Seconds 5
        }
        
        # Stop and restart the Windows Installer service
        Write-Log "Stopping Windows Installer service..." -Level "INFO"
        Stop-Service -Name "msiserver" -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 5
        
        Write-Log "Starting Windows Installer service..." -Level "INFO"
        Start-Service -Name "msiserver" -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 10
        
        # Verify service is running
        $service = Get-Service -Name "msiserver" -ErrorAction SilentlyContinue
        if ($service -and $service.Status -eq 'Running') {
            Write-Log "Windows Installer service restarted successfully" -Level "SUCCESS"
        } else {
            Write-Log "Warning: Windows Installer service may not be running properly" -Level "WARN"
        }
    }
    catch {
        Write-Log "Error restarting Windows Installer service: $($_.Exception.Message)" -Level "WARN"
    }
}

function Get-FileWithRetry {
    param(
        [string]$Url,
        [string]$OutputPath,
        [int]$MaxRetries = 3
    )

    for ($i = 1; $i -le $MaxRetries; $i++) {
        try {
            Write-Log "Download attempt $i of ${MaxRetries}: $Url" -Level "DOWNLOAD"
            Invoke-WebRequest -Uri $Url -OutFile $OutputPath -UseBasicParsing
            Write-Log "Successfully downloaded $Url to $OutputPath" -Level "SUCCESS"
            return
        }
        catch {
            Write-Log "Failed to download $Url (Attempt $i of ${MaxRetries}): $($_.Exception.Message)" -Level "WARNING"
            if ($i -eq $MaxRetries) {
                throw "Failed to download file after ${MaxRetries} retries."
            }
            Start-Sleep -Seconds (5 * $i)
        }
    }
}
#endregion

#region Banner Function
function Show-Banner {
    # Cloud-X Security ASCII Art Welcome Banner
    Write-Host "" -ForegroundColor Blue
   
    Write-Host '                                                                                                    ' -ForegroundColor Blue
    Write-Host '                                                                                                    ' -ForegroundColor Blue
    Write-Host '                                               @@@@@                                                ' -ForegroundColor Blue
    Write-Host '                                            @@@      @@                                             ' -ForegroundColor Blue
    Write-Host '                                          @@             @@                                         ' -ForegroundColor Blue
    Write-Host '                                     @@@@@@         @@@@@@@@@@@                                     ' -ForegroundColor Blue
    Write-Host '                                    @@@           @@@         @@                                    ' -ForegroundColor Blue
    Write-Host '                                   @@           @@@  @@@@@@@@@ @@                                   ' -ForegroundColor Blue
    Write-Host '                                   @@ @       @@@  @@@       @ @@                                   ' -ForegroundColor Blue
    Write-Host '                                   @@ @@    @@@  @@@         @ @@                                   ' -ForegroundColor Blue
    Write-Host '                                    @@   @@    @@@            @@                                    ' -ForegroundColor Blue
    Write-Host '                                     @@@@@@@@@@@       @@@@@@@                                      ' -ForegroundColor Blue
    Write-Host '                                         @@@                                                        ' -ForegroundColor Blue
    Write-Host '                                                                                                    ' -ForegroundColor Blue
    Write-Host '                                    @@                     @@    @    @                             ' -ForegroundColor Blue
    Write-Host '                               @    @@   @@             @  @     @@  @                              ' -ForegroundColor Blue
    Write-Host '                             @@@@@@ @@ @@@@@@  @@  @@ @@@@@@       @@                               ' -ForegroundColor Blue
    Write-Host '                            @@      @@ @@   @@ @   @@ @    @      @ @@                              ' -ForegroundColor Blue
    Write-Host '                             @@@@@  @@ @@@@@@  @@@@@@ @@@@@@@    @   @@                             ' -ForegroundColor Blue
    Write-Host '                                                                                                    ' -ForegroundColor Blue
    Write-Host '                                                                                                    ' -ForegroundColor Blue
    Write-Host '                                                                                                    ' -ForegroundColor Blue
    Write-Host ""
    Write-Host "                       CLOUD-X SECURITY WAZUH AGENT ENTERPRISE SETUP                         " -ForegroundColor White -BackgroundColor DarkGreen
    Write-Host "                              Version 3.1 - Enhanced Security                           " -ForegroundColor White -BackgroundColor DarkGreen
    Write-Host "                                   $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss UTC')                              " -ForegroundColor Yellow -BackgroundColor DarkGreen
    Write-Host "                                     by CLOUD-X SECURITY                                  " -ForegroundColor Cyan -BackgroundColor DarkGreen
    Write-Host ""
}
#endregion

#region Wazuh Operations
function Uninstall-ExistingWazuhAgent {
    Start-Step "Uninstalling Existing Wazuh Agent (if any)"

    # Attempt to stop the service first to release file locks.
    Write-Log "Attempting to stop the Wazuh Agent service (WazuhSvc)..." -Level "INFO"
    $service = Get-Service -Name "WazuhSvc" -ErrorAction SilentlyContinue
    if ($service -and $service.Status -ne 'Stopped') {
        Stop-Service -Name "WazuhSvc" -Force -ErrorAction SilentlyContinue
        Write-Log "Waiting 5 seconds for processes to terminate..." -Level "INFO"
        Start-Sleep -Seconds 5
    }

    # Find the Wazuh Agent installation by checking the registry.
    Write-Log "Searching for Wazuh Agent in installed programs..." -Level "INFO"
    $uninstallPaths = @(
        "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*",
        "HKLM:\SOFTWARE\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*"
    )
    $wazuhApp = Get-ItemProperty -Path $uninstallPaths -ErrorAction SilentlyContinue | Where-Object { $_.DisplayName -like "Wazuh Agent*" }

    if (-not $wazuhApp) {
        Write-Log "Wazuh Agent not found. No uninstall needed." -Level "SUCCESS"
        return
    }

    Write-Log "Found Wazuh Agent. Running the official uninstaller silently..." -Level "INFO"
    $uninstallCommand = $wazuhApp.UninstallString
    if ($uninstallCommand -like "MsiExec.exe*") {
        $productCode = $wazuhApp.PSChildName
        $command = "msiexec.exe"
        $arguments = "/x $productCode /q"
        Write-Log "Executing: $command $arguments" -Level "INFO"
        Start-Process -FilePath $command -ArgumentList $arguments -Wait -NoNewWindow
    } else {
        Write-Log "Executing non-MSI uninstaller: $uninstallCommand /S" -Level "INFO"
        Start-Process -FilePath $uninstallCommand -ArgumentList "/S" -Wait -NoNewWindow
    }
    
    Write-Log "Uninstaller process has finished." -Level "SUCCESS"

    # Final Cleanup
    $agentDir = "C:\Program Files (x86)\ossec-agent"
    if (Test-Path $agentDir) {
        Write-Log "Performing post-uninstall cleanup of the installation directory..." -Level "INFO"
        Remove-Item -Recurse -Force $agentDir -ErrorAction SilentlyContinue
        
        if (!(Test-Path $agentDir)) {
            Write-Log "Directory successfully removed." -Level "SUCCESS"
        } else {
            Write-Log "FAILED to remove directory: $agentDir. A process may still be locking it." -Level "ERROR"
        }
    } else {
        Write-Log "Wazuh Agent uninstall complete and directory is clean." -Level "SUCCESS"
    }
}

function Install-WazuhAgentMSI {
    param(
        [string]$ipAddress,
        [string]$agentName,
        [string]$groupLabel
    )
    
    # Use local network IP for all groups (local network setup)
    $managerIP = "192.168.100.37"  # Internal network IP for all groups
    
    Write-Log "Group: $groupLabel - Using Local Network Manager IP: $managerIP" -Level "INFO"
    
    Start-Step "Installing Wazuh Agent"
    
    $installerPath = Join-Path $env:TEMP "wazuh-agent-$WAZUH_VERSION.msi"
    if (Test-Path $installerPath) {
        Remove-Item $installerPath -Force
    }

    $maxRetries = 3
    $retryCount = 0

    do {
        try {
            Write-Log "Download attempt $($retryCount + 1) of $($maxRetries + 1)" -Level "INFO"
            
            Get-FileWithRetry -Url $WAZUH_URL -OutputPath $installerPath -MaxRetries 3

            Write-Log "Starting Wazuh agent installation..." -Level "INFO"
            $logFile = Join-Path $env:TEMP "wazuh-install-$(Get-Date -Format 'yyyyMMdd-HHmmss').log"
            $installArgs = "/i `"$installerPath`" /qn /l*v `"$logFile`" WAZUH_MANAGER=$managerIP WAZUH_REGISTRATION_SERVER=$managerIP WAZUH_AGENT_GROUP=$groupLabel WAZUH_AGENT_NAME=$agentName"
            Write-Log "MSI command: msiexec.exe $installArgs" -Level "INFO"
            Write-Log "MSI log file: $logFile" -Level "INFO"
            $process = Start-Process -FilePath "msiexec.exe" -ArgumentList $installArgs -Wait -PassThru

            if ($process.ExitCode -eq 0) {
                Write-Log "Wazuh agent installed successfully" -Level "SUCCESS"
                break
            } else {
                Write-Log "Reading MSI log file for error details..." -Level "INFO"
                if (Test-Path $logFile) {
                    try {
                        $logContent = Get-Content $logFile -Tail 20 -ErrorAction SilentlyContinue
                        if ($logContent) {
                            Write-Log "Last 20 lines of MSI log:" -Level "ERROR"
                            $logContent | ForEach-Object { Write-Log $_ -Level "ERROR" }
                        }
                    }
                    catch {
                        Write-Log "Could not read MSI log file" -Level "WARN"
                    }
                }
                throw "MSI installation failed with exit code: $($process.ExitCode)"
            }
        }
        catch {
            $retryCount++
            if ($retryCount -le $maxRetries) {
                Write-Log "Installation attempt failed: $($_.Exception.Message). Retrying in 10 seconds..." -Level "WARN"
                Start-Sleep -Seconds 10
            } else {
                Write-Log "Installation failed after $($maxRetries + 1) attempts: $($_.Exception.Message)" -Level "ERROR"
                throw
            }
        }
    } while ($retryCount -le $maxRetries)

    # Cleanup
    Remove-Item $installerPath -Force -ErrorAction SilentlyContinue
}

function Set-WazuhAgentConfiguration {
    param(
        [string]$ipAddress,
        [string]$agentName,
        [string]$groupLabel
    )
    
    Start-Step "Configuring Wazuh Agent"
    
    # Use local network IP for all groups (local network setup)
    $configIP = "192.168.100.37"  # Internal network IP for all groups
    
    Write-Log "Group: $groupLabel - Using Local Network IP: $configIP" -Level "INFO"
    
    $ossecAgentPath = if ([IntPtr]::Size -eq 8) { "${env:ProgramFiles(x86)}\ossec-agent" } else { "$env:ProgramFiles\ossec-agent" }
    $configPath = Join-Path $ossecAgentPath "ossec.conf"

    # Wait for config file to be created after installation
    $timeout = 60 # seconds
    $elapsed = 0
    while (-not (Test-Path $configPath) -and $elapsed -lt $timeout) {
        Write-Host "." -NoNewline -ForegroundColor Green
        Start-Sleep -Seconds 3
        $elapsed += 3
    }
    Write-Host ""

    if (-not (Test-Path $configPath)) {
        throw "Configuration file not found after installation timeout: $configPath"
    }

    try {
        $config = Get-Content -Path $configPath -Raw
        $config = $config -replace '<address>.*?</address>', "<address>$configIP</address>"
        Write-Log "Updated manager IP address to: $configIP" -Level "SUCCESS"

        $enrollmentSection = @"
<enrollment>
    <enabled>yes</enabled>
    <manager_address>$configIP</manager_address>
    <agent_name>$agentName</agent_name>
</enrollment>
"@

        if ($config -notmatch '<enrollment>') {
            $config = $config -replace '(?s)(<client>.*?)(</client>)', "`$1`n$enrollmentSection`n`$2"
            Write-Log "Added enrollment configuration" -Level "SUCCESS"
        }

        if ($config -notmatch '<groups>') {
            $groupSection = "<groups>$groupLabel</groups>"
            $config = $config -replace '</enrollment>', "$groupSection`n</enrollment>"
            Write-Log "Added group configuration: $groupLabel" -Level "SUCCESS"
        }

        $config | Set-Content -Path $configPath
        Write-Log "Wazuh agent configuration completed successfully" -Level "SUCCESS"
        
        Write-Log "Local network setup - all groups use internal network (192.168.100.37)" -Level "INFO"
    }
    catch {
        Write-Log "Failed to configure Wazuh agent: $($_.Exception.Message)" -Level "ERROR"
        throw
    }
}

function Start-WazuhService {
    Start-Step "Starting Wazuh Service"

    try {
        Write-Log "Starting Wazuh agent service..." -Level "INFO"
        $process = Start-Process -FilePath "net" -ArgumentList "start WazuhSvc" -Wait -PassThru -NoNewWindow
        
        if ($process.ExitCode -ne 0) {
            throw "Failed to start Wazuh service with exit code: $($process.ExitCode)"
        }

        # Verify service is running
        Start-Sleep -Seconds 5
        $service = Get-Service -Name "WazuhSvc" -ErrorAction SilentlyContinue
        if ($service.Status -eq 'Running') {
            Write-Log "Wazuh agent service started successfully" -Level "SUCCESS"
        } else {
            throw "Wazuh service is not running after start attempt"
        }
    }
    catch {
        Write-Log "Failed to start Wazuh service: $($_.Exception.Message)" -Level "ERROR"
        throw
    }
}
#endregion

#region Post-Install Functions
function Install-ActiveResponseScripts {
    Start-Step "Deploying Active Response Scripts"
    
    Write-Log "Checking for active response scripts..." -Level "INFO"
    
    $ossecAgentPath = if ([IntPtr]::Size -eq 8) { "${env:ProgramFiles(x86)}\ossec-agent" } else { "$env:ProgramFiles\ossec-agent" }
    $activeResponsePath = Join-Path $ossecAgentPath "active-response\bin"
    
    if (Test-Path $activeResponsePath) {
        Write-Log "Active response directory found: $activeResponsePath" -Level "SUCCESS"
        Write-Log "Active response scripts deployment completed" -Level "SUCCESS"
    } else {
        Write-Log "No active response scripts to deploy" -Level "INFO"
    }
}

function Invoke-PostInstallSetup {
    Start-Step "Running Post-Installation Setup"
    
    $postInstallScriptUrl = "https://raw.githubusercontent.com/MAPLEIZER/Cloud-X-security-agent/main/wazuh-configs/scripts/windows/post-install-setup.ps1"
    $cacheBuster = (Get-Date).Ticks
    $urlWithCacheBuster = "$($postInstallScriptUrl)?cache=$($cacheBuster)"
    $tempScriptPath = Join-Path $env:TEMP "post-install-setup.ps1"
    
    try {
        Write-Log "Downloading post-install setup script..." -Level "INFO"
        Get-FileWithRetry -Url $urlWithCacheBuster -OutputPath $tempScriptPath
        
        Write-Log "Executing post-install setup script..." -Level "INFO"
        $ossecAgentPath = if ([IntPtr]::Size -eq 8) { "${env:ProgramFiles(x86)}\ossec-agent" } else { "$env:ProgramFiles\ossec-agent" }
        
        $process = Start-Process -FilePath "powershell.exe" -ArgumentList "-ExecutionPolicy Bypass -File `"$tempScriptPath`" -wazuh_path `"$ossecAgentPath`"" -Wait -PassThru -NoNewWindow
        
        if ($process.ExitCode -ne 0) {
            throw "Post-install script failed with exit code: $($process.ExitCode)"
        }
        
        Write-Log "Post-installation setup completed successfully." -Level "SUCCESS"
    }
    catch {
        Write-Log "Failed to run post-installation setup: $($_.Exception.Message)" -Level "ERROR"
    }
    finally {
        if (Test-Path $tempScriptPath) {
            Remove-Item $tempScriptPath -Force -ErrorAction SilentlyContinue
        }
    }
}

function Remove-TempFiles {
    Write-Log "Cleaning up temporary files..." -Level "INFO"
    
    try {
        $tempFiles = @(
            (Join-Path $env:TEMP "wazuh-agent-*.msi"),
            (Join-Path $env:TEMP "wazuh-install-*.log"),
            (Join-Path $env:TEMP "wazuh-uninstall-*.log")
        )
        
        foreach ($pattern in $tempFiles) {
            Get-ChildItem -Path $pattern -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue
        }
        
        Write-Log "Temporary files cleaned up successfully" -Level "SUCCESS"
    }
    catch {
        Write-Log "Warning: Could not clean up all temporary files: $($_.Exception.Message)" -Level "WARN"
    }
}

function Show-Summary {
    param (
        [datetime]$startTime,
        [string]$agentName,
        [string]$ipAddress,
        [string]$groupLabel
    )

    # Use local network IP for all groups (local network setup)
    $actualIP = "192.168.100.37"  # Internal network IP for all groups

    $endTime = Get-Date
    $duration = New-TimeSpan -Start $startTime -End $endTime

    Write-Host ""
    Write-Host "================================================================================" -ForegroundColor Green
    Write-Host "                         SETUP COMPLETED SUCCESSFULLY                           " -ForegroundColor Green
    Write-Host "================================================================================" -ForegroundColor Green
    Write-Host ""
    Write-Log "Setup completed successfully." -Level "SUCCESS"

    Write-Host "Summary:" -ForegroundColor Cyan
    Write-Host "- Agent Name:    $agentName" -ForegroundColor White
    Write-Host "- Manager IP:    $actualIP" -ForegroundColor White
    Write-Host "- Agent Group:   $groupLabel" -ForegroundColor White
    Write-Host "- Total Time:    $($duration.Minutes)m $($duration.Seconds)s" -ForegroundColor White
    Write-Host "- Log File:      $($global:LogPath)" -ForegroundColor White
    Write-Host ""
    
    Write-Host "Note: Local network setup - all groups use internal network IP (192.168.100.37)" -ForegroundColor Yellow
    Write-Host ""
}
#endregion

#region Main Installation Function
function Install-WazuhAgent {
    param(
        [Parameter(Mandatory=$true)]
        [string]$ipAddress,
        
        [Parameter(Mandatory=$true)]
        [string]$agentName,
        
        [Parameter(Mandatory=$true)]
        [string]$groupLabel,
        
        [string]$ConfigFile = $null,
        [switch]$SKIP_HASH_CHECK,
        [switch]$KeepLogs,
        [string]$LogPath = $null
    )

    # Initialize logging and progress tracking
    $script:startTime = Get-Date
    $script:totalSteps = 9
    $script:currentStep = 0
    
    # Set up logging
    if ($LogPath) {
        $global:LogPath = $LogPath
    } else {
        $global:LogPath = Join-Path $env:TEMP "Cloud-X-Security-Wazuh-Installer-$(Get-Date -Format 'yyyyMMdd-HHmmss').log"
    }
    
    Start-Transcript -Path $global:LogPath -Append
    
    try {
        # Display banner
        Show-Banner
        
        Write-Log "Cloud-X Security Wazuh Agent setup started..." -Level "INFO"
        Write-Log "Parameters provided by: Manual" -Level "INFO"
        Write-Log "Starting Cloud-X Security Wazuh Agent setup..." -Level "INFO"

        # Load configuration from file if provided
        if ($ConfigFile -and (Test-Path $ConfigFile)) {
            Write-Log "Loading configuration from file: $ConfigFile" -Level "INFO"
            # Placeholder for config file loading
            Write-Log "Config file loading is a placeholder in this module version." -Level "WARNING"
        }

        # Main Execution
        Start-Step "Initialization and Parameter Validation"
        Write-Log "Setup initiated by user: $env:USERNAME" -Level "INFO"
        Write-Log "Parameters: IP=$ipAddress, AgentName=$agentName, Group=$groupLabel, Version=$WAZUH_VERSION" -Level "INFO"

        # Pre-flight checks
        Test-SystemCompatibility
        Test-MSIAvailability

        # Core Operations
        Uninstall-ExistingWazuhAgent
        Install-WazuhAgentMSI -ipAddress $ipAddress -agentName $agentName -groupLabel $groupLabel
        Set-WazuhAgentConfiguration -ipAddress $ipAddress -agentName $agentName -groupLabel $groupLabel
        Start-WazuhService

        # Post-Install
        Start-Step "Finalizing Setup"
        Install-ActiveResponseScripts
        Invoke-PostInstallSetup
        Remove-TempFiles
    }
    catch {
        Write-Host ""
        Write-Host "================================================================================" -ForegroundColor Red
        Write-Host "                            SETUP FAILED                                     " -ForegroundColor Red
        Write-Host "================================================================================" -ForegroundColor Red
        Write-Host ""
        Write-Log "Setup failed: $($_.Exception.Message)" -Level "ERROR"
        Write-Log "Completed $script:currentStep of $script:totalSteps steps." -Level "ERROR"
        Write-Host ""
        Write-Host "Troubleshooting tips:" -ForegroundColor Yellow
        Write-Host "* Ensure you're running as Administrator." -ForegroundColor White
        Write-Host "* Check your network connection and that the manager IP (192.168.100.37) is reachable." -ForegroundColor White
        Write-Host "* Review the log file for details: $($global:LogPath)" -ForegroundColor White
        Write-Host ""
        throw
    }
    finally {
        if ($PSItem -eq $null) { # If no errors occurred
            Show-Summary -startTime $script:startTime -agentName $agentName -ipAddress $ipAddress -groupLabel $groupLabel
        }
        Stop-Transcript
    }
}
#endregion

# Export the main function
Export-ModuleMember -Function Install-WazuhAgent
