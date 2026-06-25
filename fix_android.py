content = """#!/bin/bash
echo "android wrapper: $@" >&2
case "$1" in
    list)
        cat << "EOF2"
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
    update)
        exit 0
        ;;
    *)
        echo "android wrapper: $@" >&2
        exit 0
        ;;
esac
"""

with open('/home/amirabbas/.buildozer/android/platform/android-sdk/tools/bin/android', 'w') as f:
    f.write(content)
print("Done")