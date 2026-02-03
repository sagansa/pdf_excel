import sys

try:
    with open('index.html', 'r') as f:
        content = f.read()
    
    # Check for script tag balance
    open_scripts = content.count('<script')
    close_scripts = content.count('</script>')
    
    if open_scripts != close_scripts:
        print(f"MISMATCH: <script> {open_scripts} vs </script> {close_scripts}")
    else:
        print("Script tags balanced.")
        
    # Check for unclosed divs (basic count)
    open_divs = content.count('<div')
    close_divs = content.count('</div>')
    
    print(f"Divs: {open_divs} open, {close_divs} close")
    
except Exception as e:
    print(str(e))
