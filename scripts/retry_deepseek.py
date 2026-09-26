"""只重跑两个失败场景和一次受控注入检查，隐藏输入密钥。"""
import argparse
import os
import sys
from getpass import getpass
from scripts.evaluate_llm import main as evaluate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case-id', action='append', choices=['ownership', 'number', 'injection'])
    args = parser.parse_args()
    cases = args.case_id or ['ownership', 'number', 'injection']
    cases = list(dict.fromkeys(cases))
    print(f'{len(cases)}条任务：{", ".join(cases)}。会产生API费用，无自动重试。')
    key=getpass('请粘贴API密钥（不显示，空值退出）：').strip()
    if not key:
        return
    previous={k:os.environ.get(k) for k in ('LLM_API_KEY','LLM_BASE_URL','LLM_MODEL')}
    argv=sys.argv[:]
    try:
        os.environ.update(LLM_API_KEY=key,LLM_BASE_URL='https://api.deepseek.com',LLM_MODEL='deepseek-flash')
        sys.argv=['evaluate_llm','--live','--repeat','1','--max-output-tokens','2000','--disable-thinking',
                  '--controlled-injection']
        for case_id in cases:
            sys.argv.extend(['--case-id', case_id])
        evaluate()
    finally:
        sys.argv=argv
        for k,v in previous.items():
            if v is None: os.environ.pop(k,None)
            else: os.environ[k]=v


if __name__=='__main__':
    main()
