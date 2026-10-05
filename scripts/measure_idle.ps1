param([string]$Name = "MNIME", [int]$Seconds = 60, [string]$Scenario = "S1")
$p  = Get-Process -Name $Name | Sort-Object WorkingSet64 -Descending | Select-Object -First 1
if (-not $p) {
    Write-Output "Process $Name not found"
    exit 1
}
$c0 = $p.TotalProcessorTime.TotalSeconds
Start-Sleep -Seconds $Seconds
$p.Refresh()
$c1 = $p.TotalProcessorTime.TotalSeconds
[pscustomobject]@{
  scenario   = $Scenario
  ws_mb      = [math]::Round($p.WorkingSet64 / 1MB, 1)
  private_mb = [math]::Round($p.PrivateMemorySize64 / 1MB, 1)
  peak_ws_mb = [math]::Round($p.PeakWorkingSet64 / 1MB, 1)
  threads    = $p.Threads.Count
  handles    = $p.HandleCount
  cpu_pct    = [math]::Round(100 * ($c1 - $c0) / $Seconds / [Environment]::ProcessorCount, 3)
  cpu_s      = [math]::Round($c1 - $c0, 2)
} | ConvertTo-Json
