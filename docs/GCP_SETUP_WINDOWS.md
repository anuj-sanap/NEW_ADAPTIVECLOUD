# Google Cloud Platform (GCP) Windows Worker VM Setup Guide

> [!CAUTION]
> **CRITICAL COST WARNING (GCP Trial Credit Management)**
> - **Windows Server Licensing Surcharge**: Windows Server carries a proprietary Microsoft OS license fee (~$0.023–$0.046/hour depending on vCPU count) which is charged **in addition** to base compute costs.
> - **Always Free Tier Limitation**: GCP's "Always Free" `e2-micro` allowance applies **strictly to Linux OS images only**. There is **NO free tier for Windows Server**.
> - **Preserving Your ₹0 Budget**: Every minute the Windows VM runs, it deducts from your GCP $300 (or equivalent) trial credits. **ALWAYS STOP the VM when not actively testing.**

---

## 1. Prerequisites (gcloud CLI on Windows)

Ensure Google Cloud SDK is installed on your Windows machine:
```powershell
gcloud --version
```
If not installed, run in PowerShell:
```powershell
winget install Google.CloudSDK
```
Authenticate and set your default configuration:
```powershell
gcloud auth login
```

---

## 2. Project Creation & Budget Alert Setup

### 2.1 Set Project ID
```powershell
$PROJECT_ID = "adaptivecloud-" + (Get-Random -Minimum 10000 -Maximum 99999)
gcloud projects create $PROJECT_ID --name="AdaptiveCloud Security"
gcloud config set project $PROJECT_ID
```
Ensure billing is linked to your project in the GCP Console:
`Billing > Account management > Link project`

### 2.2 Configure Budget Alerts (Console)
1. In GCP Console, open **Billing > Budgets & alerts**.
2. Click **Create Budget**:
   - Scope: Target your `adaptivecloud-xxxxx` project.
   - Amount: Set a Target budget (e.g. ₹500 or $10).
   - Threshold rules: Alert at **50%**, **90%**, and **100%**.
   - Notifications: Check **Email alerts to billing account admins**.
3. Save the budget.

---

## 3. Restrictive VPC Firewall Configuration

> [!IMPORTANT]
> Never open RDP (port 3389) to `0.0.0.0/0`. Automated Internet scanners will brute-force Windows Server within minutes. We restrict ingress exclusively to your current public IPv4 address.

### Step 3.1: Discover Your Current Public IP
```powershell
$MY_IP = (Invoke-RestMethod https://api.ipify.org).Trim()
Write-Host "Detected public IP: $MY_IP" -ForegroundColor Cyan
```

### Step 3.2: Create the Ingress Firewall Rule
```powershell
gcloud compute firewall-rules create allow-rdp-my-ip-only `
    --project=$PROJECT_ID `
    --direction=INGRESS `
    --priority=1000 `
    --network=default `
    --action=ALLOW `
    --rules=tcp:3389 `
    --source-ranges="$MY_IP/32" `
    --target-tags=windows-worker `
    --description="Allow RDP only from developer public IP"
```

---

## 4. Provision the Windows Server 2022 Worker VM

### 4.1 Specification
- **OS**: Windows Server 2022 Datacenter Edition (`windows-cloud/windows-2022`)
- **Machine Type**: `e2-medium` (2 vCPUs, 4 GB RAM — minimum required for Windows Server + Wazuh + Agent)
- **Disk**: 50 GB standard persistent disk (`pd-standard`)
- **Network Tag**: `windows-worker`

### 4.2 Creation Command
```powershell
gcloud compute instances create win-worker-01 `
    --project=$PROJECT_ID `
    --zone=us-central1-a `
    --machine-type=e2-medium `
    --image-family=windows-2022 `
    --image-project=windows-cloud `
    --boot-disk-size=50GB `
    --boot-disk-type=pd-standard `
    --tags=windows-worker `
    --metadata=enable-oslogin=FALSE
```

The VM takes approximately 2–3 minutes to finish Sysprep initialization.

---

## 5. Setting Windows Administrator Credentials

Use the secure `gcloud compute reset-windows-password` command. This uses the Google Compute Engine Windows guest agent to inject a cryptographically random password:

```powershell
gcloud compute reset-windows-password win-worker-01 `
    --zone=us-central1-a `
    --user=admin_analyst
```
Copy the printed password to your secure local clipboard.

---

## 6. Connecting via Remote Desktop (RDP)

1. Retrieve the public IP of the worker:
```powershell
$WORKER_IP = (gcloud compute instances describe win-worker-01 --zone=us-central1-a --format="value(networkInterfaces[0].accessConfigs[0].natIP)")
Write-Host "Connecting to $WORKER_IP via RDP..." -ForegroundColor Green
```

2. Launch Microsoft Remote Desktop Connection:
```powershell
mstsc /v:$WORKER_IP
```
3. Log in with:
   - **Username**: `admin_analyst`
   - **Password**: *(Password generated in Section 5)*

---

## 7. Saving Credits: Stopping and Starting the Worker

Whenever you take a break or stop development, **shut down the VM**:

### To Stop (Halts compute billing; standard disk cost is < $2/month):
```powershell
gcloud compute instances stop win-worker-01 --zone=us-central1-a
```

### To Restart (Resumes compute when you continue testing):
```powershell
gcloud compute instances start win-worker-01 --zone=us-central1-a
```
*Note*: When the VM starts, its external public IP may change unless static. Check with:
```powershell
gcloud compute instances describe win-worker-01 --zone=us-central1-a --format="value(networkInterfaces[0].accessConfigs[0].natIP)"
```
*(Once Tailscale is configured as described in `docs/TAILSCALE_SETUP.md`, the VM maintains a constant Tailscale IP regardless of external IP churn!)*

---

## 8. Complete Project Teardown

To release all disks, IPs, and compute resources completely:
```powershell
.\scripts\gcp_teardown.ps1
```

