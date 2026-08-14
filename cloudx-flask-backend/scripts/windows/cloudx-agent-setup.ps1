param(
    [string]$WazuhPath = 'C:\Program Files (x86)\ossec-agent',
    [string]$WazuhManager = '',
    [string]$AgentName = $env:COMPUTERNAME
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Test-Administrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

if (-not (Test-Administrator)) {
    throw 'Cloud-X post-install setup must run as Administrator.'
}

if (-not (Test-Path -LiteralPath $WazuhPath -PathType Container)) {
    $candidates = @(
        (Join-Path $env:ProgramFiles 'ossec-agent'),
        (Join-Path ${env:ProgramFiles(x86)} 'ossec-agent')
    )
    $WazuhPath = $candidates | Where-Object { $_ -and (Test-Path -LiteralPath $_ -PathType Container) } | Select-Object -First 1
}
if (-not $WazuhPath) { throw 'Wazuh installation directory was not found.' }

$python = Get-Command python.exe -ErrorAction SilentlyContinue
if (-not $python) { $python = Get-Command python -ErrorAction SilentlyContinue }
if (-not $python) { throw 'Python 3 with psutil must be installed before enabling Cloud-X active response.' }
& $python.Source -c 'import psutil' 2>$null
if ($LASTEXITCODE -ne 0) { throw 'Python psutil is required. Install it through your approved software-management process.' }

$sourceScript = Join-Path $PSScriptRoot 'remove-threat.py'
if (-not (Test-Path -LiteralPath $sourceScript -PathType Leaf)) {
    throw 'The Cloud-X deployment bundle is missing remove-threat.py.'
}

$activeResponseDir = Join-Path $WazuhPath 'active-response\bin'
New-Item -ItemType Directory -Path $activeResponseDir -Force | Out-Null
$destinationScript = Join-Path $activeResponseDir 'remove-threat.py'
Copy-Item -LiteralPath $sourceScript -Destination $destinationScript -Force

$scriptAcl = New-Object System.Security.AccessControl.FileSecurity
$scriptAcl.SetAccessRuleProtection($true, $false)
$scriptAcl.AddAccessRule((New-Object System.Security.AccessControl.FileSystemAccessRule('SYSTEM', 'FullControl', 'Allow')))
$scriptAcl.AddAccessRule((New-Object System.Security.AccessControl.FileSystemAccessRule('BUILTIN\Administrators', 'FullControl', 'Allow')))
Set-Acl -LiteralPath $destinationScript -AclObject $scriptAcl

$configDir = Join-Path $WazuhPath 'etc'
New-Item -ItemType Directory -Path $configDir -Force | Out-Null
$configPath = Join-Path $configDir 'cloudx_active_response.conf'
@'
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
'@ | Set-Content -LiteralPath $configPath -Encoding UTF8

$quarantineDir = Join-Path $env:ProgramData 'CloudX\Quarantine'
New-Item -ItemType Directory -Path $quarantineDir -Force | Out-Null
$quarantineAcl = New-Object System.Security.AccessControl.DirectorySecurity
$quarantineAcl.SetAccessRuleProtection($true, $false)
$quarantineAcl.AddAccessRule((New-Object System.Security.AccessControl.FileSystemAccessRule('SYSTEM', 'FullControl', 'ContainerInherit,ObjectInherit', 'None', 'Allow')))
$quarantineAcl.AddAccessRule((New-Object System.Security.AccessControl.FileSystemAccessRule('BUILTIN\Administrators', 'FullControl', 'ContainerInherit,ObjectInherit', 'None', 'Allow')))
Set-Acl -LiteralPath $quarantineDir -AclObject $quarantineAcl

$scriptBlockPath = 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\PowerShell\ScriptBlockLogging'
New-Item -Path $scriptBlockPath -Force | Out-Null
New-ItemProperty -Path $scriptBlockPath -Name EnableScriptBlockLogging -Value 1 -PropertyType DWord -Force | Out-Null

$moduleLogPath = 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\PowerShell\ModuleLogging'
New-Item -Path $moduleLogPath -Force | Out-Null
New-ItemProperty -Path $moduleLogPath -Name EnableModuleLogging -Value 1 -PropertyType DWord -Force | Out-Null

Restart-Service -Name 'WazuhSvc' -Force
if ((Get-Service -Name 'WazuhSvc').Status -ne 'Running') {
    throw 'Wazuh service did not return to Running state after Cloud-X setup.'
}

Write-Output "Cloud-X active response configured for $AgentName."
