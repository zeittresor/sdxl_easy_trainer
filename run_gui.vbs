Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
shell.CurrentDirectory = scriptDir
pyw = scriptDir & "\.venv\Scripts\pythonw.exe"
py = scriptDir & "\.venv\Scripts\python.exe"
cmd = ""
If fso.FileExists(pyw) Then
    cmd = Chr(34) & pyw & Chr(34) & " " & Chr(34) & scriptDir & "\launch.py" & Chr(34)
ElseIf fso.FileExists(py) Then
    cmd = Chr(34) & py & Chr(34) & " " & Chr(34) & scriptDir & "\launch.py" & Chr(34)
Else
    cmd = Chr(34) & scriptDir & "\run_windows.bat" & Chr(34)
End If
shell.Run cmd, 0, False
