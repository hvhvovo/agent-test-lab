"""12个合成开发场景各重复3次；仅在本机输入密钥后调用模型。"""
import os
import sys
from pathlib import Path
from getpass import getpass
from scripts.evaluate_llm import main as evaluate


def main():
    print('批量评测：12个场景 × 3次 = 36条任务，顺序执行，会产生API费用。')
    print('每轮最多2000输出Token；一条任务可能有多轮请求，无自动重试。')
    print('Ctrl+C可停止；已完成结果保存在reports，重新运行会从头开始。')
    key = getpass('请粘贴API密钥（不显示，直接回车退出）：').strip()
    if not key:
        return
    previous = {k: os.environ.get(k) for k in ('LLM_API_KEY', 'LLM_BASE_URL', 'LLM_MODEL')}
    argv = sys.argv[:]
    try:
        os.environ.update(LLM_API_KEY=key, LLM_BASE_URL='https://api.deepseek.com', LLM_MODEL='deepseek-flash')
        dataset = Path(__file__).resolve().parents[1] / 'evals' / 'grounding_batch.json'
        sys.argv = ['evaluate_llm', '--live', '--dataset', str(dataset), '--repeat', '3',
                    '--max-output-tokens', '2000', '--disable-thinking', '--controlled-injection']
        evaluate()
    finally:
        sys.argv = argv
        for k, v in previous.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


if __name__ == '__main__':
    main()
