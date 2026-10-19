"""任务2：补全共享FIFO分组交换发送。"""
def serve_packet(queue, tick, cfg):
    """queue为共享deque[Pending]，原地更新。
    remaining_wire_bits已由框架初始化为payload_bits+header_bits，不再重复加包头。
    每tick发送不超过slot_bits；必须发完队首再处理下一项。
    分组允许跨tick续传，但不得与其他分组交错，不能因大于一个时隙就丢弃。
    返回(线速发送比特数,完整发送的Pending列表)；空队列返回(0,[])。
    """
    budget = cfg.slot_bits
    wire_bits = 0
    completed = []
    # 共享FIFO：始终服务队首，预算有剩余再顺延到下一条，绝不跳队或交错。
    while budget > 0 and queue:
        record = queue[0]
        # 包头已在准入时计入remaining_wire_bits，此处只按剩余量扣预算。
        send = min(budget, record.remaining_wire_bits)
        record.remaining_wire_bits -= send
        budget -= send
        wire_bits += send
        if record.remaining_wire_bits:
            # 大分组跨tick：保留队首剩余量，下个tick继续，不丢弃也不重加包头。
            break
        queue.popleft()
        completed.append(record)
    return wire_bits, completed
