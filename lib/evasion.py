import platform

if platform.system() == 'Windows':
    from lib.evasion_windows import *
else:
    from lib.evasion_linux import *
