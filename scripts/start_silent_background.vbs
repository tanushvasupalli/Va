Set WshShell = CreateObject("WScript.Shell")
strPath = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName) & "\.."
WshShell.CurrentDirectory = strPath
WshShell.Run """" & strPath & "\venv\Scripts\pythonw.exe"" -m dashboard.app", 0, False
Set WshShell = Nothing
