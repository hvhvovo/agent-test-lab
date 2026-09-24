"""交互式单样例测试：密钥仅在当前进程中使用，不写入文件。"""
import os
import sys
from getpass import getpass
from scripts.evaluate_llm import main as evaluate


def main():
    print('将调用 DeepSeek Flash：1条合成样例，最多5轮，每轮最多2000输出Token，无自动重试。')
    print('这会产生API费用；未截断不代表语义正确。输入为空可退出。')
    key = getpass('请粘贴API密钥并回车（不显示）：').strip()
    if not key:
        print('未输入密钥，未发送请求。')
        return
    names = ('LLM_API_KEY', 'LLM_BASE_URL', 'LLM_MODEL')
    previous = {name: os.environ.get(name) for name in names}
    original_argv = sys.argv[:]
    try:
        os.environ.update(LLM_API_KEY=key, LLM_BASE_URL='https://api.deepseek.com',
                          LLM_MODEL='deepseek-flash')
        sys.argv = ['evaluate_llm', '--live', '--limit', '1', '--repeat', '1',
                    '--max-output-tokens', '2000', '--disable-thinking']
        evaluate()
    finally:
        sys.argv = original_argv
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


if __name__ == '__main__':
    main()
