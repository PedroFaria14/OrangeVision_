param(
    [ValidateSet('Frontend', 'Samples', 'Camera', 'Auto')][string]$Mode = 'Frontend',
    [string]$ApiUrl = '',
    [switch]$Local,
    [ValidateRange(0, 65535)][int]$FrontendPort = 0,
    [switch]$NoBrowser
)
if ($Local) {
    $port = if ($FrontendPort) { $FrontendPort } else { 5174 }
    & (Join-Path $PSScriptRoot 'Start-Local.ps1') -Mode $Mode -FrontendPort $port -NoBrowser:$NoBrowser
} else {
    $port = if ($FrontendPort) { $FrontendPort } else { 5173 }
    & (Join-Path $PSScriptRoot 'Start-Remote.ps1') -Mode $Mode -ApiUrl $ApiUrl -FrontendPort $port -NoBrowser:$NoBrowser
}
