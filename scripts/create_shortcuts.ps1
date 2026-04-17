param(
    [Parameter(Mandatory = $true)][string]$ProjectDir,
    [Parameter(Mandatory = $true)][string]$ShortcutName,
    [string]$VbsPath = "run_gui.vbs"
)

$projectDir = (Resolve-Path $ProjectDir).Path
$target = Join-Path $projectDir $VbsPath
if (-not (Test-Path $target)) {
    throw "Launcher not found: $target"
}

$locations = @(
    [Environment]::GetFolderPath('Desktop'),
    (Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs')
)

$wshell = New-Object -ComObject WScript.Shell
foreach ($location in $locations) {
    if (-not $location) { continue }
    if (-not (Test-Path $location)) { continue }
    $shortcutPath = Join-Path $location ($ShortcutName + '.lnk')
    $shortcut = $wshell.CreateShortcut($shortcutPath)
    $shortcut.TargetPath = $target
    $shortcut.WorkingDirectory = $projectDir
    $iconPath = Join-Path $projectDir "app\assets\app_icon.ico"
    if (Test-Path $iconPath) {
        $shortcut.IconLocation = $iconPath
    } else {
        $shortcut.IconLocation = "$env:SystemRoot\System32\SHELL32.dll,220"
    }
    $shortcut.Save()
}
