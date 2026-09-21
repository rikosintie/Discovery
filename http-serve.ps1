# Receives Cisco config backups pushed via `copy running-config http://...`
# and writes them into the same folder this script itself lives in,
# cleaning up the numeric suffix IOS appends to the URL path (observed on
# a real 3850: a push to ".../x.txt" arrives with a URL path ending
# "x.txt-321" - the trailing "-NNN" gets moved to just before the
# extension: "x-321.txt").
#
# Run this from an elevated (Administrator) PowerShell. HttpListener
# refuses to bind a wildcard prefix like "http://+:8080/" from a normal
# session ("Access is denied"), regardless of the port number - that's a
# Windows http.sys URL-ACL restriction, unrelated to port 8080 itself
# being non-privileged.

# $PSScriptRoot (this script's own folder), not $PWD (wherever the shell
# happened to be) - keeps backups landing in a predictable place if this
# is ever launched a different way (Task Scheduler, a shortcut) where the
# working directory isn't guaranteed to match where the script sits.
$DestDir = $PSScriptRoot

$listener = New-Object System.Net.HttpListener
$listener.Prefixes.Add("http://+:8080/")
try {
    $listener.Start()
} catch {
    # Without this, a port already in use (or, on Windows, a missing
    # elevated session / URL reservation - see the note above) throws here
    # uncaught, before the "Listening..." line ever prints, and the script
    # just dies back to the prompt with no clue why - confirmed the hard
    # way testing this on a second machine.
    Write-Host "Could not start listening on port 8080: $($_.Exception.Message)"
    Write-Host "If this is a port conflict, something else on this machine is already using it - check with:"
    Write-Host "  netstat -ano | findstr :8080     (Windows)"
    Write-Host "  sudo ss -ltnp | grep 8080         (Linux/macOS)"
    exit 1
}
Write-Host "Listening on port 8080, saving to $DestDir ..."

while ($listener.IsListening) {
    $context = $listener.GetContext()
    $request = $context.Request

    try {
        # GetFileName() strips any directory-separator components from the
        # URL path before it's used to build a filesystem path, so a
        # request can't be crafted to write outside $DestDir.
        $filename = [System.IO.Path]::GetFileName($request.Url.AbsolutePath.TrimStart('/'))
        if ([string]::IsNullOrWhiteSpace($filename)) { $filename = "backup.cfg" }

        # Fix filenames like 'name.txt-317' -> 'name-317.txt'
        $filename = $filename -replace '(\.[a-zA-Z0-9]+)-(\d+)$', '-$2$1'

        $destinationPath = Join-Path $DestDir $filename
        $saveStream = [System.IO.File]::Create($destinationPath)
        $request.InputStream.CopyTo($saveStream)
        $saveStream.Close()

        Write-Host "Saved: $destinationPath"
        $context.Response.StatusCode = 200
    } catch {
        # Without this catch, a failed save (missing folder, no disk space,
        # permissions) prints its own error but the loop carries on to the
        # "Saved" line below regardless - confirmed the hard way - so this
        # is the difference between an accurate log and a false "Saved"
        # message for a file that was never actually written.
        Write-Host "FAILED to save request: $_"
        $context.Response.StatusCode = 500
    } finally {
        $context.Response.Close()
    }
}
