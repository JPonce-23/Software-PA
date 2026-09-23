param(
    [string]$ProjectRoot = "C:\Proyectos\Software-PA-backend-logica",
    [string]$DbContainer = "software-pa-db-1",
    [string]$DbName = "db_carga_excel",
    [string]$DbUser = "pa_app",
    [string]$ProjectKey = "MEX-QRO",
    [string]$SchemaVersion = "018"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$ExpectedExcelSha = "bac01c25e9ff963f524fa8a48d69e74d92a0d36578731b1eca91f0e5a3573c3f"
$ExpectedResolutionSha = "912d05e031a3edd08652fb7adb4a716ec1588137822cf2b998ca51f26e1361ee"

if ($DbName -ne "db_carga_excel") {
    throw "Protección: este script sólo acepta DbName=db_carga_excel."
}
if ($SchemaVersion -ne "018") {
    throw "Protección: este paquete está congelado para schema 018."
}
if ($ProjectKey -ne "MEX-QRO") {
    throw "Protección: este paquete está congelado para MEX-QRO."
}

$ImportRoot = Join-Path $ProjectRoot "data\importacion"
$ReportsRoot = Join-Path $ImportRoot "reportes"
$ExcelPath = Join-Path $ImportRoot "mq_colectivos.xlsx"
$ResolutionPath = Join-Path $ReportsRoot "2j_post_reparaciones\resolucion_seguimiento_post_reparaciones.csv"
$AuditJson = Join-Path $ReportsRoot "cierre_global\auditoria_global_migracion_mq.json"
$AuditCsv = Join-Path $ReportsRoot "cierre_global\auditoria_global_migracion_mq.csv"
$ScriptsRoot = Join-Path $ProjectRoot "backend\scripts"

foreach ($required in @($ExcelPath, $ResolutionPath, $AuditJson, $AuditCsv)) {
    if (-not (Test-Path -LiteralPath $required -PathType Leaf)) {
        throw "Falta archivo obligatorio: $required"
    }
}

function Normalize-Sha256([object]$Value, [string]$Label) {
    if ($null -eq $Value) {
        throw "$Label es NULL."
    }

    $Normalized = ([string]$Value).Trim().ToLowerInvariant()

    if ($Normalized -notmatch '^[0-9a-f]{64}$') {
        throw "$Label no es un SHA-256 hexadecimal válido de 64 caracteres: '$Normalized' (longitud=$($Normalized.Length))."
    }

    return $Normalized
}

function Get-Sha256([string]$Path) {
    $RawHash = (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash
    return Normalize-Sha256 $RawHash "SHA-256 calculado de $Path"
}

function Assert-Sha256(
    [string]$Actual,
    [string]$Expected,
    [string]$Label
) {
    $A = Normalize-Sha256 $Actual "$Label actual"
    $E = Normalize-Sha256 $Expected "$Label esperado"

    if (-not [System.String]::Equals(
        $A,
        $E,
        [System.StringComparison]::Ordinal
    )) {
        throw "$Label inesperado. actual='$A' (len=$($A.Length)); esperado='$E' (len=$($E.Length))."
    }
}

# Validar artefactos fuente antes de crear nada.
$ExcelSha = Get-Sha256 $ExcelPath
Assert-Sha256 $ExcelSha $ExpectedExcelSha "SHA-256 del Excel"

$ResolutionSha = Get-Sha256 $ResolutionPath
Assert-Sha256 $ResolutionSha $ExpectedResolutionSha "SHA-256 de resolución 2J"

$Audit = Get-Content -LiteralPath $AuditJson -Raw -Encoding UTF8 | ConvertFrom-Json

if ([string]$Audit.database -ne $DbName) {
    throw "El reporte global fue generado contra otra BD: $($Audit.database)"
}
if ([string]$Audit.schema -ne $SchemaVersion) {
    throw "El reporte global fue generado contra otro schema: $($Audit.schema)"
}
if ([string]$Audit.project -ne $ProjectKey) {
    throw "El reporte global corresponde a otro proyecto: $($Audit.project)"
}
Assert-Sha256 ([string]$Audit.excel_sha256) $ExpectedExcelSha "SHA-256 Excel en auditoría"
Assert-Sha256 ([string]$Audit.resolution_2j_sha256) $ExpectedResolutionSha "SHA-256 resolución 2J en auditoría"
if ([string]$Audit.summary.result -ne "PASS") {
    throw "La auditoría global no está en PASS."
}
if ([int]$Audit.summary.FAIL -ne 0) {
    throw "La auditoría global contiene FAIL=$($Audit.summary.FAIL)."
}

# Confirmar que el contenedor y la BD son exactamente los esperados.
$CurrentDb = (
    docker exec $DbContainer psql -U $DbUser -d $DbName -Atc "SELECT current_database();"
).Trim()
if ($LASTEXITCODE -ne 0 -or $CurrentDb -ne $DbName) {
    throw "No se pudo confirmar la BD dentro de $DbContainer."
}

$CurrentSchema = (
    docker exec $DbContainer psql -U $DbUser -d $DbName -Atc "SELECT max(version) FROM schema_migrations;"
).Trim()
if ($LASTEXITCODE -ne 0 -or $CurrentSchema -ne $SchemaVersion) {
    throw "Schema inesperado en PostgreSQL: '$CurrentSchema'."
}

$ProjectCount = (
    docker exec $DbContainer psql -U $DbUser -d $DbName -Atc "SELECT COUNT(*) FROM proyecto WHERE activo IS TRUE AND clave_proyecto='$ProjectKey';"
).Trim()
if ($LASTEXITCODE -ne 0 -or $ProjectCount -ne "1") {
    throw "No existe exactamente un proyecto activo $ProjectKey."
}

# Contrato runtime: debe existir el rol estable y conservar los privilegios
# necesarios. El LOGIN real del backend hereda este rol.
$RuntimeRoleExists = (
    docker exec $DbContainer psql -U $DbUser -d $DbName -Atc "SELECT COUNT(*) FROM pg_roles WHERE rolname='software_pa_app';"
).Trim()
if ($LASTEXITCODE -ne 0 -or $RuntimeRoleExists -ne "1") {
    throw "Falta el rol runtime estable software_pa_app."
}

$RuntimeSchemaUsage = (
    docker exec $DbContainer psql -U $DbUser -d $DbName -Atc "SELECT has_schema_privilege('software_pa_app','public','USAGE');"
).Trim()
if ($LASTEXITCODE -ne 0 -or $RuntimeSchemaUsage -ne "t") {
    throw "software_pa_app no tiene USAGE sobre schema public."
}

$RuntimeSchemaMigrations = (
    docker exec $DbContainer psql -U $DbUser -d $DbName -Atc "SELECT has_table_privilege('software_pa_app','public.schema_migrations','SELECT') AND NOT has_table_privilege('software_pa_app','public.schema_migrations','INSERT') AND NOT has_table_privilege('software_pa_app','public.schema_migrations','UPDATE') AND NOT has_table_privilege('software_pa_app','public.schema_migrations','DELETE') AND NOT has_table_privilege('software_pa_app','public.schema_migrations','TRUNCATE');"
).Trim()
if ($LASTEXITCODE -ne 0 -or $RuntimeSchemaMigrations -ne "t") {
    throw "Contrato de privilegios de software_pa_app sobre schema_migrations no coincide."
}

$RuntimeProyecto = (
    docker exec $DbContainer psql -U $DbUser -d $DbName -Atc "SELECT has_table_privilege('software_pa_app','public.proyecto','SELECT') AND has_table_privilege('software_pa_app','public.proyecto','INSERT') AND has_table_privilege('software_pa_app','public.proyecto','UPDATE') AND NOT has_table_privilege('software_pa_app','public.proyecto','DELETE') AND NOT has_table_privilege('software_pa_app','public.proyecto','TRUNCATE');"
).Trim()
if ($LASTEXITCODE -ne 0 -or $RuntimeProyecto -ne "t") {
    throw "Contrato de privilegios de software_pa_app sobre proyecto no coincide."
}

$RuntimeBitacora = (
    docker exec $DbContainer psql -U $DbUser -d $DbName -Atc "SELECT has_table_privilege('software_pa_app','public.bitacora','SELECT') AND NOT has_table_privilege('software_pa_app','public.bitacora','INSERT') AND NOT has_table_privilege('software_pa_app','public.bitacora','UPDATE') AND NOT has_table_privilege('software_pa_app','public.bitacora','DELETE') AND NOT has_table_privilege('software_pa_app','public.bitacora','TRUNCATE');"
).Trim()
if ($LASTEXITCODE -ne 0 -or $RuntimeBitacora -ne "t") {
    throw "Contrato append-only de software_pa_app sobre bitacora no coincide."
}

# Carpeta inmutable por timestamp. Nunca sobrescribe un paquete previo.
$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$PackageRoot = Join-Path $ImportRoot "promocion\$ProjectKey\schema_${SchemaVersion}_$Stamp"
if (Test-Path -LiteralPath $PackageRoot) {
    throw "La carpeta de paquete ya existe: $PackageRoot"
}

$EvidenceDir = Join-Path $PackageRoot "evidencia"
$ScriptsDir = Join-Path $PackageRoot "scripts"
$SourceDir = Join-Path $PackageRoot "fuente"
$DbDir = Join-Path $PackageRoot "database"

New-Item -ItemType Directory -Path $EvidenceDir -Force | Out-Null
New-Item -ItemType Directory -Path $ScriptsDir -Force | Out-Null
New-Item -ItemType Directory -Path $SourceDir -Force | Out-Null
New-Item -ItemType Directory -Path $DbDir -Force | Out-Null

# Copiar fuente y evidencia ya auditada.
Copy-Item -LiteralPath $ExcelPath -Destination (Join-Path $SourceDir "mq_colectivos.xlsx")
Copy-Item -LiteralPath $ResolutionPath -Destination (Join-Path $EvidenceDir "resolucion_seguimiento_post_reparaciones.csv")
Copy-Item -LiteralPath $AuditJson -Destination (Join-Path $EvidenceDir "auditoria_global_migracion_mq.json")
Copy-Item -LiteralPath $AuditCsv -Destination (Join-Path $EvidenceDir "auditoria_global_migracion_mq.csv")

# Scripts focales que llevaron del estado post-2B a cierre global.
$ScriptNames = @(
    "preflight_reparacion_asambleas_permanentes.py",
    "importar_reparacion_asambleas_permanentes.py",
    "preflight_reparacion_convenios_asamblea_2d_r.py",
    "importar_reparacion_convenios_asamblea_2d_r.py",
    "preflight_reparacion_ran_2f_r.py",
    "importar_reparacion_ran_2f_r.py",
    "reconciliar_soporte_documental_ck_cl_post_2f_r.py",
    "preflight_reparacion_soporte_documental_2i_b_r.py",
    "importar_reparacion_soporte_documental_2i_b_r.py",
    "resolver_seguimiento_post_reparaciones_2j.py",
    "preflight_seguimiento_2j.py",
    "importar_seguimiento_2j.py",
    "auditoria_global_migracion_mq.py"
)

foreach ($name in $ScriptNames) {
    $source = Join-Path $ScriptsRoot $name
    if (-not (Test-Path -LiteralPath $source -PathType Leaf)) {
        throw "Falta script de evidencia: $source"
    }
    Copy-Item -LiteralPath $source -Destination (Join-Path $ScriptsDir $name)
}

# Capturar estado Git. No exige árbol limpio: lo registra de manera explícita.
$GitHead = (& git -C $ProjectRoot rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($GitHead)) {
    throw "No se pudo obtener git HEAD de $ProjectRoot."
}
$GitStatusLines = @(& git -C $ProjectRoot status --short)
$GitStatusPath = Join-Path $EvidenceDir "git_status.txt"
@(
    "git_head=$GitHead"
    "capturado_en=$((Get-Date).ToString('o'))"
    ""
    "git status --short:"
    $GitStatusLines
) | Set-Content -LiteralPath $GitStatusPath -Encoding UTF8

# Dump custom-format. pg_dump no modifica la BD.
$DumpName = "db_carga_excel_schema018.dump"
$ContainerDump = "/tmp/$DumpName"
$LocalDump = Join-Path $DbDir $DumpName

docker exec $DbContainer rm -f $ContainerDump
if ($LASTEXITCODE -ne 0) {
    throw "No se pudo limpiar el dump temporal dentro del contenedor."
}

# Conservamos ACLs: el runtime del backend usa un LOGIN separado que
# hereda privilegios del rol NOLOGIN software_pa_app. Un dump sin ACL no
# reproduce el contrato operativo del backend al restaurarse.
docker exec $DbContainer pg_dump `
    -U $DbUser `
    -d $DbName `
    -Fc `
    --no-owner `
    -f $ContainerDump

if ($LASTEXITCODE -ne 0) {
    throw "pg_dump falló."
}

docker cp "${DbContainer}:${ContainerDump}" $LocalDump
if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $LocalDump -PathType Leaf)) {
    throw "No se pudo copiar el dump al paquete."
}

# Verificación mínima de legibilidad del dump dentro del mismo contenedor,
# antes de eliminar el archivo temporal. No usa redirección binaria de PowerShell.
$DumpListPath = Join-Path $EvidenceDir "pg_restore_list.txt"
$DumpList = @(docker exec $DbContainer pg_restore -l $ContainerDump)
if ($LASTEXITCODE -ne 0) {
    throw "pg_restore -l no pudo leer el dump generado."
}
$DumpList | Set-Content -LiteralPath $DumpListPath -Encoding UTF8

docker exec $DbContainer rm -f $ContainerDump | Out-Null

# Hash de todos los archivos del paquete excepto el manifest final.
$Files = Get-ChildItem -LiteralPath $PackageRoot -Recurse -File |
    Sort-Object FullName

$FileEntries = foreach ($file in $Files) {
    [ordered]@{
        relative_path = $file.FullName.Substring($PackageRoot.Length).TrimStart('\')
        size_bytes = $file.Length
        sha256 = Get-Sha256 $file.FullName
    }
}

$DumpSha = Get-Sha256 $LocalDump

$Manifest = [ordered]@{
    manifest_version = 1
    created_at = (Get-Date).ToString("o")
    status = "CANDIDATO_CONGELADO_PENDIENTE_RESTORECHECK"
    source_database = $DbName
    schema_version = $SchemaVersion
    project_key = $ProjectKey
    db_container = $DbContainer
    db_user = $DbUser
    excel_sha256 = $ExpectedExcelSha
    resolution_2j_sha256 = $ExpectedResolutionSha
    audit = [ordered]@{
        result = [string]$Audit.summary.result
        pass = [int]$Audit.summary.PASS
        fail = [int]$Audit.summary.FAIL
        info = [int]$Audit.summary.INFO
    }
    runtime_acl = [ordered]@{
        role = "software_pa_app"
        schema_public_usage = $true
        schema_migrations_select_only = $true
        proyecto_select_insert_update_no_delete_truncate = $true
        bitacora_select_only = $true
    }
    dump = [ordered]@{
        file = "database\$DumpName"
        format = "PostgreSQL custom"
        no_owner = $true
        acl_included = $true
        runtime_role = "software_pa_app"
        sha256 = $DumpSha
    }
    git = [ordered]@{
        head = $GitHead
        status_clean = ($GitStatusLines.Count -eq 0)
        status_file = "evidencia\git_status.txt"
    }
    files = @($FileEntries)
}

$ManifestPath = Join-Path $PackageRoot "manifest.json"
$Manifest | ConvertTo-Json -Depth 8 |
    Set-Content -LiteralPath $ManifestPath -Encoding UTF8

$ManifestSha = Get-Sha256 $ManifestPath
$ManifestShaPath = Join-Path $PackageRoot "manifest.sha256.txt"
"$ManifestSha  manifest.json" |
    Set-Content -LiteralPath $ManifestShaPath -Encoding ASCII

Write-Host ""
Write-Host "=== PAQUETE DE PROMOCIÓN CONGELADO ==="
Write-Host "Paquete:           $PackageRoot"
Write-Host "BD fuente:         $DbName"
Write-Host "Schema:            $SchemaVersion"
Write-Host "Proyecto:          $ProjectKey"
Write-Host "Auditoría:         PASS=$($Audit.summary.PASS) FAIL=$($Audit.summary.FAIL) INFO=$($Audit.summary.INFO)"
Write-Host "Excel SHA-256:     $ExpectedExcelSha"
Write-Host "Resolución SHA:    $ExpectedResolutionSha"
Write-Host "Dump SHA-256:      $DumpSha"
Write-Host "Manifest SHA-256:  $ManifestSha"
Write-Host "Git HEAD:          $GitHead"
Write-Host "Git limpio:        $($GitStatusLines.Count -eq 0)"
Write-Host ""
Write-Host "Estado:"
Write-Host "  CANDIDATO_CONGELADO_PENDIENTE_RESTORECHECK"
Write-Host ""
Write-Host "No se modificó PostgreSQL."
Write-Host "No se tocó db_pruebas_alfredo."
Write-Host "El siguiente paso es restaurar ESTE dump en una BD temporal aislada y repetir la auditoría."
