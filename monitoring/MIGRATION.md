# Migration Guide

Steps to copy historical data from the Synology NAS InfluxDB into the new local instance.
Complete the **First-time setup** section before migrating.

---

## First-time setup

### 1. Install Docker Desktop
Download from docker.com if not already installed. Make sure it is running.

### 2. Create your .env file
```
cd monitoring
copy .env.example .env
```
Edit `.env`:
- Set a strong `INFLUXDB_ADMIN_PASSWORD` and `GRAFANA_ADMIN_PASSWORD`
- Set `INFLUXDB_ADMIN_TOKEN` to the token from `configs/influxdb_credentials.json`
  (keeping the same token means the cutover only requires a URL change)
- Fill in the three `GRAFANA_CLOUD_*` values from your Grafana Cloud stack's
  Prometheus details page

### 3. Start the stack
```
cd monitoring
docker compose up -d
```
Wait ~30 seconds for InfluxDB to initialize, then check:
- InfluxDB UI:  http://localhost:8086  (login with INFLUXDB_ADMIN_USER / PASSWORD)
- Grafana:      http://localhost:3000  (login with GRAFANA_ADMIN_USER / PASSWORD)

The Grafana datasource and dashboard are provisioned automatically.

### 4. Create the `testing` bucket
The Python health-check writes to a bucket called `testing`. Create it once:
```
docker exec influxdb influx bucket create \
  --name testing \
  --org lics \
  --token YOUR_TOKEN_HERE
```

---

## Data migration from Synology NAS

### Step 1 — SSH into the Synology and identify the InfluxDB container
```bash
ssh YOUR_NAS_USER@YOUR_NAS_IP
sudo docker ps | grep -i influx
# Note the CONTAINER NAME or ID (left-most column)
```

### Step 2 — Create a backup inside the container
```bash
CONTAINER=<container-name-from-step-1>
TOKEN=dF1QV6oF05mb-0lSqOxQ69K8mum8Aba-dTdJ4psj5uM4KSpQTnKhB5QfoyxawnGjvDED_t8B_UVXzA0S4iAN0A==

sudo docker exec "$CONTAINER" influx backup /tmp/influx-backup \
  --host http://localhost:8086 \
  --token "$TOKEN"
```

### Step 3 — Copy the backup out of the container
```bash
sudo docker cp "$CONTAINER":/tmp/influx-backup ~/influx-backup
```

### Step 4 — Transfer to this Windows machine
Run this in Git Bash or PowerShell on the Windows machine:
```bash
scp -r YOUR_NAS_USER@YOUR_NAS_IP:~/influx-backup \
  "C:/Users/lics/Desktop/DatabaseDevelopment/monitoring/influx-backup"
```

### Step 5 — Copy backup into the new InfluxDB container
Run from the `monitoring/` directory:
```bash
docker cp influx-backup influxdb:/tmp/influx-backup
```

### Step 6 — Restore
```bash
TOKEN=dF1QV6oF05mb-0lSqOxQ69K8mum8Aba-dTdJ4psj5uM4KSpQTnKhB5QfoyxawnGjvDED_t8B_UVXzA0S4iAN0A==

docker exec influxdb influx restore /tmp/influx-backup \
  --host http://localhost:8086 \
  --token "$TOKEN" \
  --org lics
```

If you see "bucket already exists" errors for `mainLab`, that is fine — InfluxDB
will merge the restored data into the existing bucket. If restore fails entirely
on `mainLab`, delete it first and retry:
```bash
# Find the bucket ID
docker exec influxdb influx bucket list --org lics --token "$TOKEN"

# Delete and retry (replace <ID> with the mainLab bucket ID)
docker exec influxdb influx bucket delete --id <ID> --token "$TOKEN"

# Then rerun Step 6
```

### Step 7 — Verify in Grafana
Open http://localhost:3000, navigate to the "LICS Lab Environment" dashboard,
and extend the time range to see historical data.

---

## Cutover (switching live data to the new stack)

Only do this once the migration above is complete and you have verified
historical data looks correct in local Grafana.

**The only file you need to edit is `configs/influxdb_credentials.json`:**

Change:
```json
"url": "https://128.135.108.12:8086"
```
To:
```json
"url": "http://localhost:8087"
```

Then restart the heimdall server. Data will now flow:

```
Python sensor code
  → Telegraf (localhost:8087)
      → Local InfluxDB (full history, local Grafana)
      → Grafana Cloud (last 14 days, Prometheus remote write)
```

No other changes are needed — org, token, and bucket names are identical.

---

## Grafana Cloud dashboard setup

After cutover, metrics from your sensors will appear in Grafana Cloud with
Prometheus-sanitized names. Log into grafana.com and explore your metrics:
- Measurement `Temperature (C)` → metric name prefix `Temperature__C_`
- Measurement `Relative Humidity (%)` → metric name prefix `Relative_Humidity___`
- Tags (`Serial_Number`, `Device_Class`, `Parameter`) become Prometheus labels

Example PromQL to show all temperatures in Grafana Cloud:
```
{__name__=~"Temperature__C_.*", Device_Class="Dracal"}
```

Build a Grafana Cloud dashboard using these queries. It will only have data
from the cutover date onward (free tier has 14-day retention).

---

## Automated daily backups

Backups are handled by `monitoring/backup.ps1`. It runs `influx backup` against
the live container, copies the result to `C:/InfluxDB/backups/backup-YYYY-MM-DD/`,
and deletes folders older than 30 days.

### Schedule with Windows Task Scheduler

1. Open **Task Scheduler** (search in Start menu)
2. Click **Create Task** (not "Create Basic Task" — you need the full dialog)
3. **General tab**
   - Name: `InfluxDB Daily Backup`
   - Select **Run whether user is logged on or not**
   - Check **Run with highest privileges**
4. **Triggers tab** → New
   - Begin the task: **On a schedule** → Daily
   - Start time: pick an off-hours time, e.g. `03:00:00`
5. **Actions tab** → New
   - Program/script: `powershell.exe`
   - Add arguments:
     ```
     -NonInteractive -ExecutionPolicy Bypass -File "C:\Users\lics\Desktop\DatabaseDevelopment\monitoring\backup.ps1"
     ```
6. **Conditions tab**
   - Uncheck "Start the task only if the computer is on AC power" if this machine
     might be on battery
7. Click **OK** and enter your Windows password when prompted

### Test the script manually first

```powershell
powershell.exe -ExecutionPolicy Bypass -File "C:\Users\lics\Desktop\DatabaseDevelopment\monitoring\backup.ps1"
```

Check `C:/InfluxDB/backups/` for the output folder and `backup.log` for the run log.

To keep more or fewer days of history, pass `-RetainDays`:
```powershell
... -File ".\monitoring\backup.ps1" -RetainDays 60
```

---

## Cleanup

After cutover is stable, optionally stop the Synology InfluxDB via Container Manager.
The local stack auto-restarts on boot via Docker Desktop's startup settings.
