import os
import subprocess
import ctypes

def test_launches():
    print("=== Testing Windows App Launches ===")
    
    # 1. Shell.Application COM
    try:
        ps_cmd = '$s = New-Object -ComObject Shell.Application; $s.ShellExecute("notepad.exe", "", "", "open", 1)'
        subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], check=True)
        print("[1] Shell.Application COM: Succeeded")
    except Exception as e:
        print("[1] Shell.Application COM Failed:", e)

    # 2. Explorer shell:AppsFolder
    try:
        app_id = r"shell:AppsFolder\Microsoft.WindowsCalculator_8wekyb3d8bbwe!App"
        subprocess.Popen(f'explorer.exe "{app_id}"', shell=True)
        print("[2] Explorer AppsFolder: Succeeded")
    except Exception as e:
        print("[2] Explorer AppsFolder Failed:", e)

    # 3. Protocol URI
    try:
        subprocess.Popen('explorer.exe "calculator:"', shell=True)
        print("[3] Protocol URI: Succeeded")
    except Exception as e:
        print("[3] Protocol URI Failed:", e)

if __name__ == "__main__":
    test_launches()
