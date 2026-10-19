"""学生自拟用例：手算基准 + 三个反例，检验模型规则而不是照抄实现。

所有期望值都先用纸笔算好再写成断言，注释保留计算过程。
每个用例对应PRD第6章的一条规则，失败时能直接指出实现错在哪里。
"""
from collections import deque

from src.models import Arrival, Config, Pending
from src.metrics import summarize
from src.part1_circuit import serve_circuit
from src.part2_packet import serve_packet
from src.utils import simulate


def test_two_user_hand_calc():
    """PRD 6.1两用户手算基准：2用户、2 tick、128 bit/tick、包头32 bit。

    只有tick 0的用户1到达一条96 bit记录。
    电路：tick 0归用户0，用户1的记录只能等tick 1；96 bit在一个时隙发完，
          完成边界为tick 2，时延=2 tick=2 ms；线路忙碌率=96/256=37.5%。
    分组：tick 0直接发96+32=128 bit，完成边界为tick 1，时延=1 ms；
          线路忙碌率=128/256=50%。
    两者有效载荷利用率都是96/256=37.5%，说明同样的吞吐可以对应不同的时延与线速占用。
    """
    cfg = Config(users=2, ticks=2)
    arrivals = [Arrival(0, 1, 96)]

    circuit = summarize(simulate(arrivals, cfg, 'circuit'), cfg)
    packet = summarize(simulate(arrivals, cfg, 'packet'), cfg)

    for m in (circuit, packet):
        assert m['payload_utilization'] == 96 / 256
        assert m['loss_ratio'] == 0
        assert m['backlog_payload_bits'] == 0
    assert (circuit['mean_delay_ms'], circuit['wire_utilization']) == (2.0, 96 / 256)
    assert (packet['mean_delay_ms'], packet['wire_utilization']) == (1.0, 128 / 256)


def test_circuit_never_lends_idle_slot():
    """反例1：空闲时隙不能借给其他用户。

    2用户、128 bit/tick。tick 0属于用户0，但用户0队列为空；用户1有96 bit。
    手算：tick 0必须返回(0, [])且用户1的记录原封不动；tick 1才轮到用户1，
          发送96 bit并完成。
    若实现把空时隙“顺路”让给用户1，tick 0就会返回96，奖励了违规的统计复用。
    """
    record = Pending(1, 0, 96, 96)
    queues = [deque(), deque([record])]
    cfg = Config(users=2)

    assert serve_circuit(queues, 0, cfg) == (0, [])
    assert len(queues[1]) == 1 and record.remaining_wire_bits == 96

    wire, done = serve_circuit(queues, 1, cfg)
    assert wire == 96 and done == [record] and not queues[1]


def test_packet_header_counted_once():
    """反例2：跨tick续传不得重复加包头。

    载荷200 bit，准入后remaining_wire_bits=200+32=232。
    tick 0发送128 bit，剩104 bit；tick 1发送104 bit并完成。
    手算总发送量=128+104=232=200+32，若每个tick重加32 bit头会变成264 bit。
    """
    record = Pending(0, 0, 200, 232)
    queue = deque([record])
    cfg = Config()

    wire0, done0 = serve_packet(queue, 0, cfg)
    assert (wire0, done0) == (128, [])
    assert record.remaining_wire_bits == 104

    wire1, done1 = serve_packet(queue, 1, cfg)
    assert (wire1, done1) == (104, [record])
    assert wire0 + wire1 == 232


def test_partial_send_not_delivered():
    """反例3：部分发送的记录不能提前记成交付。

    1用户、3 tick、128 bit/tick，tick 0到达200 bit。
    手算：tick 0发128、tick 1发72，在tick 2边界完成，时延=2 ms；
          交付200 bit，有效利用率=200/(3*128)，无丢失无积压。
    若实现在tick 0就报告完成，simulate会因remaining_wire_bits!=0抛出ValueError。
    """
    cfg = Config(users=1, ticks=3)
    raw = simulate([Arrival(0, 0, 200)], cfg, 'circuit')
    metrics = summarize(raw, cfg)

    assert raw['delivered_payload_bits'] == 200
    assert raw['backlog_payload_bits'] == 0
    assert metrics['payload_utilization'] == 200 / 384
    assert (metrics['mean_delay_ms'], metrics['max_delay_ms']) == (2.0, 2.0)


def test_backlog_has_no_delay_sample():
    """反例4：窗口末尾未完成的数据计积压，不能被当成0 ms送达。

    分组模型、1个tick窗口、一条200 bit记录：需要200+32=232 bit，
    一个时隙只有128 bit，因此窗口内交付0 bit、积压200 bit，
    平均/最大时延必须为None，守恒式仍成立。
    """
    cfg = Config(ticks=1)
    raw = simulate([Arrival(0, 0, 200)], cfg, 'packet')
    metrics = summarize(raw, cfg)

    assert raw['delivered_payload_bits'] == 0
    assert raw['backlog_payload_bits'] == 200
    assert metrics['payload_utilization'] == 0
    assert metrics['mean_delay_ms'] is None and metrics['max_delay_ms'] is None
