#!/bin/bash
curl -sL 'https://developer.android.com/ndk/downloads' | grep -o 'href="[^"]*ndk[^"]*linux[^"]*\.zip' | head -10