param(
    [string]$SourcePath = "",
    [switch]$NoLoad
)

$argsList = @()
if ($SourcePath -ne "") {
    $argsList += "--source-path"
    $argsList += $SourcePath
}
if ($NoLoad) {
    $argsList += "--no-load"
}

py -m taxi_pipeline.cli @argsList
