param(
    [string]$ProjectRoot = "C:\Proyectos\Software-PA-backend-logica",
    [Parameter(Mandatory=$true)]
    [string]$PackageRoot,
    [string]$DbContainer = "software-pa-db-1",
    [string]$DbUser = "pa_app"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$ProtectedDatabases = @(
    "db_carga_excel",
    "db_pruebas_alfredo"
)

function Get-Sha256([string]$Path) {
    return (
        (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash
    ).Trim().ToLowerInvariant()
}

function Assert-FileHash(
    [string]$Path,
    [string]$Expected,
    [string]$Label
) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "Falta $Label`: $Path"
    }

    $Actual = Get-Sha256 $Path
    $ExpectedNormalized = ([string]$Expected).Trim().ToLowerInvariant()

    if ($Actual -ne $ExpectedNormalized) {
        throw "$Label cambió. esperado=$ExpectedNormalized actual=$Actual"
    }
}

if (-not (Test-Path -LiteralPath $PackageRoot -PathType Container)) {
    throw "No existe PackageRoot: $PackageRoot"
}

$ManifestPath = Join-Path $PackageRoot "manifest.json"
$ManifestShaPath = Join-Path $PackageRoot "manifest.sha256.txt"

if (-not (Test-Path -LiteralPath $ManifestPath -PathType Leaf)) {
    throw "Falta manifest.json."
}
if (-not (Test-Path -LiteralPath $ManifestShaPath -PathType Leaf)) {
    throw "Falta manifest.sha256.txt."
}

# ----------------------------------------------------------------------
# 1. Verificar que el paquete congelado no cambió.
# ----------------------------------------------------------------------
$ManifestShaLine = (
    Get-Content -LiteralPath $ManifestShaPath -Raw -Encoding ASCII
).Trim()

if ($ManifestShaLine -notmatch '^([0-9a-fA-F]{64})\s+manifest\.json$') {
    throw "Formato inválido de manifest.sha256.txt."
}
$ExpectedManifestSha = $Matches[1].ToLowerInvariant()
Assert-FileHash $ManifestPath $ExpectedManifestSha "manifest.json"

$Manifest = Get-Content -LiteralPath $ManifestPath -Raw -Encoding UTF8 |
    ConvertFrom-Json

if ([string]$Manifest.status -ne "CANDIDATO_CONGELADO_PENDIENTE_RESTORECHECK") {
    throw "Estado de manifest inesperado: $($Manifest.status)"
}
if ([string]$Manifest.source_database -ne "db_carga_excel") {
    throw "El paquete no proviene de db_carga_excel."
}
if ([string]$Manifest.schema_version -ne "018") {
    throw "El paquete no corresponde a schema 018."
}
if ([string]$Manifest.project_key -ne "MEX-QRO") {
    throw "El paquete no corresponde a MEX-QRO."
}
if ([string]$Manifest.audit.result -ne "PASS" -or [int]$Manifest.audit.fail -ne 0) {
    throw "El paquete no tiene auditoría global PASS/FAIL=0."
}
if (-not [bool]$Manifest.dump.acl_included) {
    throw "El paquete no incluye ACLs; no es apto para restore-check runtime."
}
if ([string]$Manifest.dump.runtime_role -ne "software_pa_app") {
    throw "El paquete no declara software_pa_app como rol runtime estable."
}

