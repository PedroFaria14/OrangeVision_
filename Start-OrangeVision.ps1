param(
    [ValidateSet('Frontend', 'Samples', 'Camera', 'Auto')][string]$Mode = 'Frontend',
    [string]$ApiUrl = 'https://orangevision.onrender.com',
    [switch]$NoBrowser
)
& (Join-Path $PSScriptRoot 'Start-Remote.ps1') -Mode $Mode -ApiUrl $ApiUrl -FrontendPort 5174 -NoBrowser:$NoBrowser
