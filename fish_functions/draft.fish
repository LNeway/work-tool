function draft
    # 参数验证
    if test (count $argv) -ne 1
        echo "错误：需要且只能接受一个参数"
        echo "用法：draft <草稿ID或带前缀的字符串>"
        return 1
    end

    # 解析逻辑
    set -l raw_input $argv[1]
    set -l draft_id

    if string match -q "原始素材草稿id:*" -- $raw_input
        set draft_id (string replace "原始素材草稿id:" "" -- $raw_input)
    else
        set draft_id $raw_input
    end

    # 执行操作
    make draft || return
    sleep 1
    input $draft_id

    echo "已输入草稿ID：$draft_id"
end
