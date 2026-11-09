param(
    [ValidateSet('Frontend', 'Samples', 'Camera', 'Auto')][string]$Mode = 'Frontend',
    [ValidateRange(1, 65535)][int]$FrontendPort = 5174,
    [ValidateRange(1, 65535)][int]$ApiPort = 8001,
    [ValidateRange(0, 20)][int]$CameraIndex = 0,
    [switch]$NoBrowser
)
$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$frontend = Join-Path $root 'Frontend'
$apiPython = Join-Path $root 'web_api\.venv-web\Scripts\python.exe'
$devicePython = Join-Path $root 'backend\.venv-device\Scripts\python.exe'
$vite = Join-Path $frontend 'node_modules\vite\bin\vite.js'
foreach ($file in @($apiPython, $vite)) {
    if (-not (Test-Path -LiteralPath $file)) { throw "Dependência não encontrada: $file" }
}
if ($Mode -ne 'Frontend' -and -not (Test-Path -LiteralPath $devicePython)) { throw 'Ambiente do dispositivo não encontrado.' }
if ($ApiPort -eq $FrontendPort) { throw 'API e frontend precisam de portas diferentes.' }
foreach ($port in @($ApiPort, $FrontendPort)) {
    if (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) { throw "Porta $port ocupada. Nenhum processo foi encerrado." }
}
if ($Mode -ne 'Frontend') {
    $workers = @(Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^python(w)?\.exe$' -and $_.CommandLine -match 'backend\.device(\s+samples|\.inspect)' })
    if ($workers) { throw 'Encerre o executor anterior com Ctrl+C ou Q antes de iniciar outro.' }
}
$node = (Get-Command node -ErrorAction Stop).Source
$apiUrl = "http://127.0.0.1:$ApiPort"
$frontOrigin = "http://127.0.0.1:$FrontendPort"
$variables = @('WEB_ENV', 'WEB_ALLOWED_ORIGINS', 'API_PROXY_TARGET', 'VITE_API_BASE_URL', 'VITE_API_ENABLED', 'WEB_API_BASE_URL', 'ALLOW_INSECURE_LOCAL_API', 'WEB_FRONTEND_ORIGIN', 'DEVICE_SQLITE_PATH')
$previous = @{}
foreach ($name in $variables) { $previous[$name] = [Environment]::GetEnvironmentVariable($name, 'Process') }
$owned = @()
$started = $false
try {
    # Configuração apenas dos processos filhos. Os .env privados não são alterados.
    $env:WEB_ENV = 'development'
    $env:WEB_ALLOWED_ORIGINS = "$apiUrl,$frontOrigin,http://localhost:$FrontendPort"
    $env:API_PROXY_TARGET = $apiUrl
    $env:VITE_API_BASE_URL = '/api'
    $env:VITE_API_ENABLED = 'true'
    $env:WEB_API_BASE_URL = $apiUrl
    $env:ALLOW_INSECURE_LOCAL_API = 'true'
    $env:WEB_FRONTEND_ORIGIN = $frontOrigin
    # Outbox separada das sessões já usadas por outros destinos/portas.
    $env:DEVICE_SQLITE_PATH = "data/local-$ApiPort/device_pipeline.db"
    & $node --experimental-strip-types (Join-Path $frontend 'scripts\check-api-status.ts')
    if ($LASTEXITCODE -ne 0) { Write-Warning 'Render indisponível. A execução abaixo usará a API local e o PostgreSQL já configurado.' }
    $apiProcess = Start-Process -FilePath $apiPython -ArgumentList @('-B', '-m', 'uvicorn', 'web_api.main:app', '--host', '127.0.0.1', '--port', "$ApiPort") -WorkingDirectory $root -PassThru
    $owned += $apiProcess
    $ready = $false
    $deadline = (Get-Date).AddSeconds(30)
    while ((Get-Date) -lt $deadline -and -not $apiProcess.HasExited) {
        try {
            $health = Invoke-RestMethod -Uri "$apiUrl/health" -TimeoutSec 2
            if ($health.status -eq 'ok' -and $health.service -eq 'orangevision-web') { $ready = $true; break }
        } catch { Start-Sleep -Milliseconds 300 }
    }
    if (-not $ready) { throw 'API local não iniciou. Confira o diagnóstico na janela Python.' }
    if ($Mode -ne 'Frontend') {
        & $devicePython -B -c 'import sys; sys.path.insert(0,sys.argv[1]); from backend.device.detector import OrangeDetector; OrangeDetector()' $root
        if ($LASTEXITCODE -ne 0) { throw 'Modelo local indisponível. Execute a preparação do modelo descrita na documentação.' }
        'Modelo local validado.'
    }
    $viteProcess = Start-Process -FilePath $node -ArgumentList @("`"$vite`"", '--host', '127.0.0.1', '--port', "$FrontendPort", '--strictPort') -WorkingDirectory $frontend -PassThru
    $owned += $viteProcess
    $ready = $false
    $deadline = (Get-Date).AddSeconds(30)
    while ((Get-Date) -lt $deadline -and -not $viteProcess.HasExited) {
        try {
            $response = Invoke-WebRequest -UseBasicParsing -Uri $frontOrigin -TimeoutSec 2
            if ($response.StatusCode -eq 200) { $ready = $true; break }
        } catch { Start-Sleep -Milliseconds 300 }
    }
    if (-not $ready) { throw 'Frontend não iniciou. Confira a janela do Vite.' }
    if ($Mode -ne 'Frontend') {
        $arguments = if ($Mode -eq 'Samples') { '-B -m backend.device samples --loop --ai' } elseif ($Mode -eq 'Camera') { "-B -m backend.device.inspect --camera $CameraIndex" } else { "-B -m backend.device.inspect --camera $CameraIndex --auto" }
        $deviceProcess = Start-Process -FilePath $devicePython -ArgumentList $arguments -WorkingDirectory $root -PassThru
        $owned += $deviceProcess
        Start-Sleep -Seconds 2
        if ($deviceProcess.HasExited) { throw 'Executor encerrou durante a inicialização. Confira credencial, vínculo ou câmera na janela Python.' }
    }
    $started = $true
    "Frontend: $frontOrigin | API local: $apiUrl | Swagger: $apiUrl/docs"
    'Banco: PostgreSQL configurado na Web API; este modo não cria um banco offline.'
    'Para imagens: faça login, abra Amostras, envie a foto e escolha o equipamento. Qualidade depende de calibração validada.'
    'Mantenha as janelas abertas. Para encerrar, use Ctrl+C nos servidores/executor ou Q na câmera.'
    if (-not $NoBrowser) { Start-Process "$frontOrigin/dashboard/amostras" }
} finally {
    foreach ($name in $variables) { [Environment]::SetEnvironmentVariable($name, $previous[$name], 'Process') }
    if (-not $started) {
        foreach ($process in $owned) { if (-not $process.HasExited) { Stop-Process -Id $process.Id -ErrorAction SilentlyContinue } }
    }
}
