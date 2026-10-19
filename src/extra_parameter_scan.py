"""选做参数扫描：只改变包头长度或缓存容量，用于说明基线结论的适用条件。

基线8组结果固定为 Config()（header_bits=32、buffer_payload_bits=4096、seed=2026），
本脚本把变化量单独写到 results/extra/，不混入 results/comparison.*。
运行：python src/extra_parameter_scan.py
"""
from pathlib import Path
import csv
import json
import sys

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.models import Config
from src.metrics import summarize
from src.utils import make_traffic, simulate

SCENARIOS = ('continuous', 'staggered_burst', 'synchronized_burst', 'light_random')
HEADERS = (0, 16, 32, 64, 96)
BUFFERS = (512, 1024, 2048, 4096, 8192)
FIELDS = ('payload_utilization', 'wire_utilization', 'mean_delay_ms',
          'max_delay_ms', 'loss_ratio', 'backlog_payload_bits')


def scan(varied, values, **overrides):
    """对每个取值跑四种业务，返回(行列表, 图用的汇总数据)。"""
    rows = []
    for value in values:
        cfg = Config(**{varied: value}, **overrides)
        for scenario in SCENARIOS:
            arrivals = make_traffic(scenario, cfg, seed=2026)
            for mode in ('circuit', 'packet'):
                metrics = summarize(simulate(arrivals, cfg, mode), cfg)
                rows.append(dict(varied=varied, value=value, scenario=scenario,
                                 mode=mode, **metrics))
    return rows


def write_csv(path, rows):
    with path.open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def plot(header_rows, buffer_rows, output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np

    fig, axs = plt.subplots(1, 2, figsize=(11, 4.2))
    for scenario, color in (('continuous', '#27638b'), ('synchronized_burst', '#d27a35')):
        sub = [r for r in header_rows if r['scenario'] == scenario and r['mode'] == 'packet']
        axs[0].plot([r['value'] for r in sub], [r['payload_utilization'] for r in sub],
                    'o-', color=color, label='packet/' + scenario)
        sub = [r for r in header_rows if r['scenario'] == scenario and r['mode'] == 'circuit']
        axs[0].plot([r['value'] for r in sub], [r['payload_utilization'] for r in sub],
                    's--', color=color, alpha=.45, label='circuit/' + scenario)
    axs[0].set(xlabel='Packet header (bit)', ylabel='Payload utilization',
               title='Header overhead only affects the packet model')
    axs[0].grid(alpha=.2)
    axs[0].legend(fontsize=7)

    for scenario, color in (('staggered_burst', '#27638b'), ('synchronized_burst', '#d27a35')):
        for mode, ls in (('circuit', 's--'), ('packet', 'o-')):
            sub = [r for r in buffer_rows if r['scenario'] == scenario and r['mode'] == mode]
            axs[1].plot([r['value'] for r in sub], [r['loss_ratio'] for r in sub],
                        ls, color=color, alpha=.85, label=mode + '/' + scenario)
    axs[1].set(xlabel='Payload buffer (bit)', ylabel='Payload loss ratio',
               title='Buffer size trades loss against queueing', xscale='log')
    axs[1].set_xticks(BUFFERS, [str(v) for v in BUFFERS])
    axs[1].minorticks_off()
    axs[1].grid(alpha=.2)
    axs[1].legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(output / 'parameter_scan.png', dpi=150)
    plt.close(fig)


def main():
    output = Path(__file__).resolve().parents[1] / 'results' / 'extra'
    output.mkdir(parents=True, exist_ok=True)
    header_rows = scan('header_bits', HEADERS)
    buffer_rows = scan('buffer_payload_bits', BUFFERS)
    write_csv(output / 'header_scan.csv', header_rows)
    write_csv(output / 'buffer_scan.csv', buffer_rows)
    (output / 'parameter_scan.json').write_text(json.dumps(dict(
        seed=2026,
        base_config=Config().__dict__,
        varied={'header_bits': list(HEADERS), 'buffer_payload_bits': list(BUFFERS)},
        scenarios=list(SCENARIOS),
        header_scan=header_rows,
        buffer_scan=buffer_rows,
    ), ensure_ascii=False, indent=2), encoding='utf-8')
    plot(header_rows, buffer_rows, output)
    print('Generated header_scan.csv, buffer_scan.csv, parameter_scan.json, parameter_scan.png in ' + str(output))
    return header_rows, buffer_rows


if __name__ == '__main__':
    main()
