Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$script:DefaultWazuhVersion = '4.14.7-1'

function Test-CloudXHost {
    param([Parameter(Mandatory = $true)][string]$Value)
    if ($Value.Length -gt 253) { return $false }
    return $Value -match '^[A-Za-z0-9:][A-Za-z0-9.:-]*$'
}

function Test-CloudXIdentifier {
    param([Parameter(Mandatory = $true)][string]$Value)
    if ($Value.Length -gt 128) { return $false }
    return $Value -match '^[A-Za-z0-9][A-Za-z0-9_.-]*$'
}

function Assert-CloudXAdministrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw 'Cloud-X agent deployment must run as Administrator.'
    }
}

function Get-CloudXWazuhInstaller {
    param([Parameter(Mandatory = $true)][string]$Version)

    if ($Version -notmatch '^\d+\.\d+\.\d+-\d+$') {
        throw 'Invalid Wazuh agent version format.'
    }

    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    $url = "https://packages.wazuh.com/4.x/windows/wazuh-agent-$Version.msi"
    $path = Join-Path ([IO.Path]::GetTempPath()) ("cloudx-wazuh-{0}.msi" -f ([Guid]::NewGuid().ToString('N')))

    Invoke-WebRequest -Uri $url -OutFile $path -UseBasicParsing -MaximumRedirection 3

    $signature = Get-AuthenticodeSignature -LiteralPath $path
    if ($signature.Status -ne [System.Management.Automation.SignatureStatus]::Valid) {
        Remove-Item -LiteralPath $path -Force -ErrorAction SilentlyContinue
        throw "Downloaded Wazuh installer has an invalid Authenticode signature: $($signature.Status)"
    }

    return $path
}

function Install-CloudXAgent {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)][string]$ManagerIP,
        [Parameter(Mandatory = $true)][string]$AgentName,
        [Parameter(Mandatory = $true)][string]$AgentGroup,
        [string]$WazuhVersion = $script:DefaultWazuhVersion
    )

    Assert-CloudXAdministrator
    if (-not (Test-CloudXHost -Value $ManagerIP)) { throw 'Invalid Wazuh manager address.' }
    if (-not (Test-CloudXIdentifier -Value $AgentName)) { throw 'Invalid Wazuh agent name.' }
    if (-not (Test-CloudXIdentifier -Value $AgentGroup)) { throw 'Invalid Wazuh agent group.' }

    $installerPath = Get-CloudXWazuhInstaller -Version $WazuhVersion
    try {
        $arguments = @(
            '/i', "`"$installerPath`"",
            '/qn',
            '/norestart',
            "WAZUH_MANAGER=`"$ManagerIP`"",
            "WAZUH_REGISTRATION_SERVER=`"$ManagerIP`"",
            "WAZUH_AGENT_NAME=`"$AgentName`"",
            "WAZUH_AGENT_GROUP=`"$AgentGroup`""
        )
        $process = Start-Process -FilePath 'msiexec.exe' -ArgumentList $arguments -Wait -PassThru -NoNewWindow
        if ($process.ExitCode -notin @(0, 3010)) {
            throw "Wazuh MSI installation failed with exit code $($process.ExitCode)."
        }

        $service = Get-Service -Name 'WazuhSvc' -ErrorAction SilentlyContinue
        if ($service) {
            Set-Service -Name 'WazuhSvc' -StartupType Automatic
            if ($service.Status -ne 'Running') {
                Start-Service -Name 'WazuhSvc'
            }
        }

        [pscustomobject]@{
            Status = 'success'
            Manager = $ManagerIP
            AgentName = $AgentName
            Group = $AgentGroup
            WazuhVersion = $WazuhVersion
            RebootRequired = ($process.ExitCode -eq 3010)
        }
    }
    finally {
        Remove-Item -LiteralPath $installerPath -Force -ErrorAction SilentlyContinue
    }
}

function Install-WazuhAgent {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)][string]$ipAddress,
        [Parameter(Mandatory = $true)][string]$agentName,
        [Parameter(Mandatory = $true)][string]$groupLabel,
        [string]$WazuhVersion = $script:DefaultWazuhVersion
    )

    Install-CloudXAgent -ManagerIP $ipAddress -AgentName $agentName -AgentGroup $groupLabel -WazuhVersion $WazuhVersion
}

Export-ModuleMember -Function Install-CloudXAgent, Install-WazuhAgent
