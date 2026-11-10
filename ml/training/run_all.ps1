# ml/training/run_all.ps1
# End-to-end reproducible machine learning pipeline script for AdaptiveCloud.
# Acquires/bootstraps dataset, cleans and unifies labels, splits partitions,
# trains anomaly detector & 4 classifiers, evaluates on held-out test data,
# generates comparison rankings and confusion matrix plots.

[CmdletBinding()]
param(
    [switch]$ForceBootstrap,
    [double]$SampleRatio = 0.10,
    [switch]$SkipDbRegister
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent (Split-Path -Parent $ScriptDir)

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "   AdaptiveCloud Machine Learning Training Pipeline" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "Repository Root: $RepoRoot"

# Locate Python environment
$PythonCmd = "python"
$VenvPy = Join-Path $RepoRoot "backend\.venv\Scripts\python.exe"
if (Test-Path $VenvPy) {
    $PythonCmd = $VenvPy
    Write-Host "Using Virtual Environment Python: $PythonCmd" -ForegroundColor Green
}

Push-Location $RepoRoot
try {
    # 1. Acquire / Sample Data
    Write-Host "`n[Step 1/7] Preparing and caching dataset (Parquet)..." -ForegroundColor Yellow
    $dlArgs = @("ml\training\download_data.py", "--sample-ratio", $SampleRatio)
    if ($ForceBootstrap) {
        $dlArgs += "--bootstrap-sample"
    }
    & $PythonCmd @dlArgs

    # 2. Preprocess & Clean
    Write-Host "`n[Step 2/7] Preprocessing, deduplicating, and unifying attack labels..." -ForegroundColor Yellow
    & $PythonCmd "ml\training\preprocess.py"

    # 3. Stratified Partition Split
    Write-Host "`n[Step 3/7] Splitting stratified Train (70%), Validation (15%), Test (15%)..." -ForegroundColor Yellow
    & $PythonCmd "ml\training\split.py"

    # 4. Train Unsupervised Anomaly Detection (Isolation Forest)
    Write-Host "`n[Step 4/7] Training Isolation Forest on benign flow baseline..." -ForegroundColor Yellow
    & $PythonCmd "ml\training\train_anomaly.py"

    # 5. Train Supervised Classifiers (Random Forest, XGBoost, Decision Tree, SVM)
    Write-Host "`n[Step 5/7] Training multi-class intrusion classifiers..." -ForegroundColor Yellow
    & $PythonCmd "ml\training\train_classifiers.py"

    # 6. Evaluate on Held-out Test Data
    Write-Host "`n[Step 6/7] Evaluating all classifiers on held-out test set & plotting confusion matrices..." -ForegroundColor Yellow
    & $PythonCmd "ml\training\evaluate.py"

    # 7. Compare Models & Champion Selection
    Write-Host "`n[Step 7/7] Generating ml/models/comparison.json and ranking summary..." -ForegroundColor Yellow
    & $PythonCmd "ml\training\compare.py"

    # Optional DB registration
    if (-not $SkipDbRegister) {
        try {
            Write-Host "`nRegistering models and evaluations into database..." -ForegroundColor Yellow
            & $PythonCmd "ml\training\register_model.py"
        }
        catch {
            Write-Host "Database registration skipped (database may not be running locally)." -ForegroundColor Gray
        }
    }

    Write-Host "`n[SUCCESS] Pipeline execution complete! Trained models ready in ml/models/" -ForegroundColor Green
}
finally {
    Pop-Location
}

