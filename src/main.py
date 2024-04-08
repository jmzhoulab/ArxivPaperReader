import os
import re

from .email_helper import EmailReader
from .parser import PaperParser


BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
DOCS_DIR = os.path.join(BASE_DIR, 'docs', 'source')


def get_latest_date():
    latest_file = os.path.join(BASE_DIR, 'latest.date')
    latest_date = '20230101'
    if os.path.exists(latest_file):
        content = ''.join(open(latest_file, 'r').readlines())
        latest_date = re.findall('(\d{8})', content)
        if latest_date:
            latest_date = latest_date[0]
    return latest_date


def update_latest_date(latest_date):
    latest_file = os.path.join(BASE_DIR, 'latest.date')
    with open(latest_file, 'w') as f:
        f.write(latest_date)



if __name__=='__main__':
    latest_date = get_latest_date()

    parser = PaperParser()

    email_reader = EmailReader('xxxx@163.com', 'xxxx')
    emails = email_reader.parse_email_server(min_date=latest_date[2:], part_dir=DATA_DIR)

    for email in emails:
        if len(email['parts']) == 0:
            print("未发现附件", email)
            continue
        for part_file in email['parts']:
            parser.extra_paper(input_file=part_file, output_file=)



    last_date = sorted([f.split('_')[1].split('.')[0] for f in os.listdir(data_dir) if f.endswith('.txt')])
    if len(last_date) > 0:
        last_date = last_date[-1]
    else:
        last_date = ''
    print(f"last_date: {last_date}")

    # 读取邮件的内容

    items = obj.parse_email_server(min_date=last_date)
    print("读取邮件完成~")
    # for item in items:
    #     print(item)
    #     show_item = copy.deepcopy(item)
    #     show_item['content'] = item['content'][:50]
    #     print(show_item)
    #     file_name = 'paper_' + item['time'] + '.txt'
    #     print(f"Saved content to file {file_name}")
    #     with open(os.path.join(data_dir, file_name), mode='w', encoding='utf-8') as writer:
    #         writer.write(item['content'])

    # 解析文章
    files = os.listdir(data_dir)
    for file in files:
        if file.endswith('.md'):
            continue
        if file.replace('.txt', '.md') in files:
            continue
        extra_paper(os.path.join(data_dir, file))
