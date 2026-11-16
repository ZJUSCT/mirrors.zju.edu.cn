#!/bin/bash
# gitsync fetch 后、repack/update-server-info 前运行；只替换根树的 config.json，
# 不检出整个索引，也不创建包含全部包路径的临时 Git index。
set -euo pipefail

cd "${TO:?}"
[[ $(git rev-parse --is-bare-repository) == true ]]
ref=$(git symbolic-ref HEAD)
parent=$(git rev-parse "$ref")
old_config=$(git rev-parse "$parent:config.json")
new_config=$(git hash-object -w --stdin <<EOF
{
  "dl": "${CRATES_PROXY:?}",
  "api": "https://crates.io"
}
EOF
)
[[ $old_config != "$new_config" ]] || exit 0

# ls-tree 不递归，mktree 保留所有子树的原始对象 ID 并重新排序根目录。
tree=$(git ls-tree "$parent" |
    awk -v blob="$new_config" 'BEGIN { FS = "\t" }
        $2 == "config.json" { print "100644 blob " blob "\tconfig.json"; next }
        { print }' |
    git mktree)

# 相同上游提交生成相同的镜像提交，避免每次 fetch 后仅时间戳不同。
export GIT_AUTHOR_NAME="${CRATES_GITNAME:?}"
export GIT_AUTHOR_EMAIL="${CRATES_GITMAIL:?}"
export GIT_COMMITTER_NAME="$GIT_AUTHOR_NAME"
export GIT_COMMITTER_EMAIL="$GIT_AUTHOR_EMAIL"
GIT_AUTHOR_DATE=$(git show -s --format=%cI "$parent")
export GIT_AUTHOR_DATE GIT_COMMITTER_DATE="$GIT_AUTHOR_DATE"
commit=$(git commit-tree "$tree" -p "$parent" -m 'Redirect crate downloads to ZJU Mirrors')
git update-ref "$ref" "$commit" "$parent"
