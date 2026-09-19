#!/bin/sh
# Новая версия для ссылок на файлы и version.json — запускать перед каждой публикацией.
cd "$(dirname "$0")/.." || exit 1
V=$(git rev-parse --short HEAD)-$(date +%s)
sed -i -E "s#\?v=[a-z0-9-]+\"#?v=$V\"#g; s#\}\)\('[a-z0-9-]+'\)</script>#})('$V')</script>#" *.html
printf '{"v":"%s"}\n' "$V" > version.json
echo "$V"