# Verificar cada archivo registrado en el manifest.
foreach ($entry in $Manifest.files) {
    $Relative = ([string]$entry.relative_path).Replace("/", "\")
    $FilePath = Join-Path $PackageRoot $Relative
    Assert-FileHash $FilePath ([string]$entry.sha256) "archivo del paquete $Relative"

    $Size = (Get-Item -LiteralPath $FilePath).Length
    if ([Int64]$Size -ne [Int64]$entry.size_bytes) {
        throw "Tamaño cambió para $Relative. esperado=$($entry.size_bytes) actual=$Size"
    }
}

$DumpRelative = ([string]$Manifest.dump.file).Replace("/", "\")
$DumpPath = Join-Path $PackageRoot $DumpRelative
Assert-FileHash $DumpPath ([string]$Manifest.dump.sha256) "dump PostgreSQL"

$ExcelPath = Join-Path $PackageRoot "fuente\mq_colectivos.xlsx"
$ResolutionPath = Join-Path $PackageRoot "evidencia\resolucion_seguimiento_post_reparaciones.csv"

Assert-FileHash $ExcelPath ([string]$Manifest.excel_sha256) "Excel congelado"
Assert-FileHash $ResolutionPath ([string]$Manifest.resolution_2j_sha256) "resolución 2J congelada"

# ----------------------------------------------------------------------
# 2. Validar wrapper/auditor host-side.
# ----------------------------------------------------------------------
$ScriptsRoot = Join-Path $ProjectRoot "backend\scripts"
$AuditScript = Join-Path $ScriptsRoot "auditoria_global_migracion_mq.py"
$WrapperScript = Join-Path $ScriptsRoot "auditoria_global_restorecheck_mq.py"

foreach ($required in @($AuditScript, $WrapperScript)) {
    if (-not (Test-Path -LiteralPath $required -PathType Leaf)) {
        throw "Falta script requerido: $required"
    }
}

# El auditor usado en el restore-check debe ser byte a byte el congelado.
$FrozenAuditor = Join-Path $PackageRoot "scripts\auditoria_global_migracion_mq.py"
$FrozenAuditorSha = Get-Sha256 $FrozenAuditor
$HostAuditorSha = Get-Sha256 $AuditScript

if ($FrozenAuditorSha -ne $HostAuditorSha) {
    throw "El auditor host cambió respecto al paquete congelado. frozen=$FrozenAuditorSha host=$HostAuditorSha"
}

# ----------------------------------------------------------------------
# 3. Crear nombre efímero seguro.
# ----------------------------------------------------------------------
$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$RestoreDb = "db_carga_excel_restorecheck_$Stamp"

if ($ProtectedDatabases -contains $RestoreDb) {
    throw "Nombre de restore-check colisionó con una BD protegida."
}

if ($RestoreDb -notmatch '^db_carga_excel_restorecheck_[0-9]{8}_[0-9]{6}$') {
    throw "Nombre temporal fuera del patrón permitido: $RestoreDb"
}

$Exists = (
    docker exec $DbContainer psql `
        -U $DbUser `
        -d postgres `
        -Atc "SELECT COUNT(*) FROM pg_database WHERE datname='$RestoreDb';"
).Trim()

if ($LASTEXITCODE -ne 0) {
    throw "No se pudo consultar pg_database."
}
if ($Exists -ne "0") {
    throw "La BD temporal ya existe: $RestoreDb"
}

# ----------------------------------------------------------------------
# 4. Preparar evidencia FUERA del paquete congelado.
# ----------------------------------------------------------------------
$PackageName = Split-Path -Leaf $PackageRoot
$PromotionRoot = Split-Path -Parent (Split-Path -Parent $PackageRoot)
$RestoreResultsRoot = Join-Path $PromotionRoot "restorechecks\$PackageName\$Stamp"
New-Item -ItemType Directory -Path $RestoreResultsRoot -Force | Out-Null

$TranscriptPath = Join-Path $RestoreResultsRoot "restorecheck_console.txt"
$ResultJsonPath = Join-Path $RestoreResultsRoot "restorecheck_result.json"

$ContainerDump = "/tmp/restorecheck_$Stamp.dump"
$CreatedDb = $false
$AuditExit = $null

try {
    Write-Host "=== RESTORE-CHECK AISLADO MEX-QRO ==="
    Write-Host "Paquete:          $PackageRoot"
    Write-Host "Manifest SHA-256: $ExpectedManifestSha"
    Write-Host "Dump SHA-256:     $($Manifest.dump.sha256)"
    Write-Host "BD temporal:      $RestoreDb"
    Write-Host ""

    # Copiar el dump congelado al contenedor PostgreSQL.
    docker cp $DumpPath "${DbContainer}:${ContainerDump}"
    if ($LASTEXITCODE -ne 0) {
        throw "docker cp del dump falló."
    }

    # Crear la base efímera. No toca ninguna de las dos bases protegidas.
    docker exec $DbContainer createdb `
        -U $DbUser `
        -O $DbUser `
        $RestoreDb

    if ($LASTEXITCODE -ne 0) {
        throw "createdb falló para $RestoreDb."
    }
    $CreatedDb = $true

    # Restaurar exactamente el dump congelado.
    # Se conserva --no-owner para que pa_app sea propietario de los objetos,
    # pero NO se usa --no-acl: las ACLs del rol software_pa_app forman parte
    # del contrato operativo que estamos verificando.
    docker exec $DbContainer pg_restore `
        -U $DbUser `
        -d $RestoreDb `
        --no-owner `
        --exit-on-error `
        $ContainerDump

    if ($LASTEXITCODE -ne 0) {
        throw "pg_restore falló."
    }

    # Comprobación básica antes de la auditoría completa.
    $RestoredSchema = (
        docker exec $DbContainer psql `
            -U $DbUser `
            -d $RestoreDb `
            -Atc "SELECT max(version) FROM schema_migrations;"
    ).Trim()

    if ($LASTEXITCODE -ne 0 -or $RestoredSchema -ne "018") {
        throw "Schema restaurado inesperado: '$RestoredSchema'."
    }

    $RestoredProject = (
        docker exec $DbContainer psql `
            -U $DbUser `
            -d $RestoreDb `
            -Atc "SELECT COUNT(*) FROM proyecto WHERE activo IS TRUE AND clave_proyecto='MEX-QRO';"
    ).Trim()

    if ($LASTEXITCODE -ne 0 -or $RestoredProject -ne "1") {
        throw "La restauración no contiene exactamente un MEX-QRO activo."
    }

    # Contrato de ACL restaurado: si esto falla, el dump no reproduce
    # correctamente el entorno runtime aunque los datos estén presentes.
    $RestoredRuntimeAcl = (
        docker exec $DbContainer psql `
            -U $DbUser `
            -d $RestoreDb `
            -Atc "SELECT has_schema_privilege('software_pa_app','public','USAGE') AND has_table_privilege('software_pa_app','public.schema_migrations','SELECT') AND NOT has_table_privilege('software_pa_app','public.schema_migrations','INSERT') AND has_table_privilege('software_pa_app','public.proyecto','SELECT') AND has_table_privilege('software_pa_app','public.proyecto','INSERT') AND has_table_privilege('software_pa_app','public.proyecto','UPDATE') AND NOT has_table_privilege('software_pa_app','public.proyecto','DELETE') AND has_table_privilege('software_pa_app','public.bitacora','SELECT') AND NOT has_table_privilege('software_pa_app','public.bitacora','INSERT') AND NOT has_table_privilege('software_pa_app','public.bitacora','UPDATE');"
    ).Trim()

    if ($LASTEXITCODE -ne 0 -or $RestoredRuntimeAcl -ne "t") {
        throw "Las ACLs runtime no quedaron restauradas conforme al contrato."
    }

    # Calcular rutas /data/... usando PackageRoot relativo a data\importacion.
    $ImportRoot = Join-Path $ProjectRoot "data\importacion"
    $ImportRootFull = [System.IO.Path]::GetFullPath($ImportRoot)
    $PackageFull = [System.IO.Path]::GetFullPath($PackageRoot)

    if (-not $PackageFull.StartsWith(
        $ImportRootFull,
        [System.StringComparison]::OrdinalIgnoreCase
    )) {
        throw "PackageRoot debe vivir bajo data\importacion."
    }

    $RelativePackage = $PackageFull.Substring($ImportRootFull.Length).TrimStart('\')
    $DockerPackage = "/data/" + ($RelativePackage -replace '\\','/')

    $DockerExcel = "$DockerPackage/fuente/mq_colectivos.xlsx"
    $DockerResolution = "$DockerPackage/evidencia/resolucion_seguimiento_post_reparaciones.csv"

    # El output de la auditoría se manda a una carpeta temporal normal del
    # árbol de importación, NO al paquete congelado.
    $RestoreResultsFull = [System.IO.Path]::GetFullPath($RestoreResultsRoot)
    if (-not $RestoreResultsFull.StartsWith(
        $ImportRootFull,
        [System.StringComparison]::OrdinalIgnoreCase
    )) {
        throw "La evidencia restore-check debe vivir bajo data\importacion."
    }
    $RelativeOutput = $RestoreResultsFull.Substring($ImportRootFull.Length).TrimStart('\')
    $DockerOutput = "/data/" + ($RelativeOutput -replace '\\','/')

    # Ejecutar exactamente la misma auditoría, permitiendo sólo el nombre
    # efímero mediante el wrapper.
    $ComposeArgs = @(
        "compose",
        "--env-file", "C:\Proyectos\Software-PA\.env",
        "-p", "software-pa",
        "run", "--rm", "--no-deps",
        "-e", "DB_NAME=$RestoreDb",
        "-e", "RESTORECHECK_DB_NAME=$RestoreDb",
        "-v", "$ScriptsRoot`:/app/scripts:ro",
        "-v", "$ImportRoot`:/data",
        "backend",
        "python",
        "/app/scripts/auditoria_global_restorecheck_mq.py",
        $DockerExcel,
        "--resolution-2j", $DockerResolution,
        "--output-dir", $DockerOutput
    )

    # PowerShell 5.1 puede convertir cualquier texto de stderr de un
    # ejecutable nativo en NativeCommandError cuando ErrorActionPreference=Stop.
    # docker compose escribe warnings inocuos (p.ej. orphan containers) a stderr
    # aun con exit code 0. Capturamos stdout/stderr por separado y decidimos
    # exclusivamente con el exit code real del proceso.
    $AuditStdoutPath = Join-Path $RestoreResultsRoot "audit_stdout.txt"
    $AuditStderrPath = Join-Path $RestoreResultsRoot "audit_stderr.txt"

    $DockerProcess = Start-Process `
        -FilePath "docker.exe" `
        -ArgumentList $ComposeArgs `
        -NoNewWindow `
        -Wait `
        -PassThru `
        -RedirectStandardOutput $AuditStdoutPath `
        -RedirectStandardError $AuditStderrPath

    $AuditExit = $DockerProcess.ExitCode

    $AuditStdout = @()
    $AuditStderr = @()

    if (Test-Path -LiteralPath $AuditStdoutPath) {
        $AuditStdout = @(Get-Content -LiteralPath $AuditStdoutPath -Encoding UTF8)
    }
    if (Test-Path -LiteralPath $AuditStderrPath) {
        $AuditStderr = @(Get-Content -LiteralPath $AuditStderrPath -Encoding UTF8)
    }

    $AuditOutput = @(
        $AuditStdout
        if ($AuditStderr.Count -gt 0) {
            ""
            "--- STDERR DOCKER ---"
            $AuditStderr
        }
    )

    $AuditOutput | Set-Content -LiteralPath $TranscriptPath -Encoding UTF8
    $AuditOutput | ForEach-Object { Write-Host $_ }

    if ($AuditExit -ne 0) {
        throw "La auditoría sobre la BD restaurada falló con exit code $AuditExit. Revise $AuditStdoutPath y $AuditStderrPath."
    }

    $RestoredAuditJson = Join-Path $RestoreResultsRoot "auditoria_global_migracion_mq.json"
    if (-not (Test-Path -LiteralPath $RestoredAuditJson -PathType Leaf)) {
        throw "La auditoría restaurada no generó JSON."
    }

    $RestoredAudit = Get-Content -LiteralPath $RestoredAuditJson -Raw -Encoding UTF8 |
        ConvertFrom-Json

    if ([string]$RestoredAudit.summary.result -ne "PASS") {
        throw "La auditoría restaurada no quedó en PASS."
    }
    if ([int]$RestoredAudit.summary.FAIL -ne 0) {
        throw "La auditoría restaurada reportó FAIL=$($RestoredAudit.summary.FAIL)."
    }
    if ([int]$RestoredAudit.summary.PASS -ne 119) {
        throw "La auditoría restaurada cambió PASS: esperado=119 actual=$($RestoredAudit.summary.PASS)."
    }
    if ([int]$RestoredAudit.summary.INFO -ne 3) {
        throw "La auditoría restaurada cambió INFO: esperado=3 actual=$($RestoredAudit.summary.INFO)."
    }

    $Result = [ordered]@{
        status = "RESTORECHECK_PASS"
        checked_at = (Get-Date).ToString("o")
        package_root = $PackageRoot
        manifest_sha256 = $ExpectedManifestSha
        dump_sha256 = [string]$Manifest.dump.sha256
        source_database = [string]$Manifest.source_database
        restored_database = $RestoreDb
        schema_version = "018"
        project_key = "MEX-QRO"
        audit = [ordered]@{
            PASS = [int]$RestoredAudit.summary.PASS
            FAIL = [int]$RestoredAudit.summary.FAIL
            INFO = [int]$RestoredAudit.summary.INFO
            result = [string]$RestoredAudit.summary.result
        }
        temporary_database_removed = $false
    }

    Write-Host ""
    Write-Host "RESTORE + AUDITORÍA: PASS"
}
finally {
    # Limpiar dump temporal.
    docker exec $DbContainer rm -f $ContainerDump 2>$null | Out-Null

    # Eliminar EXCLUSIVAMENTE la BD temporal creada por este script.
    if ($CreatedDb) {
        docker exec $DbContainer dropdb `
            -U $DbUser `
            --if-exists `
            --force `
            $RestoreDb

        $DropExit = $LASTEXITCODE

        if ($DropExit -ne 0) {
            Write-Warning "No se pudo eliminar automáticamente $RestoreDb."
        }
    }

    if (Test-Path variable:Result) {
        $StillExists = (
            docker exec $DbContainer psql `
                -U $DbUser `
                -d postgres `
                -Atc "SELECT COUNT(*) FROM pg_database WHERE datname='$RestoreDb';"
        ).Trim()

        if ($LASTEXITCODE -eq 0 -and $StillExists -eq "0") {
            $Result.temporary_database_removed = $true
        }

        $Result | ConvertTo-Json -Depth 6 |
            Set-Content -LiteralPath $ResultJsonPath -Encoding UTF8
    }
}

if (-not (Test-Path variable:Result)) {
    throw "Restore-check no llegó a estado PASS."
}
if (-not $Result.temporary_database_removed) {
    throw "Restore-check pasó, pero la BD temporal no pudo confirmarse eliminada."
}

$ResultSha = Get-Sha256 $ResultJsonPath

Write-Host ""
Write-Host "=== RESTORE-CHECK COMPLETADO ==="
Write-Host "Estado:             RESTORECHECK_PASS"
Write-Host "BD temporal:        $RestoreDb"
Write-Host "BD temporal borrada: True"
Write-Host "Auditoría:          PASS=119 FAIL=0 INFO=3"
Write-Host "Manifest SHA-256:   $ExpectedManifestSha"
Write-Host "Dump SHA-256:       $($Manifest.dump.sha256)"
Write-Host "Resultado SHA-256:  $ResultSha"
Write-Host "Evidencia:          $RestoreResultsRoot"
Write-Host ""
Write-Host "No se tocó db_carga_excel."
Write-Host "No se tocó db_pruebas_alfredo."
