param()

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$root = Split-Path -Parent $PSScriptRoot

function Assert-Condition {
    param([bool]$Condition, [string]$Message)
    if (-not $Condition) {
        throw $Message
    }
}

function Read-Json {
    param([string]$Path)
    Assert-Condition (Test-Path -LiteralPath $Path -PathType Leaf) "Missing file: $Path"
    return Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
}

$claudeCatalogPath = Join-Path $root ".claude-plugin/marketplace.json"
$codexCatalogPath = Join-Path $root ".agents/plugins/marketplace.json"
$claudeManifestPath = Join-Path $root "plugins/compass/.claude-plugin/plugin.json"
$codexManifestPath = Join-Path $root "plugins/compass/plugin.json"
$claudeCatalog = Read-Json $claudeCatalogPath
$codexCatalog = Read-Json $codexCatalogPath
$claudeManifest = Read-Json $claudeManifestPath
$codexManifest = Read-Json $codexManifestPath

Assert-Condition ($claudeCatalog.name -eq "rule-driven-compass") "Claude marketplace name does not match the documented install identifier."
Assert-Condition ($codexCatalog.name -eq "rule-driven-compass") "Codex marketplace name does not match the documented install identifier."
Assert-Condition ($claudeCatalog.plugins.Count -eq 1) "Expected exactly one Claude marketplace plugin."
Assert-Condition ($claudeCatalog.plugins[0].name -eq "compass") "Claude plugin identifier must be compass."
Assert-Condition ($claudeCatalog.plugins[0].source -eq "./plugins/compass") "Claude marketplace must use the shared local plugin path."
Assert-Condition ($codexCatalog.plugins.Count -eq 1) "Expected exactly one Codex marketplace plugin."
Assert-Condition ($codexCatalog.plugins[0].name -eq "compass") "Codex plugin identifier must be compass."
Assert-Condition ($codexCatalog.plugins[0].source.source -eq "local") "Codex marketplace source must be local."
Assert-Condition ($codexCatalog.plugins[0].source.path -eq "./plugins/compass") "Codex marketplace must use the shared local plugin path."
Assert-Condition ($claudeManifest.name -eq "compass") "Claude manifest name must be compass."
Assert-Condition ($codexManifest.name -eq $claudeManifest.name) "Claude and Codex plugin identifiers differ."
Assert-Condition ($claudeManifest.version -eq $codexManifest.version) "Claude and Codex plugin versions differ."
Assert-Condition ($claudeCatalog.plugins[0].version -eq $codexManifest.version) "Claude catalog version differs from the plugin version."
Assert-Condition (-not (Test-Path -LiteralPath (Join-Path $root "plugins/compass/hooks"))) "The shared package must not ship hooks."
Assert-Condition (-not (Test-Path -LiteralPath (Join-Path $root "plugins/compass/.mcp.json"))) "The shared package must not ship MCP server configuration."

$skillRoot = Join-Path $root "plugins/compass/skills"
$skillFolders = @(Get-ChildItem -LiteralPath $skillRoot -Directory)
$expectedSkills = @("compass-workflow", "compass-setup", "compass-remove-project")
$actualSkills = @($skillFolders | ForEach-Object { $_.Name } | Sort-Object)
Assert-Condition (($actualSkills -join ",") -eq (($expectedSkills | Sort-Object) -join ",")) "Skill folder names differ from the expected package."

foreach ($folder in $skillFolders) {
    $skillPath = Join-Path $folder.FullName "SKILL.md"
    Assert-Condition (Test-Path -LiteralPath $skillPath -PathType Leaf) "Missing SKILL.md: $skillPath"
    $body = Get-Content -LiteralPath $skillPath -Raw
    $frontMatter = [regex]::Match($body, "\A---\r?\n(?<yaml>.*?)\r?\n---", [Text.RegularExpressions.RegexOptions]::Singleline)
    Assert-Condition $frontMatter.Success "Missing YAML frontmatter: $skillPath"
    $skillName = [regex]::Match($frontMatter.Groups["yaml"].Value, "(?m)^name:\s*([A-Za-z0-9-]+)\s*$")
    $description = [regex]::Match($frontMatter.Groups["yaml"].Value, "(?m)^description:\s*.+$")
    Assert-Condition ($skillName.Success -and $skillName.Groups[1].Value -eq $folder.Name) "Skill name must match its directory: $skillPath"
    Assert-Condition $description.Success "Skill description is missing: $skillPath"

    foreach ($match in [regex]::Matches($body, "references/[A-Za-z0-9_./-]+")) {
        $reference = $match.Value.TrimEnd(".", ",", ")", ":", ";")
        $referencePath = Join-Path $folder.FullName $reference
        Assert-Condition (Test-Path -LiteralPath $referencePath -PathType Leaf) "Missing skill reference $reference in $skillPath"
    }
}

foreach ($document in Get-ChildItem -LiteralPath $root -Recurse -File -Filter "*.md") {
    if ($document.FullName -match "[\\/]\.git[\\/]") {
        continue
    }
    $body = Get-Content -LiteralPath $document.FullName -Raw
    foreach ($match in [regex]::Matches($body, "\]\((?<target>[^)]+)\)")) {
        $target = $match.Groups["target"].Value.Split("#")[0]
        if ([string]::IsNullOrWhiteSpace($target) -or $target -match "^(https?|mailto):") {
            continue
        }
        $target = [Uri]::UnescapeDataString($target)
        $resolved = [IO.Path]::GetFullPath((Join-Path $document.DirectoryName $target))
        Assert-Condition (Test-Path -LiteralPath $resolved) "Broken local Markdown link in $($document.FullName): $target"
    }
}

Write-Output "VALID: marketplace manifests, shared plugin paths, versions, skill frontmatter, references, and local Markdown links."
