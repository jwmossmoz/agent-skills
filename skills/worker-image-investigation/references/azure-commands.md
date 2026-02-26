# Azure VM Investigation Commands

Common PowerShell commands to run on Azure VMs via `az vm run-command invoke`.

## System Information

### Windows Build Number
```powershell
(Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion').CurrentBuild
```

### Full Windows Version
```powershell
Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion' | Select-Object CurrentBuild, UBR, DisplayVersion
```

### GenericWorker Version
```powershell
Get-Content C:\generic-worker\generic-worker-info.json
```

### Installed Hotfixes
```powershell
Get-HotFix | Sort-Object InstalledOn -Descending | Select-Object -First 10 HotFixID, Description, InstalledOn
```

### File System Filter Drivers
```powershell
fltMC
```

### AppLocker Policy
```powershell
Get-AppLockerPolicy -Effective -Xml
```

## Process Information

### Running Processes
```powershell
Get-Process | Sort-Object CPU -Descending | Select-Object -First 20 Name, Id, CPU, WorkingSet
```

### Firefox/Test Processes
```powershell
Get-Process | Where-Object { $_.Name -match 'firefox|python|xpcshell' } | Select-Object Name, Id, CPU
```

## Network Information

### IPv6 Status
```powershell
Get-NetAdapterBinding -ComponentID ms_tcpip6
```

### Active Connections
```powershell
Get-NetTCPConnection -State Established | Select-Object -First 20
```

## Running Commands

Use `az vm run-command invoke` to execute:

```bash
az vm run-command invoke \
  --resource-group RG-TASKCLUSTER-WORKER-MANAGER-PRODUCTION \
  --name <VM_NAME> \
  --command-id RunPowerShellScript \
  --scripts "<POWERSHELL_COMMAND>"
```

## Resource Groups

| Environment | Resource Group |
|-------------|----------------|
| Production | `RG-TASKCLUSTER-WORKER-MANAGER-PRODUCTION` |
| Staging | `RG-TASKCLUSTER-WORKER-MANAGER-STAGING` |

## Creating Debug VMs

Spin up a throwaway VM from a worker pool image for hands-on debugging.

**Constraints:**
- VM name **must be ≤ 15 characters** (Windows NetBIOS limit)
- Always confirm `vmSize` from Taskcluster worker manager — never guess. Use the `/taskcluster` skill to look up the worker pool config and extract `vmSize` from `launchConfigs`.
- Use a simple password (`Password1!`) — these are throwaway VMs

### Create the VM

```bash
az vm create \
  --resource-group jmoss-win11 \
  --name "dbg-abc123" \
  --image "<image-id>" \
  --size "<vmSize>" \
  --admin-username azureuser \
  --admin-password "Password1!" \
  --location eastus
```

### Delete when done

```bash
az vm delete --resource-group jmoss-win11 \
  --name "dbg-abc123" --yes
```

## Finding VM Names

VM names can be found from:
1. Taskcluster task runs: `workerId` field (e.g., `vm-xyz...`)
2. `investigate.py workers <pool>` command
3. Azure portal
