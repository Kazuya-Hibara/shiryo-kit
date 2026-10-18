<#
shiryo-kit を Claude Code / Codex の skill フォルダに入れる (Windows)。

  powershell -ExecutionPolicy Bypass -File .\install.ps1           Claude Code と Codex の両方に入れる (コピー)
  powershell -ExecutionPolicy Bypass -File .\install.ps1 -Claude   Claude Code だけ (%USERPROFILE%\.claude\skills\shiryo-kit)
  powershell -ExecutionPolicy Bypass -File .\install.ps1 -Codex    Codex だけ       (%USERPROFILE%\.agents\skills\shiryo-kit)
  powershell -ExecutionPolicy Bypass -File .\install.ps1 -Link     コピーの代わりにリンク (ジャンクション) を張る

--claude / --codex / --link の書き方も受け付ける。
何度実行しても同じ結果になる。shiryo-kit 以外のフォルダには触らない。
同じ名前で中身が shiryo-kit でないフォルダがあれば、上書きせずに止める。
#>
[CmdletBinding(PositionalBinding = $false)]
param(
  [switch]$Claude,
  [switch]$Codex,
  [switch]$Link,
  [switch]$Help,
  [string]$HomeDir = [Environment]::GetFolderPath('UserProfile'),
  [Parameter(ValueFromRemainingArguments = $true)][string[]]$Rest
)
$ErrorActionPreference = 'Stop'

function Show-Usage {
  $lines = Get-Content -LiteralPath $PSCommandPath -Encoding UTF8
  $lines[1..10] | ForEach-Object { Write-Host $_ }
}

foreach ($a in $Rest) {
  switch ($a) {
    '--claude' { $Claude = $true }
    '--codex'  { $Codex = $true }
    '--link'   { $Link = $true }
    '--copy'   { $Link = $false }
    { $_ -in '--help', '-h' } { $Help = $true }
    default { Write-Host "知らない指定です: $a" -ForegroundColor Red; Show-Usage; exit 2 }
  }
}
if ($Help) { Show-Usage; exit 0 }
if (-not $Claude -and -not $Codex) { $Claude = $true; $Codex = $true }

$Src = Join-Path $PSScriptRoot 'skill\shiryo-kit'
$Skip = @('__pycache__', '.DS_Store')

# SKILL.md の frontmatter に name: shiryo-kit があるフォルダだけを shiryo-kit と認める
function Test-ShiryoDir([string]$Dir) {
  $skill = Join-Path $Dir 'SKILL.md'
  if (-not (Test-Path -LiteralPath $skill -PathType Leaf)) { return $false }
  $lines = Get-Content -LiteralPath $skill -Encoding UTF8 -TotalCount 40
  if ($lines.Count -eq 0 -or $lines[0].Trim() -ne '---') { return $false }
  for ($i = 1; $i -lt $lines.Count; $i++) {
    if ($lines[$i].Trim() -eq '---') { break }
    if ($lines[$i] -match '^name:\s*shiryo-kit\s*$') { return $true }
  }
  return $false
}

