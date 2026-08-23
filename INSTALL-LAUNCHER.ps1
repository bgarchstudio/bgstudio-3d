$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)

function Write-Step([string]$Text) { Write-Host ("[+] " + $Text) -ForegroundColor DarkYellow }
function Write-Ok([string]$Text)   { Write-Host ("[OK] " + $Text) -ForegroundColor Green }
function Write-Warn([string]$Text) { Write-Host ("[!] " + $Text) -ForegroundColor Yellow }

try {
    $packageRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
    $appHome = Join-Path $env:LOCALAPPDATA 'BGStudio3D'
    $launchHome = Join-Path $appHome 'launcher'
    $repoFile = Join-Path $launchHome 'repo-path.txt'
    $launcherSource = Join-Path $packageRoot 'launcher\BG-STUDIO-3D-YONETICI.ps1'
    $launcherTarget = Join-Path $launchHome 'BG-STUDIO-3D-YONETICI.ps1'
    $iconTarget = Join-Path $launchHome 'bgstudio3d.ico'
    $iconSource = Join-Path $packageRoot 'assets\brand\bgstudio3d-app.ico'

    Write-Host ''
    Write-Host '=====================================================' -ForegroundColor DarkYellow
    Write-Host '      BG STUDIO 3D - KALICI LAUNCHER KURULUMU' -ForegroundColor White
    Write-Host '=====================================================' -ForegroundColor DarkYellow
    Write-Host ''

    if (-not (Test-Path -LiteralPath $launcherSource)) {
        throw "Launcher sablonu bulunamadi: $launcherSource"
    }

    $candidates = @(
        $packageRoot,
        (Split-Path -Parent $packageRoot)
    ) | Select-Object -Unique

    $repo = $null
    foreach ($candidate in $candidates) {
        if ([string]::IsNullOrWhiteSpace($candidate)) { continue }
        $server = Join-Path $candidate 'tools\product_manager\server.py'
        $storage = Join-Path $candidate 'tools\product_manager\storage_cli.py'
        if ((Test-Path -LiteralPath $server) -and (Test-Path -LiteralPath $storage)) {
            $repo = (Resolve-Path -LiteralPath $candidate).Path
            break
        }
    }

    if (-not $repo -and (Test-Path -LiteralPath $repoFile)) {
        $saved = (Get-Content -LiteralPath $repoFile -Raw -ErrorAction SilentlyContinue).Trim().Trim('"')
        if ($saved) {
            $server = Join-Path $saved 'tools\product_manager\server.py'
            $storage = Join-Path $saved 'tools\product_manager\storage_cli.py'
            if ((Test-Path -LiteralPath $server) -and (Test-Path -LiteralPath $storage)) {
                $repo = (Resolve-Path -LiteralPath $saved).Path
            }
        }
    }

    while (-not $repo) {
        Write-Warn 'Repo klasoru otomatik bulunamadi.'
        Write-Host 'bgstudio-3d klasorunun TAM yolunu yapistir.'
        Write-Host 'Ornek: C:\Users\Berkant\OneDrive\Desktop\...\bgstudio-3d'
        $typed = (Read-Host 'Repo yolu').Trim().Trim('"')
        if (-not $typed) { throw 'Repo yolu bos birakildi.' }
        $server = Join-Path $typed 'tools\product_manager\server.py'
        $storage = Join-Path $typed 'tools\product_manager\storage_cli.py'
        if ((Test-Path -LiteralPath $server) -and (Test-Path -LiteralPath $storage)) {
            $repo = (Resolve-Path -LiteralPath $typed).Path
        } else {
            Write-Warn 'Bu klasorde gerekli panel dosyalari bulunamadi. Tekrar dene.'
        }
    }

    Write-Step "Repo bulundu: $repo"
    New-Item -ItemType Directory -Path $launchHome -Force | Out-Null
    Set-Content -LiteralPath $repoFile -Value $repo -Encoding UTF8

    Copy-Item -LiteralPath $launcherSource -Destination $launcherTarget -Force
    Unblock-File -LiteralPath $launcherTarget -ErrorAction SilentlyContinue
    Write-Ok "Kalici launcher olusturuldu: $launcherTarget"

    if (Test-Path -LiteralPath $iconSource) {
        Copy-Item -LiteralPath $iconSource -Destination $iconTarget -Force
        Unblock-File -LiteralPath $iconTarget -ErrorAction SilentlyContinue
        Write-Ok "BG Studio 3D uygulama ikonu kuruldu: $iconTarget"
    } else {
        Write-Warn "Uygulama ikonu bulunamadi; kisayol varsayilan ikonla olusturulacak."
    }

    $desktop = [Environment]::GetFolderPath([Environment+SpecialFolder]::Desktop)
    if ([string]::IsNullOrWhiteSpace($desktop)) {
        $shell = New-Object -ComObject WScript.Shell
        $desktop = $shell.SpecialFolders.Item('Desktop')
    }
    if ([string]::IsNullOrWhiteSpace($desktop)) { throw 'Windows masaustu klasoru bulunamadi.' }

    $shortcutPath = Join-Path $desktop 'BG Studio 3D Yönetici.lnk'
    $wsh = New-Object -ComObject WScript.Shell
    $shortcut = $wsh.CreateShortcut($shortcutPath)
    $powershellExe = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
    $shortcut.TargetPath = $powershellExe
    $shortcut.Arguments = '-NoProfile -ExecutionPolicy Bypass -File "' + $launcherTarget + '"'
    $shortcut.WorkingDirectory = $launchHome
    if (Test-Path -LiteralPath $iconTarget) { $shortcut.IconLocation = "$iconTarget,0" }
    $shortcut.Description = 'BG Studio 3D Kalıcı Yönetici'
    $shortcut.Save()
    Unblock-File -LiteralPath $shortcutPath -ErrorAction SilentlyContinue

    if (-not (Test-Path -LiteralPath $shortcutPath)) { throw 'Masaustu kisayolu kaydedilemedi.' }

    Write-Ok "Masaustu kisayolu olusturuldu: $shortcutPath"
    Write-Host ''
    Write-Host 'Kalici veri : ' -NoNewline; Write-Host $appHome -ForegroundColor Cyan
    Write-Host 'Kalici panel: ' -NoNewline; Write-Host $launcherTarget -ForegroundColor Cyan
    Write-Host 'Repo        : ' -NoNewline; Write-Host $repo -ForegroundColor Cyan
    Write-Host ''
    Write-Host 'Bundan sonra paneli masaustundeki BG Studio 3D Yönetici kısayolundan aç.' -ForegroundColor Green
    Write-Host 'Yeni ZIP paketlerindeki CMD/BAT dosyalari artik launcher icin gerekli degil.'
    Write-Host ''

    $open = (Read-Host 'Panel simdi acilsin mi? (E/H)').Trim()
    if ($open -match '^(?i:e|evet|y|yes)$') {
        Start-Process -FilePath $powershellExe -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-File',$launcherTarget)
    }
    exit 0
}
catch {
    Write-Host ''
    Write-Host '=====================================================' -ForegroundColor DarkRed
    Write-Host '                 KURULUM DURDURULDU' -ForegroundColor Red
    Write-Host '=====================================================' -ForegroundColor DarkRed
    Write-Host ''
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host ''
    exit 1
}
