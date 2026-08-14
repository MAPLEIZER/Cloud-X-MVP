Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Test-CloudXAdministrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Get-WazuhProductCodes {
    $paths = @(
        'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*',
        'HKLM:\SOFTWARE\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*'
    )

    $codes = New-Object System.Collections.Generic.HashSet[string]
    foreach ($path in $paths) {
        Get-ItemProperty -Path $path -ErrorAction SilentlyContinue |
            Where-Object {
                $_.DisplayName -and
                ($_.DisplayName -eq 'Wazuh Agent' -or $_.DisplayName -like 'Wazuh Agent *')
            } |
            ForEach-Object {
                $parsed = [Guid]::Empty
                if ([Guid]::TryParse($_.PSChildName, [ref]$parsed)) {
                    [void]$codes.Add($parsed.ToString('B'))
                }
            }
    }
    return @($codes)
}

function Remove-CloudXPath {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [switch]$Recurse
    )

    if (-not (Test-Path -LiteralPath $Path)) { return }
    if ($Recurse) {
        Remove-Item -LiteralPath $Path -Recurse -Force -ErrorAction Stop
    }
    else {
        Remove-Item -LiteralPath $Path -Force -ErrorAction Stop
    }
}

function Remove-WazuhAgent {
    [CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'High')]
    param(
        [switch]$Force,
        [switch]$KeepLogs
    )

    if (-not (Test-CloudXAdministrator)) {
        throw 'Wazuh removal must run as Administrator.'
    }

    if (-not $Force -and -not $PSCmdlet.ShouldProcess('this endpoint', 'Uninstall Wazuh Agent and Cloud-X response files')) {
        return
    }

    $service = Get-Service -Name 'WazuhSvc' -ErrorAction SilentlyContinue
    if ($service -and $service.Status -ne 'Stopped') {
        Stop-Service -Name 'WazuhSvc' -Force -ErrorAction Stop
        $service.WaitForStatus('Stopped', [TimeSpan]::FromSeconds(30))
    }

    $productCodes = Get-WazuhProductCodes
    foreach ($productCode in $productCodes) {
        $process = Start-Process -FilePath "$env:SystemRoot\System32\msiexec.exe" \
            -ArgumentList @('/x', $productCode, '/qn', '/norestart') \
            -Wait -PassThru -NoNewWindow
        if ($process.ExitCode -notin @(0, 1605, 1614, 3010)) {
            throw "Wazuh MSI uninstall failed with exit code $($process.ExitCode)."
        }
    }

    # Remove only explicit Wazuh/Cloud-X paths. Do not terminate processes by
    # wildcard names such as agent*, which can affect unrelated software.
    $paths = @(
        (Join-Path $env:ProgramFiles 'ossec-agent'),
        (Join-Path ${env:ProgramFiles(x86)} 'ossec-agent'),
        (Join-Path $env:ProgramData 'CloudX\Quarantine')
    ) | Where-Object { $_ }

    if (-not $KeepLogs) {
        $paths += @(
            (Join-Path $env:ProgramData 'ossec-agent'),
            (Join-Path $env:ProgramData 'Wazuh Agent')
        )
    }

    foreach ($path in ($paths | Select-Object -Unique)) {
        Remove-CloudXPath -Path $path -Recurse
    }

    foreach ($serviceName in @('WazuhSvc', 'OssecSvc')) {
        if (Get-Service -Name $serviceName -ErrorAction SilentlyContinue) {
            & "$env:SystemRoot\System32\sc.exe" delete $serviceName | Out-Null
        }
    }

    [pscustomobject]@{
        Status = 'success'
        ProductCodesProcessed = $productCodes.Count
        RebootMayBeRequired = $true
        LogsPreserved = [bool]$KeepLogs
    }
}

Export-ModuleMember -Function Remove-WazuhAgent
