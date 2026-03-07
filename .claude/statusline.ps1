# Claude Code Statusline Script
# PowerShell script that generates a dynamic statusline

$origDollarQuestion = $global:?
$origLastExitCode = $global:LASTEXITCODE

# Get current directory
$cwd = Get-Location
$projectName = Split-Path -Path $cwd -Leaf

# Get git branch
$gitBranch = $null
try {
    $gitBranch = git branch --show-current 2>$null
} catch {}

# Check for active tasks
$activeTasks = @()
$tasksDir = ".claude\tasks"
if (Test-Path $tasksDir) {
    $activeTasks = Get-ChildItem -Path $tasksDir -Filter "*.json" -ErrorAction SilentlyContinue |
        Where-Object { $_.LastWriteTime -gt (Get-Date).AddMinutes(-5) } |
        Select-Object -First 3 -ExpandProperty Name
}

# Build statusline
$statuslineParts = @()

# Add git branch if available
if ($gitBranch) {
    $statuslineParts += " $gitBranch"
}

# Add project/directory name
if ($projectName) {
    $statuslineParts += "$projectName"
}

# Add active tasks count
if ($activeTasks.Count -gt 0) {
    $statuslineParts += "🔄 $($activeTasks.Count) task"
} else {
    $statuslineParts += "🤖 ready"
}

# Join parts with separator
$statusline = $statuslineParts -join " │ "

# Add color (cyan)
$coloredStatusline = "$([char]0x1B)[96m$statusline$([char]0x1B)[0m"

# Output the statusline
Write-Output $coloredStatusline

# Restore original state
$global:LASTEXITCODE = $origLastExitCode
