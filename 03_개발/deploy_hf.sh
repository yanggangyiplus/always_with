#!/bin/sh
# Hugging Face Space에 이 폴더를 올린다. 사용: ./deploy_hf.sh 계정/space이름
# git이 비밀번호를 물으면 write 권한 토큰을 넣는다.
set -e
[ -n "$1" ] || { echo "사용: $0 계정/space이름"; exit 1; }
SRC=$(cd "$(dirname "$0")" && pwd)
TMP=$(mktemp -d)
git clone "https://huggingface.co/spaces/$1" "$TMP"
rsync -a --delete --exclude .git --exclude node_modules --exclude .venv --exclude __pycache__ \
  --exclude tests --exclude '*.db' --exclude .env --exclude clips \
  "$SRC/Dockerfile" "$SRC/.dockerignore" "$SRC/backend" "$SRC/frontend" "$TMP/"
printf -- '---\ntitle: Always with\nsdk: docker\napp_port: 7860\n---\n' > "$TMP/README.md"
cd "$TMP"
git add -A
git commit -m "Deploy Always with" || echo "바뀐 내용이 없어요"
git push
echo "빌드 상태: https://huggingface.co/spaces/$1"
