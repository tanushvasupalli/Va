Set WshShell = CreateObject("WScript.Shell")
strCurrentDir = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = strCurrentDir

' Launch hotkey listener & telegram_bot.py silently using pythonw.exe (0 = hide window, False = don't wait)
WshShell.Run """" & strCurrentDir & "\venv\Scripts\pythonw.exe"" scripts\hotkey_listener.py", 0, False
WshShell.Run """" & strCurrentDir & "\venv\Scripts\pythonw.exe"" core\telegram_bot.py", 0, False
