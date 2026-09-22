# Receives Cisco config backups pushed via `copy running-config http://...`
# and writes them into the same folder this script itself lives in,
# cleaning up the numeric suffix IOS appends to the URL path (observed on
# a real 3850: a push to ".../x.txt" arrives with a URL path ending
# "x.txt-321" - the trailing "-NNN" gets moved to just before the
# extension: "x-321.txt").
#
# On Windows, run this from an elevated (Administrator) PowerShell.
# HttpListener refuses to bind a wildcard prefix like "http://+:8080/"
# from a normal session ("Access is denied"), regardless of the port
# number - that's a Windows http.sys URL-ACL restriction, unrelated to
# port 8080 itself being non-privileged. On Linux/macOS this restriction
# doesn't apply - no elevation is needed to bind ports above 1024.

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
    Write-Host "  sudo ss -ltnp | grep 8080         (Linux)"
    Write-Host "  lsof -i :8080         (macOS)"
    exit 1
}
Write-Host "Listening on port 8080, saving to $DestDir ..."

# Ctrl+C normally can't interrupt a blocked GetContext() call, since it's
# a synchronous native wait rather than something that polls for
# cancellation. Trapping CancelKeyPress explicitly and calling
# listener.Stop() forces that blocked call to throw, which the catch
# block below turns into a clean exit instead of an unkillable script.
$cancelled = $false
[Console]::TreatControlCAsInput = $false
Register-ObjectEvent -InputObject ([Console]) -EventName CancelKeyPress -Action {
    $Event.MessageData.Stop()
    $script:cancelled = $true
    $EventArgs.Cancel = $true
} -MessageData $listener | Out-Null

while ($listener.IsListening) {
    # GetContext() blocks in a native wait that Stop() doesn't reliably
    # interrupt on Linux (it does on Windows, via http.sys) - confirmed
    # the hard way testing both platforms. Using the async version and
    # polling with a short timeout means the loop returns control
    # regularly instead of blocking indefinitely, so $cancelled actually
    # gets checked instead of the script hanging until the next request.
    $contextTask = $listener.GetContextAsync()
    while (-not $contextTask.AsyncWaitHandle.WaitOne(200)) {
        if ($cancelled) { break }
    }
    if ($cancelled) { break }

    try {
        $context = $contextTask.GetAwaiter().GetResult()
    } catch [System.Net.HttpListenerException] {
        if ($cancelled) { break }
        throw
    } catch [System.ObjectDisposedException] {
        if ($cancelled) { break }
        throw
    }

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

Write-Host "Listener stopped."
