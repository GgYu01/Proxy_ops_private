<#
Installs mihomo with MetaCubeXD Web UI on Windows.

Run from an elevated PowerShell session. The script downloads official latest
GitHub release assets, validates SHA256 digests returned by GitHub, validates
the mihomo profile, and registers a resident SYSTEM startup task.
#>

[CmdletBinding()]
param(
    [string]$InstallRoot = 'C:\Tools\mihomo',
    [string]$ProgramDataRoot = 'C:\ProgramData\mihomo',
    [string]$SystemConfigRoot = 'C:\Windows\System32\config\systemprofile\.config\mihomo',
    [string]$ProfileUrl = 'https://subs.sea.prod.gglohh.top/subscriptions/mihomo-universal.yaml',
    [string]$TaskName = 'Mihomo TUN Transparent Proxy',
    [int]$StartupWaitSeconds = 8
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 2.0
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$MihomoExe = Join-Path $InstallRoot 'mihomo-windows-amd64.exe'
$ProfilePath = Join-Path $ProgramDataRoot 'mihomo-universal.yaml'
$SafeProfilePath = Join-Path $SystemConfigRoot 'mihomo-universal.yaml'
$UiPath = Join-Path $SystemConfigRoot 'ui'
$LogPath = Join-Path $ProgramDataRoot 'install-mihomo-windows.log'
$WorkRoot = Join-Path $env:TEMP ('mihomo-install-' + [guid]::NewGuid().ToString('N'))

function Write-Step {
    param([Parameter(Mandatory)] [string]$Message)
    Write-Host ''
    Write-Host "== $Message =="
}

function Assert-Administrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = [Security.Principal.WindowsPrincipal]::new($identity)
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw 'Run this script from an elevated PowerShell session. TUN and SYSTEM startup task setup require administrator rights.'
    }
}

function Invoke-GitHubApi {
    param([Parameter(Mandatory)] [string]$Uri)
    Invoke-RestMethod -Uri $Uri -Headers @{ 'User-Agent' = 'proxy-platform-mihomo-installer' } -TimeoutSec 30
}

function Select-RequiredAsset {
    param(
        [Parameter(Mandatory)] $Release,
        [Parameter(Mandatory)] [string[]]$Patterns,
        [Parameter(Mandatory)] [string]$Label
    )

    foreach ($pattern in $Patterns) {
        $matches = @($Release.assets | Where-Object { $_.name -match $pattern } | Sort-Object name)
        if ($matches.Count -gt 0) {
            return $matches[0]
        }
    }
    $available = @($Release.assets | ForEach-Object { $_.name }) -join ', '
    throw "No $Label release asset matched. Available assets: $available"
}

function Save-Download {
    param(
        [Parameter(Mandatory)] [string]$Url,
        [Parameter(Mandatory)] [string]$Path
    )

    New-Item -ItemType Directory -Path (Split-Path -Parent $Path) -Force | Out-Null
    Invoke-WebRequest -Uri $Url -OutFile $Path -UseBasicParsing -TimeoutSec 120
    if (-not (Test-Path -LiteralPath $Path)) {
        throw "Download did not create expected file: $Path"
    }
}

