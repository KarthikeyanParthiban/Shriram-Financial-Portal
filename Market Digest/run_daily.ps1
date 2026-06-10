# ===========================================================================
#  Market Digest - Daily Runner
#  Triggered by Windows Task Scheduler at 09:00 every weekday.
#
#  CONFIGURE THE SECTION BELOW, THEN RUN schedule_task.ps1 TO REGISTER.
# ===========================================================================

# --- CONFIGURATION ---------------------------------------------------------
$PYTHON        = "C:\Users\K964\AppData\Local\Programs\Python\Python312\python.exe"
$PROJECT_DIR   = Split-Path -Parent -Path $MyInvocation.MyCommand.Path
$RENDER_SCRIPT = "C:\Users\K964\.gemini\antigravity\scratch\render_pdf_script.py"

# OneDrive folder where Power Automate will pick up the PDF.
# A subfolder "Market Digest" is created automatically.
$ONEDRIVE_DIR  = "C:\Users\K964\OneDrive - Shriram Finance Limited\Market Digest"
# ---------------------------------------------------------------------------

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# --- Setup -----------------------------------------------------------------
$LOG_FILE  = Join-Path $PROJECT_DIR "output\run_daily.log"
$TODAY     = Get-Date -Format "yyyy-MM-dd"
$TIMESTAMP = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

New-Item -ItemType Directory -Force -Path (Join-Path $PROJECT_DIR "output") | Out-Null
New-Item -ItemType Directory -Force -Path $ONEDRIVE_DIR | Out-Null

function Write-Log {
    param([string]$msg)
    $line = "[$(Get-Date -Format 'HH:mm:ss')] $msg"
    Write-Host $line
    try {
        [System.IO.File]::AppendAllText($LOG_FILE, "$line`r`n")
    } catch {
        Write-Warning "Failed to write to log file: $_"
    }
}

# --- Log header ------------------------------------------------------------
try {
    [System.IO.File]::AppendAllText($LOG_FILE, "`r`n" + ("=" * 60) + "`r`n  Market Digest run - $TIMESTAMP`r`n" + ("=" * 60) + "`r`n")
} catch {
    Write-Warning "Failed to write header to log file: $_"
}

# --- Step 1: Generate HTML report ------------------------------------------
Write-Log "Step 1/5 - Generating report HTML ..."
try {
    $result = & $PYTHON (Join-Path $PROJECT_DIR "generate_report.py") 2>&1
    $result | ForEach-Object { Write-Log "  $_" }
    Write-Log "Step 1 OK"
} catch {
    Write-Log "Step 1 FAILED: $_"
    exit 1
}

# --- Step 2: Render PDF ----------------------------------------------------
Write-Log "Step 2/5 - Rendering PDF ..."
try {
    $result = & $PYTHON $RENDER_SCRIPT 2>&1
    $result | ForEach-Object { Write-Log "  $_" }
    Write-Log "Step 2 OK"
} catch {
    Write-Log "Step 2 FAILED: $_"
    exit 1
}

# --- Step 3: Generate Podcast Audio ----------------------------------------
Write-Log "Step 3/5 - Generating Podcast Audio ..."
try {
    $result = & $PYTHON (Join-Path $PROJECT_DIR "generate_podcast.py") 2>&1
    $result | ForEach-Object { Write-Log "  $_" }
    Write-Log "Step 3 OK"
} catch {
    Write-Log "Warning: Podcast generation failed, continuing: $_"
}

# --- Step 4: Copy PDF to OneDrive ------------------------------------------
Write-Log "Step 4/5 - Copying PDF to OneDrive ..."
$PDF_SRC  = Join-Path $PROJECT_DIR "output\report.pdf"
$PDF_DEST = Join-Path $ONEDRIVE_DIR "Market-Digest-$TODAY.pdf"

if (-not (Test-Path $PDF_SRC)) {
    Write-Log "Step 4 FAILED: report.pdf not found at $PDF_SRC"
    exit 1
}

try {
    Copy-Item -Path $PDF_SRC -Destination $PDF_DEST -Force
    Write-Log "  Copied to: $PDF_DEST"
    Write-Log "Step 4 OK"
} catch {
    Write-Log "Step 4 FAILED: $_"
    exit 1
}

# --- Write ready.flag for local/cloud trigger backup -----------------------
$FLAG_FILE = Join-Path $ONEDRIVE_DIR "ready.flag"
$flagJson  = @{
    date     = $TODAY
    pdf_name = "Market-Digest-$TODAY.pdf"
    pdf_path = $PDF_DEST
    run_at   = $TIMESTAMP
} | ConvertTo-Json -Compress

try {
    [System.IO.File]::WriteAllText($FLAG_FILE, $flagJson)
    Write-Log "  Wrote ready.flag"
} catch {
    Write-Log "  Warning: Failed to write ready.flag: $_"
}

# --- Step 5: Share PDF and Podcast on Teams Group Chat --------------------
Write-Log "Step 5/5 - Sharing PDF and Podcast on Teams Group Chat..."
try {
    $result = & $PYTHON (Join-Path $PROJECT_DIR "post_to_teams.py") 2>&1
    $result | ForEach-Object { Write-Log "  $_" }
    Write-Log "Step 5 OK"
} catch {
    Write-Log "Step 5 FAILED: $_"
    exit 1
}

# --- Done ------------------------------------------------------------------
Write-Log "All steps complete. Report and Podcast ready and shared for $TODAY."
exit 0

