# OVOSHI: доменный стек + Vite dev в контейнере (volume ../frontend).
# Правки .css / .jsx на диске → сразу в браузере (HMR), без docker build frontend.
#
# Первый запуск (собрать образ Dockerfile.dev и node_modules volume):
#   .\up-hot-frontend.ps1 up -d --build
# Дальше:
#   .\up-hot-frontend.ps1 up -d
#
# Тест по https://ovoshipubgm.ru: NPM → этот ПК:59728 (gateway). HMR по умолчанию wss:443 (см. hot-frontend compose).

$here = $PSScriptRoot
& (Join-Path $here 'up-prod.ps1') -HotFrontend @args
