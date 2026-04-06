# Разработка: код с хоста смонтирован в контейнеры, Django runserver + Vite HMR — без rebuild при правках .py/.tsx.
# Если .ps1 блокирует ExecutionPolicy — из папки docker: .\dev.cmd -Gateway -HotFrontend up -d --build (нужен префикс .\)
# Локально:  .\dev.ps1 up -d --build
# С gateway и доменом:  .\dev.ps1 -Gateway up -d --build
# HMR через HTTPS (NPM):  .\dev.ps1 -Gateway -HotFrontend up -d --build  (четвёртый файл: docker-compose.hot-frontend.yml)
param(
    [switch] $Gateway,
    [switch] $HotFrontend,
    [Parameter(ValueFromRemainingArguments = $true)]
    [object[]] $ComposeArgs
)
$ErrorActionPreference = 'Stop'
$here = $PSScriptRoot
if ($HotFrontend -and -not $Gateway) {
    throw '-HotFrontend requires -Gateway (domain/NPM). Example: .\dev.ps1 -Gateway -HotFrontend up -d --build. For localhost:3050 omit -HotFrontend.'
}
$files = @(
    '-f', (Join-Path $here 'docker-compose.yml'),
    '-f', (Join-Path $here 'docker-compose.dev.yml')
)
if ($Gateway) {
    $files += '-f', (Join-Path $here 'docker-compose.domain.yml')
}
if ($HotFrontend) {
    $files += '-f', (Join-Path $here 'docker-compose.hot-frontend.yml')
}
# VK_CLIENT_ID из backend/.env подставляется в compose для VITE_VK_ID (через --env-file).
$backendEnv = Join-Path (Split-Path $here -Parent) 'backend\.env'
$envFileArgs = @()
if (Test-Path -LiteralPath $backendEnv) {
    $envFileArgs = @('--env-file', $backendEnv)
}
docker compose @envFileArgs @files @ComposeArgs
