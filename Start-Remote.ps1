param(
    [ValidateSet('Frontend', 'Samples', 'Camera', 'Auto')][string]$Mode = 'Frontend',
    [string]$ApiUrl = 'https://orangevision.onrender.com',
    [ValidateRange(1, 65535)][int]$FrontendPort = 5174,
    [switch]$NoBrowser
)
$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$frontend = Join-Path $root 'Frontend'
$vite = Join-Path $frontend 'node_modules\vite\bin\vite.js'
if (-not (Test-Path -LiteralPath $vite)) { throw 'Instale as dependências com yarn install na pasta Frontend.' }
$node = (Get-Command node -ErrorAction Stop).Source
$api = [uri]$ApiUrl
if ($api.Scheme -ne 'https' -or $api.UserInfo -or $api.AbsolutePath -ne '/' -or $api.Query -or $api.Fragment) {
    throw 'ApiUrl deve ser a origem HTTPS da API, sem caminho ou credenciais.'
}
$ApiUrl = $api.GetLeftPart([System.UriPartial]::Authority)
$frontOrigin = "http://127.0.0.1:$FrontendPort"
$listener = @(Get-NetTCPConnection -LocalPort $FrontendPort -State Listen -ErrorAction SilentlyContinue)
if ($listener) { throw "Porta $FrontendPort ocupada. Encerre o Vite anterior para carregar a configuração da API remota; nenhum processo foi encerrado." }
if ($Mode -ne 'Frontend') {
    $devicePython = Join-Path $root 'backend\.venv-device\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $devicePython)) { throw 'Ambiente do dispositivo não encontrado.' }
    $workers = @(Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^python(w)?\.exe$' -and $_.CommandLine -match 'backend\.device(\s+samples|\.inspect)' })
    if ($workers) { throw 'Encerre o consumidor anterior com Ctrl+C ou a câmera com Q para iniciar o executor na API remota. Use -Mode Frontend para abrir somente o site.' }
}
$health = Invoke-RestMethod -Uri "$ApiUrl/health" -TimeoutSec 60
if ($health.service -ne 'orangevision-web') { throw 'A URL não respondeu como API OrangeVision.' }
$previousProxy = $env:API_PROXY_TARGET
$previousApi = $env:WEB_API_BASE_URL
$previousFront = $env:WEB_FRONTEND_ORIGIN
try {
    $env:API_PROXY_TARGET = $ApiUrl
    $env:WEB_API_BASE_URL = $ApiUrl
    $env:WEB_FRONTEND_ORIGIN = $frontOrigin
    $viteProcess = Start-Process -FilePath $node -ArgumentList @("`"$vite`"", '--host', '127.0.0.1', '--port', "$FrontendPort", '--strictPort') -WorkingDirectory $frontend -PassThru
    $ready = $false
    $deadline = (Get-Date).AddSeconds(30)
    while ((Get-Date) -lt $deadline -and -not $viteProcess.HasExited) {
        try {
            $response = Invoke-WebRequest -UseBasicParsing -Uri $frontOrigin -TimeoutSec 2
            if ($response.StatusCode -eq 200) { $ready = $true; break }
        } catch { Start-Sleep -Milliseconds 250 }
    }
    if (-not $ready) { throw 'Vite não ficou disponível em 30 segundos. Confira a janela do frontend.' }
    if ($Mode -ne 'Frontend') {
        $model = Start-Process -FilePath $devicePython -ArgumentList '-B -m backend.device.model_setup' -WorkingDirectory $root -NoNewWindow -Wait -PassThru
        if ($model.ExitCode -ne 0) { throw 'Modelo não disponível. Confira o diagnóstico.' }
        $arguments = if ($Mode -eq 'Samples') { '-B -m backend.device samples --loop --ai' } elseif ($Mode -eq 'Camera') { '-B -m backend.device.inspect --camera 0' } else { '-B -m backend.device.inspect --camera 0 --auto' }
        Start-Process -FilePath $devicePython -ArgumentList $arguments -WorkingDirectory $root
    }
    "Frontend: $frontOrigin | API: $ApiUrl | Swagger: $ApiUrl/docs"
    'Mantenha a janela do Vite aberta. Não é necessário iniciar uma API local.'
    if (-not $NoBrowser) { Start-Process "$frontOrigin/dashboard/amostras" }
} finally {
    $env:API_PROXY_TARGET = $previousProxy
    $env:WEB_API_BASE_URL = $previousApi
    $env:WEB_FRONTEND_ORIGIN = $previousFront
}
