# Прод: docker-compose.yml + docker-compose.domain.yml.
# Подхватывает ../backend/.env (VK_CLIENT_ID и др.).
#
# -HotFrontend — фронт с Vite dev + volume ../frontend: без docker build после правок JSX (см. docker-compose.hot-frontend.yml).
param(
    [switch] $HotFrontend,
    [Parameter(ValueFromRemainingArguments = $true)]
    [object[]] $ComposeArgs
)
$ErrorActionPreference = 'Stop'
$here = $PSScriptRoot
$backendEnv = Join-Path (Split-Path $here -Parent) 'backend\.env'
$envFileArgs = @()
if (Test-Path -LiteralPath $backendEnv) {
    $envFileArgs = @('--env-file', $backendEnv)
}
$files = @(
    '-f', (Join-Path $here 'docker-compose.yml'),
    '-f', (Join-Path $here 'docker-compose.domain.yml')
)
if ($HotFrontend) {
    $files += '-f', (Join-Path $here 'docker-compose.hot-frontend.yml')
}
docker compose @envFileArgs @files @ComposeArgs
