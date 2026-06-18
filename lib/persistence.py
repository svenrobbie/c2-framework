import platform

if platform.system() == 'Windows':
    from lib.persistence_windows import *
else:
    from lib.persistence_linux import *
