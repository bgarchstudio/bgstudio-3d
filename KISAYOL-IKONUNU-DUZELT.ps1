$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)

try {
    $root = Split-Path -Parent $MyInvocation.MyCommand.Path
    $iconSource = Join-Path $root 'bgstudio3d.ico'
    $appHome = Join-Path $env:LOCALAPPDATA 'BGStudio3D'
    $launchHome = Join-Path $appHome 'launcher'
    $iconTarget = Join-Path $launchHome 'bgstudio3d.ico'

    if (-not (Test-Path -LiteralPath $iconSource)) { throw "BG Studio 3D ikon dosyasi bulunamadi." }
    New-Item -ItemType Directory -Path $launchHome -Force | Out-Null
    Copy-Item -LiteralPath $iconSource -Destination $iconTarget -Force
    Unblock-File -LiteralPath $iconTarget -ErrorAction SilentlyContinue

    $desktop = [Environment]::GetFolderPath([Environment+SpecialFolder]::Desktop)
    if ([string]::IsNullOrWhiteSpace($desktop)) {
        $tmp = New-Object -ComObject WScript.Shell
        $desktop = $tmp.SpecialFolders.Item('Desktop')
    }
    if ([string]::IsNullOrWhiteSpace($desktop)) { throw 'Windows masaustu yolu bulunamadi.' }

    $shortcutPath = Join-Path $desktop 'BG Studio 3D Yonetici.lnk'
    if (-not (Test-Path -LiteralPath $shortcutPath)) { throw "Masaustu kisayolu bulunamadi: $shortcutPath" }

    $wsh = New-Object -ComObject WScript.Shell
    $shortcut = $wsh.CreateShortcut($shortcutPath)
    $shortcut.IconLocation = "$iconTarget,0"
    $shortcut.Description = 'BG Studio 3D Yonetici'
    $shortcut.Save()
    Unblock-File -LiteralPath $shortcutPath -ErrorAction SilentlyContinue

    # Ask Windows Explorer to refresh icon resources without restarting Explorer.
    Add-Type @'
using System;
using System.Runtime.InteropServices;
public static class ShellNotify {
  [DllImport("shell32.dll")]
  public static extern void SHChangeNotify(uint wEventId, uint uFlags, IntPtr dwItem1, IntPtr dwItem2);
}
'@ -ErrorAction SilentlyContinue
    [ShellNotify]::SHChangeNotify(0x08000000, 0x0000, [IntPtr]::Zero, [IntPtr]::Zero)

    Write-Host ''
    Write-Host '[OK] BG Studio 3D ikonu masaustu kisayoluna uygulandi.' -ForegroundColor Green
    Write-Host "Ikon: $iconTarget" -ForegroundColor Cyan
    Write-Host ''
    Write-Host 'Masaustunde hemen degismezse F5 yap veya kisayolu bir kez yenile.'
}
catch {
    Write-Host ''
    Write-Host ('[HATA] ' + $_.Exception.Message) -ForegroundColor Red
    Write-Host ''
}
Read-Host 'Kapatmak icin Enter'
