# ===========================================================================
#  Market Digest - Task Scheduler Registration
#
#  Run this ONCE as Administrator to register the daily 9 AM task.
#  1. Right-click PowerShell -> "Run as Administrator"
#  2. cd "D:\Projects\Github\Market Digest"
#  3. .\schedule_task.ps1
# ===========================================================================

$TASK_NAME   = "Market Digest Daily"
$PS_SCRIPT   = Join-Path (Split-Path -Parent -Path $MyInvocation.MyCommand.Path) "run_daily.ps1"
$WORKING_DIR = Split-Path -Parent -Path $MyInvocation.MyCommand.Path
$RUN_HOUR    = 9
$RUN_MINUTE  = 0

# --- Check for Admin -------------------------------------------------------
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]"Administrator"
)
if (-not $isAdmin) {
    Write-Host "ERROR: Please run this script as Administrator." -ForegroundColor Red
    exit 1
}

# --- Remove existing task if present ---------------------------------------
if (Get-ScheduledTask -TaskName $TASK_NAME -ErrorAction SilentlyContinue) {
    Write-Host "Removing existing task '$TASK_NAME' ..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $TASK_NAME -Confirm:$false
}

# --- Trigger: 09:00 AM, Mon-Fri -------------------------------------------
$trigger = New-ScheduledTaskTrigger `
    -Weekly `
    -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday `
    -At ("{0:D2}:{1:D2}" -f $RUN_HOUR, $RUN_MINUTE)

# --- Action ----------------------------------------------------------------
$action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NonInteractive -ExecutionPolicy Bypass -File `"$PS_SCRIPT`"" `
    -WorkingDirectory $WORKING_DIR

# --- Settings --------------------------------------------------------------
$settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 30) `
    -StartWhenAvailable `
    -DontStopIfGoingOnBatteries `
    -DontStopOnIdleEnd

# --- Principal: run as current user ----------------------------------------
$principal = New-ScheduledTaskPrincipal `
    -UserId $env:USERNAME `
    -LogonType S4U `
    -RunLevel Highest

# --- Register --------------------------------------------------------------
$task = Register-ScheduledTask `
    -TaskName   $TASK_NAME `
    -Trigger    $trigger `
    -Action     $action `
    -Settings   $settings `
    -Principal  $principal `
    -Description "Generates the Market Digest report and copies PDF to OneDrive for Teams delivery."

if ($task) {
    Write-Host ""
    Write-Host "Task registered successfully!" -ForegroundColor Green
    Write-Host ("  Name     : " + $TASK_NAME)
    Write-Host ("  Schedule : Every weekday (Mon-Fri) at " + $RUN_HOUR + ":00 AM")
    Write-Host ("  Script   : " + $PS_SCRIPT)
    Write-Host ""
    Write-Host "To test now (without waiting for 9 AM), run:"
    Write-Host "  Start-ScheduledTask -TaskName '$TASK_NAME'"
    Write-Host ""
    Write-Host "To view logs after a run:"
    Write-Host "  notepad '$WORKING_DIR\output\run_daily.log'"
} else {
    Write-Host "Registration failed. Check errors above." -ForegroundColor Red
    exit 1
}
