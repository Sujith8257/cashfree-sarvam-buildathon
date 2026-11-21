[CmdletBinding()]
param([switch]$Production)

$ErrorActionPreference = 'Stop'
$frontendRoot = Split-Path -Parent $PSScriptRoot
foreach ($command in @('node', 'npm', 'npx')) {
    if (-not (Get-Command $command -ErrorAction SilentlyContinue)) {
        throw "Install Node.js 22.12+ (or a newer supported LTS) and retry: missing $command."
    }
}

Push-Location -LiteralPath $frontendRoot
try {
    Write-Host 'Checking the frontend build...'
    & npm ci
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
    & npm run build
    if ($LASTEXITCODE -ne 0) { throw 'Build failed. Deployment cancelled.' }

    Write-Host 'Before deploying, configure SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY in the Vercel project environment settings.'
    Write-Host 'For a project imported from GitHub, set its Root Directory to frontend.'
    $deployArgs = @('--yes', '--package=vercel', 'vercel', 'deploy')
    if ($Production) { $deployArgs += '--prod' }
    & npx @deployArgs
    if ($LASTEXITCODE -ne 0) { throw 'Vercel deployment failed. Check CLI login and project settings.' }
} finally {
    Pop-Location
}
