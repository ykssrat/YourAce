param(
    [Parameter(Mandatory=$true)]
    [string]$SourceImage
)

if (-not (Test-Path $SourceImage)) {
    Write-Error "Icon file not found: $SourceImage"
    exit 1
}

Add-Type -AssemblyName System.Drawing

$resDir = "D:\QMT\YourAce\scripts\mobile\react_native_app\android\app\src\main\res"

$sizes = @{
    "mipmap-mdpi"    = 48
    "mipmap-hdpi"    = 72
    "mipmap-xhdpi"   = 96
    "mipmap-xxhdpi"  = 144
    "mipmap-xxxhdpi" = 192
}

$src = [System.Drawing.Image]::FromFile((Resolve-Path $SourceImage).Path)

foreach ($density in $sizes.Keys) {
    $px = $sizes[$density]
    $outDir = Join-Path $resDir $density
    if (-not (Test-Path $outDir)) { New-Item -ItemType Directory -Path $outDir | Out-Null }

    foreach ($name in @("ic_launcher.png", "ic_launcher_round.png")) {
        $outPath = Join-Path $outDir $name
        $bmp = New-Object System.Drawing.Bitmap($px, $px)
        $g = [System.Drawing.Graphics]::FromImage($bmp)
        $g.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
        $g.DrawImage($src, 0, 0, $px, $px)
        $g.Dispose()

        if ($name -like "*round*") {
            $rounded = New-Object System.Drawing.Bitmap($px, $px)
            $gr = [System.Drawing.Graphics]::FromImage($rounded)
            $gr.Clear([System.Drawing.Color]::Transparent)
            $path = New-Object System.Drawing.Drawing2D.GraphicsPath
            $path.AddEllipse(0, 0, $px, $px)
            $gr.SetClip($path)
            $gr.DrawImage($bmp, 0, 0)
            $gr.Dispose()
            $bmp.Dispose()
            $bmp = $rounded
        }

        $bmp.Save($outPath, [System.Drawing.Imaging.ImageFormat]::Png)
        $bmp.Dispose()
        Write-Host "OK $density/$name ($px x $px)"
    }
}

$src.Dispose()
Write-Host "Done."
