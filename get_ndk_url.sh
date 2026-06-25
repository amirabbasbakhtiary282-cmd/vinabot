#!/bin/bash
curl -sL 'https://developer.android.com/ndk/downloads' | grep -o 'https://[^"'\'']*ndk[^"'\'']*linux[^"'\'']*\.zip' | head -10