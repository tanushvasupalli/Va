Set WshShell = CreateObject("WScript.Shell")
strCurrentDir = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = strCurrentDir

' Launch dashboard.app silently using pythonw.exe (0 = hide window, False = don't wait)
strCommand = """" & strCurrentDir & "\venv\Scripts\pythonw.exe"" -m dashboard.app"
WshShell.Run strCommand, 0, False

