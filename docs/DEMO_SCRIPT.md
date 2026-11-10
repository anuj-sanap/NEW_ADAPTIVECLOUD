# AdaptiveCloud - 10-Minute Live Demonstration Script & Demo Day Checklist
**For Final Evaluation, Academic Defence, and Stakeholder Presentations**

---

## 1. Demo Day Pre-Flight Checklist

Complete these verification steps **30 minutes prior** to the presentation:

- [ ] **1. Workstation Host Check**:
  - Windows PC online with PowerShell 7 and Docker Desktop running.
  - Tailscale running with mesh IP verified (`tailscale ip -4`).
- [ ] **2. Cloud Worker VM Check**:
  - If GCP VM was stopped, start it:
    ```powershell
    gcloud compute instances start adaptivecloud-worker-01 --zone us-central1-a
    ```
  - Verify worker reaches control stack via Tailscale ping:
    ```powershell
    tailscale ping <worker-tailscale-ip>
    ```
- [ ] **3. Control Stack Startup**:
  - Launch production containers:
    ```powershell
    pwsh -File .\scripts\tasks.ps1 -Task up
    ```
- [ ] **4. Run Automated Healthcheck**:
  - Run the full verification suite to ensure all 11 subsystems are GREEN:
    ```powershell
    pwsh -File .\scripts\tasks.ps1 -Task e2e
    ```
- [ ] **5. Browser Setup**:
  - Open Chrome to `https://localhost` (or `https://100.64.0.10`).
  - Log in with `admin` / `password123`.
  - Maximize browser window (F11 or full screen).

---

## 2. 10-Minute Demonstration Flow & Talk Track

```
TIMELINE BREAKDOWN:
[00:00 - 02:00]  Act I: Executive Overview & Problem Context
[02:00 - 04:00]  Act II: Real-time Telemetry & Fleet Visibility
[04:00 - 06:00]  Act III: Live Attack Trigger & Instant ML Classification
[06:00 - 07:15]  Act IV: Automated Forensic Root Cause Analysis (RCA)
[07:15 - 08:30]  Act V: Automated Response Countermeasures & Rollback
[08:30 - 09:30]  Act VI: Threat Forecasting & Predictive Maintenance
[09:30 - 10:00]  Act VII: Active Learning & Champion Governance + Q&A
```

---

### Act I: Executive Overview & Problem Context (0:00 - 2:00)
**Screen**: Executive Overview Page (`/`)

> **Presenter Talk Track**:  
> *"Good morning committee members and colleagues. Today, cloud security operations are overwhelmed by alert fatigue, disparate telemetry tools, and expensive subscription licensing. Small-to-medium teams cannot afford enterprise SIEMs that cost thousands of dollars per month.*  
>  
> *Here is **AdaptiveCloud**: an autonomous, zero-budget cloud security and predictive maintenance platform engineered from scratch for hybrid Windows Server cloud environments.*  
>  
> *Looking at our Executive Dashboard right now, we see our **System Health Score at 98%**, our 4 KPI stat tiles showing active incidents, attacks blocked today, the highest forecasted risk, and our active production ML model.*  
>  
> *Notice our 'What Needs Attention' panel: it translates raw database metrics into concise, plain-English intelligence that any IT Director or Head of Department can immediately act upon."*

---

### Act II: Real-time Telemetry & Infrastructure Health (2:00 - 4:00)
**Screen**: System Monitoring Page (`/monitoring`)

> **Presenter Talk Track**:  
> *"Let's navigate to System Monitoring. Here we observe our live fleet. We have our Windows Server 2022 worker node hosted in Google Cloud Platform.*  
>  
> *Through a private, zero-cost Tailscale WireGuard mesh, the worker's native Python agent streams live telemetry over WebSockets into our frontend dashboard every 2 seconds.*  
>  
> *Notice these live radial gauges tracking CPU, memory, and disk load in real time, along with the health status of critical Windows services like Time Sync, DNS Cache, and Workstation. No polling, zero mock data — everything you see is live streaming telemetry from our cloud instance."*

---

### Act III: Live Attack Trigger & Instant ML Classification (4:00 - 6:00)
**Action**: Split screen with PowerShell terminal. Execute safe port scan simulation:
```powershell
pwsh -File .\scripts\simulate\port_scan.ps1 -TargetIp 100.64.0.50 -DurationSec 5
```
**Screen**: Switch to Attack Detections (`/detections`) & Classifications (`/classifications`)

