import os
import re
import subprocess
ipynbs = [e for e in os.listdir('./') if re.match('.*\.ipynb$', e)]
for e in ipynbs:
        subprocess.run(["quarto", "convert", e])
