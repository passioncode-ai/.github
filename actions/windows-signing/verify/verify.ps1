# Every file must carry a Valid Authenticode signature with an RFC 3161 timestamp, from the
# expected signer when one is named; the report (JSON) goes where the caller says, for the
# product's receipt. Exits non-zero and names the file otherwise.
#
# Why the timestamp is required: Azure Artifact Signing issues certificates that live about three
# days. A signature without a timestamp stops validating when its certificate expires, so a
# release would turn "unsigned" for every user three days after it shipped.
param(
  [Parameter(Mandatory = $true)][string]$Files,
  [Parameter(Mandatory = $true)][string]$Out,
  [string]$ExpectedSubject = ''
)
$ErrorActionPreference = 'Stop'

$paths = @()
foreach ($line in ($Files -split "`r?`n")) {
  $pattern = $line.Trim()
  if ($pattern -eq '') { continue }
  $found = @(Get-ChildItem -Path $pattern -File -ErrorAction SilentlyContinue)
  if ($found.Count -eq 0) { throw "windows-signing/verify: no file matches $pattern" }
  $paths += $found.FullName
}
if ($paths.Count -eq 0) { throw 'windows-signing/verify: no files given' }

$report = foreach ($path in $paths) {
  $sig = Get-AuthenticodeSignature -FilePath $path
  $name = Split-Path $path -Leaf
  $subject = if ($sig.SignerCertificate) { $sig.SignerCertificate.Subject } else { '' }
  $stamper = if ($sig.TimeStamperCertificate) { $sig.TimeStamperCertificate.Subject } else { '' }
  Write-Host "${name}: $($sig.Status); signer: $subject; timestamp: $stamper"
  if ("$($sig.Status)" -ne 'Valid') { throw "windows-signing/verify: Authenticode status of $name is $($sig.Status), not Valid" }
  if ($stamper -eq '') { throw "windows-signing/verify: $name has no timestamp; it would stop validating when its short-lived certificate expires" }
  if ($ExpectedSubject -ne '' -and -not $subject.Contains($ExpectedSubject)) {
    throw "windows-signing/verify: $name is signed by '$subject', not by '$ExpectedSubject'"
  }
  [pscustomobject]@{
    file        = $name
    status      = "$($sig.Status)"
    signer      = $subject
    thumbprint  = $sig.SignerCertificate.Thumbprint
    timestamper = $stamper
    sha256      = (Get-FileHash -Algorithm SHA256 -Path $path).Hash.ToLowerInvariant()
  }
}
$dir = Split-Path -Parent $Out
if ($dir -and -not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir | Out-Null }
ConvertTo-Json -InputObject @($report) -Depth 3 | Set-Content -Encoding utf8 -Path $Out
Write-Host "windows-signing/verify: $($paths.Count) file(s) Valid and timestamped; report $Out"
