function gpsup
    # 检查是否在Git仓库
    if not git rev-parse --is-inside-work-tree >/dev/null 2>&1
        echo "❌ 错误：当前目录不是Git仓库"
        return 1
    end

    # 获取当前分支名
    set -l branch (command git branch --show-current 2>/dev/null)
    if test -z "$branch"
        echo "❌ 错误：当前不在任何分支上"
        return 1
    end

    # 执行推送命令
    echo "🚀 正在推送分支 [$branch] 到远程..."
    if git push -u origin "$branch"
        echo "✅ 成功推送分支 [$branch] 到远程"
        # 显示远程URL
        set -l remote_url (git remote get-url origin)
        echo "🌐 远程仓库: $remote_url"
    else
        echo "❌ 推送失败，请检查网络连接或权限设置"
        return 1
    end
end
