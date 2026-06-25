#!/bin/bash
cd /home/amirabbas/Vina
source /home/amirabbas/venv/bin/activate
/home/amirabbas/venv/bin/buildozer -v android debug
echo "Exit code: $?"