> **Presenter Talk Track**:  
> *"Now, let's test our defense capabilities under fire. In this terminal, I will launch an authorized, bounded TCP port sweep against our worker node.*  
>  
> *[Trigger script]*  
>  
> *Immediately within 50 milliseconds, our unsupervised Isolation Forest model detects that packet rates have spiked beyond normal baselines. Watch the Detections page update in real time.*  
>  
> *Next, our Universal Feature Bridge feeds the 28 canonical flow features into our trained XGBoost classifier. Looking at the Classifications page, the attack is categorized with **99% confidence as a `port_scan`**. The system has automatically correlated this into a high-severity security incident."*

---

### Act IV: Automated Forensic Root Cause Analysis (6:00 - 7:15)
**Screen**: Forensic RCA Page (`/rca`), clicking on the latest generated incident.

> **Presenter Talk Track**:  
> *"In a standard SOC, triaging this alert takes 30 to 45 minutes of manual log analysis. In AdaptiveCloud, our forensic engine builds an instant Root Cause Analysis.*  
>  
> *Here is the chronologically ordered timeline: it joins the metric spike with the network flow burst and the correlated Windows Event IDs.*  
>  
> *Notice the Probable Cause statement: it transparently explains why this alert occurred. And look below: it automatically generates an exact, copy-pasteable PowerShell script using `netsh advfirewall` to isolate the attacker's IP without manual human scripting."*

---

### Act V: Automated Countermeasures & Rollback (7:15 - 8:30)
**Screen**: Automated Responses Page (`/responses`)

> **Presenter Talk Track**:  
> *"Now let's examine our automated containment engine. Rather than relying on slow human intervention, AdaptiveCloud's response engine can automatically enforce quarantine.*  
>  
> *Here on the Responses page, we see the attacker's IP quarantined in the blocklist with an automatic 30-minute time-to-live. Notice our safety rails: our control server and local subnet are protected by an immutable allowlist.*  
>  
> *And if an administrator determines an action was a false positive, a single click on this 'Rollback' button instantly instructs the Windows worker agent to revoke the firewall rule and restore traffic."*

---

### Act VI: Threat Forecasting & Predictive Maintenance (8:30 - 9:30)
**Screen**: Threat Forecasting (`/threat-prediction`) & Maintenance (`/maintenance`)

> **Presenter Talk Track**:  
> *"Security is only half the battle; infrastructure reliability is the other. AdaptiveCloud uses predictive modeling to stop outages before they happen.*  
>  
> *On the Threat Forecasting page, our autoregressive models predict the probability of attacks occurring in the next 15 and 60 minutes based on historical attack cadence. If insufficient data is collected, notice our cold-start progress indicator — we never fabricate predictions.*  
>  
> *On the Predictive Maintenance page, our Theil-Sen linear estimator analyzes disk telemetry trends to project the exact number of days remaining before disk saturation reaches 95%. This allows IT teams to schedule maintenance days in advance rather than responding to emergency midnight disk crashes."*

---

### Act VII: Active Learning & Champion Governance (9:30 - 10:00)
**Screen**: Models & Learning Page (`/models-learning`)

> **Presenter Talk Track**:  
> *"Finally, we solve the domain gap problem. Machine learning models decay over time as network traffic patterns evolve.*  
>  
> *Here on the Models & Learning page, our Population Stability Index (PSI) monitors feature drift across every flow stream. If drift is detected, an administrator can click 'Trigger Retraining'.*  
>  
> *The candidate model is trained on combined historical data plus analyst ground-truth feedback. If the Challenger outperforms our active Champion F1-score, it is safely promoted with zero downtime.*  
>  
> *To summarize: AdaptiveCloud delivers end-to-end detection, automated forensics, predictive maintenance, and active adaptation — all running securely on a strict ₹0 budget. Thank you, and I welcome your questions."*

---

## 3. Post-Demo Teardown (Credit Protection)

Immediately after completing the presentation, execute the teardown commands to prevent unneeded billing:

```powershell
# 1. Stop the GCP VM to halt Windows Server hourly licensing
pwsh -File .\scripts\gcp_teardown.ps1 -ProjectId "your-gcp-project-id" -InstanceName "adaptivecloud-worker-01"

# 2. Halt local Docker containers
pwsh -File .\scripts\tasks.ps1 -Task down
```
