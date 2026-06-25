#!/bin/bash
source /home/amirabbas/venv/bin/activate
cd /home/amirabbas/Vina
rm -rf .buildozer
/home/amirabbas/venv/bin/buildozer -v android debug 2>&1
