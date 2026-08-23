$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$Host.UI.RawUI.WindowTitle = 'BG Studio 3D - Kalıcı Yönetici'

$appHome = Join-Path $env:LOCALAPPDATA 'BGStudio3D'
$launchHome = Join-Path $appHome 'launcher'
$repoFile = Join-Path $launchHome 'repo-path.txt'
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'

function Wait-And-Exit([string]$Message) {
    Write-Host ''
    Write-Host $Message -ForegroundColor Red
    Write-Host ''
    Read-Host 'Kapatmak icin Enter'
    exit 1
}

try {
    New-Item -ItemType Directory -Path $launchHome -Force | Out-Null
    $repo = $null
    if (Test-Path -LiteralPath $repoFile) {
        $repo = (Get-Content -LiteralPath $repoFile -Raw -ErrorAction SilentlyContinue).Trim().Trim('"')
    }

    while ($true) {
        if ($repo) {
            $server = Join-Path $repo 'tools\product_manager\server.py'
            $storage = Join-Path $repo 'tools\product_manager\storage_cli.py'
            if ((Test-Path -LiteralPath $server) -and (Test-Path -LiteralPath $storage)) { break }
        }
        Clear-Host
        Write-Host '===============================================' -ForegroundColor DarkYellow
        Write-Host '       BG STUDIO 3D - KALICI YÖNETİCİ' -ForegroundColor White
        Write-Host '===============================================' -ForegroundColor DarkYellow
        Write-Host ''
        Write-Host 'Kayitli repo bulunamadi veya tasinmis.' -ForegroundColor Yellow
        Write-Host 'bgstudio-3d klasorunun TAM yolunu yapistir.'
        $typed = (Read-Host 'Repo yolu').Trim().Trim('"')
        if (-not $typed) { Wait-And-Exit 'Repo yolu bos birakildi.' }
        $server = Join-Path $typed 'tools\product_manager\server.py'
        $storage = Join-Path $typed 'tools\product_manager\storage_cli.py'
        if ((Test-Path -LiteralPath $server) -and (Test-Path -LiteralPath $storage)) {
            $repo = (Resolve-Path -LiteralPath $typed).Path
            Set-Content -LiteralPath $repoFile -Value $repo -Encoding UTF8
            break
        }
        Write-Host '[HATA] Bu klasorde gerekli panel dosyalari yok.' -ForegroundColor Red
        Start-Sleep -Seconds 1
        $repo = $null
    }

    # Keep the visible desktop shortcut name fully Turkish.
    try {
        $desktop = [Environment]::GetFolderPath([Environment+SpecialFolder]::Desktop)
        if (-not [string]::IsNullOrWhiteSpace($desktop)) {
            $legacyShortcut = Join-Path $desktop 'BG Studio 3D Yonetici.lnk'
            $turkishShortcut = Join-Path $desktop 'BG Studio 3D Yönetici.lnk'
            if ((Test-Path -LiteralPath $legacyShortcut) -and -not (Test-Path -LiteralPath $turkishShortcut)) {
                Rename-Item -LiteralPath $legacyShortcut -NewName 'BG Studio 3D Yönetici.lnk' -Force
            }
        }
    } catch {}

    # Keep the persistent desktop shortcut icon synced with the current repo artwork.
    $repoIcon = Join-Path $repo 'assets\brand\bgstudio3d-app.ico'
    $iconTarget = Join-Path $launchHome 'bgstudio3d.ico'
    if (Test-Path -LiteralPath $repoIcon) {
        $needsCopy = -not (Test-Path -LiteralPath $iconTarget)
        if (-not $needsCopy) {
            try { $needsCopy = (Get-FileHash -LiteralPath $repoIcon -Algorithm SHA256).Hash -ne (Get-FileHash -LiteralPath $iconTarget -Algorithm SHA256).Hash } catch { $needsCopy = $true }
        }
        if ($needsCopy) {
            Copy-Item -LiteralPath $repoIcon -Destination $iconTarget -Force
            Unblock-File -LiteralPath $iconTarget -ErrorAction SilentlyContinue
            try {
                Add-Type @'
using System;
using System.Runtime.InteropServices;
public static class BG3DShellNotify {
  [DllImport("shell32.dll")]
  public static extern void SHChangeNotify(uint wEventId, uint uFlags, IntPtr dwItem1, IntPtr dwItem2);
}
'@ -ErrorAction SilentlyContinue
                [BG3DShellNotify]::SHChangeNotify(0x08000000, 0x0000, [IntPtr]::Zero, [IntPtr]::Zero)
            } catch {}
        }
    }

    Clear-Host
    Write-Host '===============================================' -ForegroundColor DarkYellow
    Write-Host '       BG STUDIO 3D - KALICI YÖNETİCİ' -ForegroundColor White
    Write-Host '===============================================' -ForegroundColor DarkYellow
    Write-Host ''
    Write-Host ('Repo : ' + $repo)
    Write-Host ('Veri : ' + $appHome)
    Write-Host ''
    Write-Host 'Kalici veriler hazirlaniyor...' -ForegroundColor DarkYellow

    $pythonCommand = $null
    $pythonPrefix = @()
    if (Get-Command py -ErrorAction SilentlyContinue) {
        $pythonCommand = 'py'; $pythonPrefix = @('-3')
    } elseif (Get-Command python -ErrorAction SilentlyContinue) {
        $pythonCommand = 'python'
    } elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
        $pythonCommand = 'python3'
    }
    if (-not $pythonCommand) { Wait-And-Exit 'Python 3 bulunamadi.' }

    $storage = Join-Path $repo 'tools\product_manager\storage_cli.py'
    $server = Join-Path $repo 'tools\product_manager\server.py'

    & $pythonCommand @pythonPrefix $storage 'prepare'
    if ($LASTEXITCODE -ne 0) { Wait-And-Exit 'Kalici veri kasasi hazirlanamadi. Verilerin silinmedi.' }

    & $pythonCommand @pythonPrefix $server
    if ($LASTEXITCODE -ne 0) { Wait-And-Exit "Panel sunucusu hata koduyla kapandi: $LASTEXITCODE" }
}
catch {
    Wait-And-Exit $_.Exception.Message
}