function Assert-FileDigest {
    param(
        [Parameter(Mandatory)] [string]$Path,
        [Parameter(Mandatory)] [string]$Digest,
        [Parameter(Mandatory)] [string]$Label
    )

    if ($Digest -notmatch '^sha256:[0-9a-fA-F]{64}$') {
        throw "$Label release asset does not expose a usable sha256 digest"
    }
    $expected = $Digest.Substring(7).ToLowerInvariant()
    $actual = (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant()
    Write-Host "$Label expected_sha256=$expected"
    Write-Host "$Label actual_sha256=$actual"
    if ($actual -ne $expected) {
        throw "$Label SHA256 mismatch"
    }
}

function Backup-ExistingPath {
    param(
        [Parameter(Mandatory)] [string]$Path,
        [Parameter(Mandatory)] [string]$BackupRoot
    )

    if (-not (Test-Path -LiteralPath $Path)) {
        return
    }
    New-Item -ItemType Directory -Path $BackupRoot -Force | Out-Null
    $leaf = Split-Path -Leaf $Path
    $destination = Join-Path $BackupRoot $leaf
    Copy-Item -LiteralPath $Path -Destination $destination -Recurse -Force
    Write-Host "backup_path=$destination"
}

function Stop-MihomoRuntime {
    Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    Get-Process mihomo-windows-amd64, mihomo -ErrorAction SilentlyContinue | Stop-Process -Force
}

function Set-YamlScalarValue {
    param(
        [Parameter(Mandatory)] [string]$Text,
        [Parameter(Mandatory)] [string]$Key,
        [Parameter(Mandatory)] [string]$Value
    )

    if ($Text -match "(?m)^$([regex]::Escape($Key)):\s*.+$") {
        return [regex]::Replace($Text, "(?m)^$([regex]::Escape($Key)):\s*.+$", "$Key`: $Value")
    }
    return $Text.TrimEnd() + "`r`n$Key`: $Value`r`n"
}

function Write-ReviewedProfile {
    param(
        [Parameter(Mandatory)] [string]$SourcePath,
        [Parameter(Mandatory)] [string]$DestinationPath
    )

    # Runtime binding invariants:
    # SYSTEM profile: C:\Windows\System32\config\systemprofile\.config\mihomo\mihomo-universal.yaml
    # external-controller: 127.0.0.1:9090
    # external-ui: ui
    $profile = Get-Content -LiteralPath $SourcePath -Raw
    $profile = Set-YamlScalarValue -Text $profile -Key 'external-controller' -Value '127.0.0.1:9090'
    $profile = Set-YamlScalarValue -Text $profile -Key 'external-ui' -Value 'ui'
    New-Item -ItemType Directory -Path (Split-Path -Parent $DestinationPath) -Force | Out-Null
    Set-Content -LiteralPath $DestinationPath -Value $profile -Encoding UTF8
}

function Expand-MihomoAsset {
    param(
        [Parameter(Mandatory)] [string]$ArchivePath,
        [Parameter(Mandatory)] [string]$DestinationRoot
    )

    $extractRoot = Join-Path $WorkRoot 'mihomo'
    New-Item -ItemType Directory -Path $extractRoot -Force | Out-Null
    Expand-Archive -LiteralPath $ArchivePath -DestinationPath $extractRoot -Force
    $candidate = Get-ChildItem -LiteralPath $extractRoot -Recurse -File |
        Where-Object { $_.Name -match '^mihomo.*\.exe$' } |
        Sort-Object FullName |
        Select-Object -First 1
    if (-not $candidate) {
        throw 'mihomo executable was not found inside the downloaded archive'
    }
    New-Item -ItemType Directory -Path $DestinationRoot -Force | Out-Null
    Copy-Item -LiteralPath $candidate.FullName -Destination $MihomoExe -Force
}

function Expand-MetaCubeXDWebUi {
    param(
        [Parameter(Mandatory)] [string]$ArchivePath,
        [Parameter(Mandatory)] [string]$DestinationRoot,
        [Parameter(Mandatory)] [string]$BackupRoot
    )

    $tar = Get-Command tar.exe -ErrorAction SilentlyContinue
    if (-not $tar) {
        throw 'tar.exe was not found. Windows 10/11 includes it by default; install bsdtar or update Windows.'
    }

    $extractRoot = Join-Path $WorkRoot 'metacubexd'
    New-Item -ItemType Directory -Path $extractRoot -Force | Out-Null
    & $tar.Source -xzf $ArchivePath -C $extractRoot
    if ($LASTEXITCODE -ne 0) {
        throw "MetaCubeXD extraction failed with exit code $LASTEXITCODE"
    }

    $index = Get-ChildItem -LiteralPath $extractRoot -Recurse -File -Filter 'index.html' |
        Sort-Object FullName |
        Select-Object -First 1
    if (-not $index) {
        throw 'MetaCubeXD Web UI index.html was not found inside compressed-dist.tgz'
    }

    $sourceUi = Split-Path -Parent $index.FullName
    Backup-ExistingPath -Path $DestinationRoot -BackupRoot $BackupRoot
    if (Test-Path -LiteralPath $DestinationRoot) {
        Remove-Item -LiteralPath $DestinationRoot -Recurse -Force
    }
    New-Item -ItemType Directory -Path $DestinationRoot -Force | Out-Null
    Copy-Item -Path (Join-Path $sourceUi '*') -Destination $DestinationRoot -Recurse -Force
}

function Register-MihomoStartupTask {
    $action = New-ScheduledTaskAction -Execute $MihomoExe -Argument "-f `"$SafeProfilePath`"" -WorkingDirectory $InstallRoot
    $trigger = New-ScheduledTaskTrigger -AtStartup
    $principal = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -RunLevel Highest
    $settings = New-ScheduledTaskSettingsSet `
        -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries `
        -ExecutionTimeLimit (New-TimeSpan -Seconds 0) `
        -RestartCount 3 `
        -RestartInterval (New-TimeSpan -Minutes 1)

    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings | Out-Null
    Start-ScheduledTask -TaskName $TaskName
}

function Assert-Listener {
    param([Parameter(Mandatory)] [int]$Port)
    $listener = Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue |
        Where-Object { $_.LocalAddress -eq '127.0.0.1' -and $_.LocalPort -eq $Port } |
        Select-Object -First 1
    if (-not $listener) {
        throw "Expected listener was not found on 127.0.0.1:$Port"
    }
    Write-Host "listener_ok=127.0.0.1:$Port"
}

function Assert-HttpOk {
    param([Parameter(Mandatory)] [string]$Url)
    $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 10
    if ([int]$response.StatusCode -lt 200 -or [int]$response.StatusCode -ge 300) {
        throw "$Url returned HTTP $($response.StatusCode)"
    }
    Write-Host "http_ok=$Url status=$($response.StatusCode)"
}

Assert-Administrator
New-Item -ItemType Directory -Path $ProgramDataRoot, $InstallRoot, $SystemConfigRoot, $WorkRoot -Force | Out-Null
Start-Transcript -Path $LogPath -Append | Out-Null

try {
    $backupRoot = Join-Path $ProgramDataRoot ('backup-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))

    Write-Step 'Resolve official latest GitHub releases'
    $mihomoRelease = Invoke-GitHubApi -Uri 'https://api.github.com/repos/MetaCubeX/mihomo/releases/latest'
    $metacubeRelease = Invoke-GitHubApi -Uri 'https://api.github.com/repos/MetaCubeX/metacubexd/releases/latest'
    $mihomoAsset = Select-RequiredAsset -Release $mihomoRelease -Label 'mihomo Windows amd64' -Patterns @(
        '^mihomo-windows-amd64-v[0-9]+\.[0-9]+\.[0-9]+\.zip$',
        '^mihomo-windows-amd64-compatible-.*\.zip$',
        '^mihomo-windows-amd64.*\.zip$'
    )
    $metacubeAsset = Select-RequiredAsset -Release $metacubeRelease -Label 'MetaCubeXD Web UI' -Patterns @(
        '^compressed-dist\.tgz$'
    )
    Write-Host "mihomo_release=$($mihomoRelease.tag_name)"
    Write-Host "mihomo_asset=$($mihomoAsset.name)"
    Write-Host "metacubexd_release=$($metacubeRelease.tag_name)"
    Write-Host "metacubexd_asset=$($metacubeAsset.name)"

    Write-Step 'Download and verify release assets'
    $mihomoArchive = Join-Path $WorkRoot $mihomoAsset.name
    $metacubeArchive = Join-Path $WorkRoot $metacubeAsset.name
    Save-Download -Url $mihomoAsset.browser_download_url -Path $mihomoArchive
    Save-Download -Url $metacubeAsset.browser_download_url -Path $metacubeArchive
    Assert-FileDigest -Path $mihomoArchive -Digest $mihomoAsset.digest -Label 'mihomo'
    Assert-FileDigest -Path $metacubeArchive -Digest $metacubeAsset.digest -Label 'metacubexd'

    Write-Step 'Download and prepare mihomo profile'
    $downloadedProfile = Join-Path $WorkRoot 'mihomo-universal.yaml'
    Save-Download -Url $ProfileUrl -Path $downloadedProfile
    Backup-ExistingPath -Path $ProfilePath -BackupRoot $backupRoot
    Backup-ExistingPath -Path $SafeProfilePath -BackupRoot $backupRoot
    Write-ReviewedProfile -SourcePath $downloadedProfile -DestinationPath $ProfilePath

    Write-Step 'Install mihomo executable and MetaCubeXD Web UI'
    Stop-MihomoRuntime
    Backup-ExistingPath -Path $MihomoExe -BackupRoot $backupRoot
    Expand-MihomoAsset -ArchivePath $mihomoArchive -DestinationRoot $InstallRoot
    Expand-MetaCubeXDWebUi -ArchivePath $metacubeArchive -DestinationRoot $UiPath -BackupRoot $backupRoot

    Write-Step 'Validate and sync SYSTEM profile'
    & $MihomoExe -t -f $ProfilePath
    if ($LASTEXITCODE -ne 0) {
        throw "mihomo configuration validation failed with exit code $LASTEXITCODE"
    }
    Copy-Item -LiteralPath $ProfilePath -Destination $SafeProfilePath -Force
    & $MihomoExe -t -f $SafeProfilePath
    if ($LASTEXITCODE -ne 0) {
        throw "SYSTEM mihomo configuration validation failed with exit code $LASTEXITCODE"
    }

    Write-Step 'Register and start SYSTEM startup task'
    Register-MihomoStartupTask
    Start-Sleep -Seconds $StartupWaitSeconds

    Write-Step 'Verify local runtime'
    Assert-Listener -Port 7890
    Assert-Listener -Port 9090
    Assert-HttpOk -Url 'http://127.0.0.1:9090/version'
    Assert-HttpOk -Url 'http://127.0.0.1:9090/ui/'

    Write-Host ''
    Write-Host 'install_result=PASS'
    Write-Host 'dashboard_url=http://127.0.0.1:9090/ui/'
    Write-Host "profile_url=$ProfileUrl"
    Write-Host "log_path=$LogPath"
} finally {
    if (Test-Path -LiteralPath $WorkRoot) {
        Remove-Item -LiteralPath $WorkRoot -Recurse -Force -ErrorAction SilentlyContinue
    }
    Stop-Transcript | Out-Null
}
