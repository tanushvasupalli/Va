Set WshShell = CreateObject("WScript.Shell")
strPath = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName) & "\.."
WshShell.CurrentDirectory = strPath
WshShell.Run """" & strPath & "\venv\Scripts\pythonw.exe"" scripts\hotkey_listener.py", 0, False
WshShell.Run """" & strPath & "\venv\Scripts\pythonw.exe"" core\telegram_bot.py", 0, False
Set WshShell = Nothing
