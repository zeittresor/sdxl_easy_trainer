param(
    [int]$TimeoutSeconds = 20
)

$token = ""
$remaining = [Math]::Max(1, $TimeoutSeconds)
$startLeft = [Console]::CursorLeft
$startTop = [Console]::CursorTop

function Render-Prompt {
    param([int]$SecondsLeft, [int]$Length)
    $message = "Optional Hugging Face token for gated/private models (auto-skip in ${SecondsLeft}s): "
    $mask = if ($Length -gt 0) { '*' * $Length } else { '' }
    $full = $message + $mask
    [Console]::SetCursorPosition(0, $startTop)
    $width = [Math]::Max([Console]::BufferWidth - 1, $full.Length + 5)
    $padding = ' ' * $width
    [Console]::Write($padding)
    [Console]::SetCursorPosition(0, $startTop)
    [Console]::Write($full)
}

Render-Prompt -SecondsLeft $remaining -Length 0
$deadline = (Get-Date).AddSeconds($TimeoutSeconds)
$lastShown = $remaining

while ((Get-Date) -lt $deadline) {
    while ([Console]::KeyAvailable) {
        $key = [Console]::ReadKey($true)
        switch ($key.Key) {
            'Enter' {
                [Console]::WriteLine()
                Write-Output $token
                exit 0
            }
            'Backspace' {
                if ($token.Length -gt 0) {
                    $token = $token.Substring(0, $token.Length - 1)
                    $remaining = [Math]::Max(0, [int][Math]::Ceiling(($deadline - (Get-Date)).TotalSeconds))
                    Render-Prompt -SecondsLeft $remaining -Length $token.Length
                }
            }
            default {
                if (-not [char]::IsControl($key.KeyChar)) {
                    $token += $key.KeyChar
                    $remaining = [Math]::Max(0, [int][Math]::Ceiling(($deadline - (Get-Date)).TotalSeconds))
                    Render-Prompt -SecondsLeft $remaining -Length $token.Length
                }
            }
        }
    }

    $secondsLeft = [Math]::Max(0, [int][Math]::Ceiling(($deadline - (Get-Date)).TotalSeconds))
    if ($secondsLeft -ne $lastShown) {
        $lastShown = $secondsLeft
        Render-Prompt -SecondsLeft $secondsLeft -Length $token.Length
    }
    Start-Sleep -Milliseconds 100
}

Render-Prompt -SecondsLeft 0 -Length $token.Length
[Console]::WriteLine()
Write-Output ""
exit 0
