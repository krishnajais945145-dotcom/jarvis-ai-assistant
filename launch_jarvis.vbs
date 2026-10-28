Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
currDir = fso.GetParentFolderName(WScript.ScriptFullName)
batPath = currDir & "\run_jarvis.bat"
WshShell.Run """" & batPath & """", 0, False