function Get-TreeFiles([string]$Root) {
  $rootFull = (Resolve-Path -LiteralPath $Root).Path.TrimEnd('\', '/')
  Get-ChildItem -LiteralPath $Root -Recurse -File -Force |
    Where-Object {
      $rel = $_.FullName.Substring($rootFull.Length + 1)
      -not ($rel.Split([IO.Path]::DirectorySeparatorChar) | Where-Object { $Skip -contains $_ }) -and
      $_.Extension -ne '.pyc'
    } |
    ForEach-Object { $_.FullName.Substring($rootFull.Length + 1) } |
    Sort-Object
}

function Test-SameTree([string]$A, [string]$B) {
  $fa = @(Get-TreeFiles $A)
  $fb = @(Get-TreeFiles $B)
  if (($fa -join "`n") -ne ($fb -join "`n")) { return $false }
  foreach ($rel in $fa) {
    $ha = (Get-FileHash -LiteralPath (Join-Path $A $rel) -Algorithm SHA256).Hash
    $hb = (Get-FileHash -LiteralPath (Join-Path $B $rel) -Algorithm SHA256).Hash
    if ($ha -ne $hb) { return $false }
  }
  return $true
}

function Test-IsLink([string]$Path) {
  $item = Get-Item -LiteralPath $Path -Force
  return [bool]($item.Attributes -band [IO.FileAttributes]::ReparsePoint)
}

function Remove-LinkOnly([string]$Path) {
  # リンク (ジャンクション・シンボリックリンク) だけを外す。リンク先の中身は消さない
  [IO.Directory]::Delete($Path, $false)
}

function Copy-Into([string]$Dest) {
  $tmp = "$Dest.shiryo-kit-tmp.$PID"
  if (Test-Path -LiteralPath $tmp) { Remove-Item -LiteralPath $tmp -Recurse -Force }
  Copy-Item -LiteralPath $Src -Destination $tmp -Recurse
  Get-ChildItem -LiteralPath $tmp -Recurse -Force |
    Where-Object { ($Skip -contains $_.Name) -or ($_.Extension -eq '.pyc') } |
    Sort-Object { $_.FullName.Length } -Descending |
    ForEach-Object { if (Test-Path -LiteralPath $_.FullName) { Remove-Item -LiteralPath $_.FullName -Recurse -Force } }
  if (Test-Path -LiteralPath $Dest) { Remove-Item -LiteralPath $Dest -Recurse -Force }
  Move-Item -LiteralPath $tmp -Destination $Dest
}

if (-not (Test-ShiryoDir $Src)) {
  Write-Host "skill のフォルダが見つかりません: $Src" -ForegroundColor Red
  Write-Host 'このスクリプトは shiryo-kit のフォルダの一番上 (install.ps1 がある所) に置いたまま実行してください。'
  exit 1
}
$SrcFull = (Resolve-Path -LiteralPath $Src).Path.TrimEnd('\')

$script:Failed = $false
function Install-One([string]$Label, [string]$Dest) {
  $parent = Split-Path -Parent $Dest
  if (Test-Path -LiteralPath $Dest) {
    if (Test-IsLink $Dest) {
      $target = @((Get-Item -LiteralPath $Dest -Force).Target)[0]
      $targetFull = $null
      if ($target -and (Test-Path -LiteralPath $target)) { $targetFull = (Resolve-Path -LiteralPath $target).Path.TrimEnd('\') }
      if ($targetFull -and ($targetFull -eq $SrcFull) -and $Link) {
        Write-Host "[$Label] そのまま (もうリンク済み): $Dest -> $SrcFull"
        return
      }
      if ($targetFull -and -not (Test-ShiryoDir $targetFull)) {
        Write-Host "[$Label] 止めました: $Dest は shiryo-kit ではないフォルダへのリンクです ($targetFull)。手で確かめてください。" -ForegroundColor Red
        $script:Failed = $true
        return
      }
      Remove-LinkOnly $Dest
      Write-Host "[$Label] 前のリンクを外しました: $Dest"
    }
    elseif (-not (Test-Path -LiteralPath $Dest -PathType Container) -or -not (Test-ShiryoDir $Dest)) {
      Write-Host "[$Label] 止めました: $Dest は shiryo-kit ではありません。上書きしないので、名前を変えるか中身を確かめてください。" -ForegroundColor Red
      $script:Failed = $true
      return
    }
    elseif (-not $Link -and (Test-SameTree $Src $Dest)) {
      Write-Host "[$Label] そのまま (最新と同じ): $Dest"
      return
    }
  }
  elseif ((Get-Item -LiteralPath $Dest -Force -ErrorAction SilentlyContinue)) {
    # 切れたリンク
    Remove-LinkOnly $Dest
    Write-Host "[$Label] 切れたリンクを外しました: $Dest"
  }

  New-Item -ItemType Directory -Path $parent -Force | Out-Null
  if ($Link) {
    if (Test-Path -LiteralPath $Dest) {
      Remove-Item -LiteralPath $Dest -Recurse -Force
      Write-Host "[$Label] 前のコピーを外しました: $Dest"
    }
    # ジャンクションは管理者権限なしで作れる
    New-Item -ItemType Junction -Path $Dest -Target $SrcFull | Out-Null
    Write-Host "[$Label] リンクを張りました: $Dest -> $SrcFull"
  }
  else {
    $existed = Test-Path -LiteralPath $Dest
    Copy-Into $Dest
    if ($existed) { Write-Host "[$Label] 新しい版に入れ替えました: $Dest" }
    else { Write-Host "[$Label] コピーしました: $Dest" }
  }
}

if ($Claude) { Install-One 'Claude Code' (Join-Path $HomeDir '.claude\skills\shiryo-kit') }
if ($Codex)  { Install-One 'Codex' (Join-Path $HomeDir '.agents\skills\shiryo-kit') }

if ($script:Failed) {
  Write-Host '一部を入れられませんでした (上の「止めました」を見てください)。' -ForegroundColor Red
  exit 1
}
Write-Host '終わりました。Claude Code / Codex を開き直してから「セミナー資料を作りたい」のように頼んでください。'
