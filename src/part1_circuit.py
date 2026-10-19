"""任务1：补全固定时隙电路交换发送。只改本文件内TODO。"""
def serve_circuit(queues, tick, cfg):
    """queues为每用户一个deque[Pending]，原地更新。
    本tick只能服务user=tick % cfg.users，其他用户不能借用其时隙。
    该用户可在slot_bits预算内连续发送多个记录，也可部分发送一个记录。
    返回(本tick实际线速发送比特数, 本tick完整发送的Pending列表)。
    空队列返回(0,[])；记录完全发完才pop并记入完成列表。
    提示：先确定用户，再在该用户队列上按FIFO扣减remaining_wire_bits。
    """
    # 固定时隙只属于tick%users这一名用户，其他用户即使队列非空也拿不到本tick预算。
    user = tick % cfg.users
    queue = queues[user]
    budget = cfg.slot_bits
    wire_bits = 0
    completed = []
    # 预算没用完就继续送该用户的下一条；队列空则本tick提前结束，空闲时隙不转借。
    while budget > 0 and queue:
        record = queue[0]
        send = min(budget, record.remaining_wire_bits)
        record.remaining_wire_bits -= send
        budget -= send
        wire_bits += send
        if record.remaining_wire_bits:
            # 预算耗尽且记录未发完：保留在队首跨tick续传，不能报告为完成。
            break
        queue.popleft()
        completed.append(record)
    return wire_bits, completed
