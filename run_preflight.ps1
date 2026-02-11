[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING = 'utf-8'
Set-Location 'C:\Users\spencer\Documents\Projects\New_Jarvis'
& '.\.venv\Scripts\python.exe' preflight_test.py 2>&1 | Select-Object -Last 12
