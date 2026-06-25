#!/usr/bin/env python3
import sys
from buildozer.scripts.client import main
if __name__ == '__main__':
    sys.argv[0] = sys.argv[0].removesuffix('.exe')
    main()
