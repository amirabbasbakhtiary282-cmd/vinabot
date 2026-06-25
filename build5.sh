#!/bin/bash
export PATH=/home/amirabbas/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export VIRTUAL_ENV=/home/amirabbas/venv
cd /home/amirabbas/Vina
buildozer android debug 2>&1
