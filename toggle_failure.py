import os
import sys

from service_simulator import NORMAL_ERRORS, flag_path


service_name = sys.argv[1] if len(sys.argv) == 2 else None

if service_name not in NORMAL_ERRORS:
    print("Use: python toggle_failure.py <service-name>")
    print("Services:", ", ".join(NORMAL_ERRORS))
    sys.exit(1)

flag = flag_path(service_name)

if os.path.exists(flag):
    os.remove(flag)
    print(f"{service_name} ab THEEK hai (normal mode)")
else:
    with open(flag, "w", encoding="utf-8"):
        pass
    print(f"{service_name} ab KHARAB hai (failure mode)")