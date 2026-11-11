# 重启后运行：启动 Docker Desktop，构建镜像，起容器，验证 /health
$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo

$docker = "C:\Program Files\Docker\Docker\resources\bin\docker.exe"
if (-not (Test-Path $docker)) { $docker = "docker" }

$desktop = "C:\Program Files\Docker\Docker\Docker Desktop.exe"
if (Test-Path $desktop) {
    if (-not (Get-Process -Name "Docker Desktop" -ErrorAction SilentlyContinue)) {
        Start-Process $desktop
    }
}

Write-Host "Waiting for Docker daemon..."
$ready = $false
for ($i = 0; $i -lt 90; $i++) {
    & $docker info *> $null
    if ($LASTEXITCODE -eq 0) { $ready = $true; break }
    Start-Sleep -Seconds 2
}
if (-not $ready) { throw "Docker daemon did not start within 180s" }

& $docker version
& $docker build -t xbxc-ai .

& $docker rm -f xbxc-ai *> $null
& $docker run -d --name xbxc-ai --restart unless-stopped --env-file ai/.env -p 8000:8000 xbxc-ai

Write-Host "Waiting for /health..."
for ($i = 0; $i -lt 30; $i++) {
    try {
        $h = Invoke-RestMethod http://127.0.0.1:8000/health -TimeoutSec 3
        $h | ConvertTo-Json -Compress
        Write-Host "OK"
        exit 0
    } catch {
        Start-Sleep -Seconds 2
    }
}

& $docker logs --tail 80 xbxc-ai
throw "API did not become healthy"
