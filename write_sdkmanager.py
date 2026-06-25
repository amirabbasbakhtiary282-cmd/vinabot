content = """#!/bin/bash
echo "sdkmanager wrapper: $@" >&2

for arg in "$@"; do
    case "$arg" in
        --list)
            cat << 'EOF2'
Installed packages:
  Path                 | Version | Description
  -------              | ------- | -----------
  platform-tools       | 28.0.2  | Android SDK Platform-Tools
  platforms;android-30 | 3       | Android SDK Platform 30
  build-tools;30.0.3   | 30.0.3  | Android SDK Build-Tools 30.0.3

Available packages:
  Path                 | Version | Description
  -------              | ------- | -----------
  build-tools;30.0.3   | 30.0.3  | Android SDK Build-Tools 30.0.3
  platforms;android-30 | 3       | Android SDK Platform 30
  platform-tools       | 28.0.2  | Android SDK Platform-Tools
EOF2
            exit 0
            ;;
        --update)
            exit 0
            ;;
        --licenses)
            echo "y" | while read line; do echo "y"; done
            exit 0
            ;;
    esac
done

case "$1" in
    *platforms*|*build-tools*|*platform-tools*) 
        exit 0 
        ;;
    *) 
        exit 0 
        ;;
esac
"""

with open('/home/amirabbas/.buildozer/android/platform/android-sdk/tools/bin/sdkmanager', 'w') as f:
    f.write(content)
print("Done writing sdkmanager")