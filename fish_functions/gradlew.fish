function gradlew
    # 前置操作（例如打印信息）
    # xxxxx
    # 执行原始命令
    ./gradlew $argv
    set exit_code $status
    if test $exit_code -eq 0
        toast success
    else
        toast fail
    end
    return $exit_code
end
