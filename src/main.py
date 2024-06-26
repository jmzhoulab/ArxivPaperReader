import os
import re
import sys
import textwrap
from tqdm import tqdm
from dotenv import load_dotenv

load_dotenv()

from email_helper import EmailReader
from paper_parser import PaperParser
from translate import YoudaoTranslator


BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'datasets')
DOCS_DIR = os.path.join(BASE_DIR, 'docs', 'source')

if sys.platform.startswith('linux'):            # Linux
    HOME_DIR = os.path.expanduser("~")
elif sys.platform.startswith('darwin'):         # MacOS
    HOME_DIR = os.getenv("HOME")
else:
    HOME_DIR = os.getenv("USERPROFILE")             # Windows


def get_latest_date():
    latest_file = os.path.join(BASE_DIR, 'latest.date')
    latest_date = '230101'
    if os.path.exists(latest_file):
        content = ''.join(open(latest_file, 'r').readlines())
        latest_date = re.findall('(\d{6})', content)
        if latest_date:
            latest_date = latest_date[0]
    return latest_date


def update_latest_date(latest_date):
    latest_file = os.path.join(BASE_DIR, 'latest.date')
    with open(latest_file, 'w') as f:
        f.write(latest_date)


def get_save_dir(time: str):
    name = f'20{time[:4]}'
    save_dir = os.path.join(DOCS_DIR, name)
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
        with open(os.path.join(save_dir, 'index.rst'), 'w') as f:
            f.write(
                textwrap.dedent(f"""
                {name}
                ======

                .. toctree::
                   :glob:
                   :maxdepth: 3
                """).lstrip()
            )
        
        # update root index.rst
        index_lines = open(os.path.join(DOCS_DIR, 'index.rst')).readlines()
        index_lines.append(f'   {name}/index\n')
        idx = index_lines.index('.. toctree::\n') + 1
        with open(os.path.join(DOCS_DIR, 'index.rst'), 'w') as f:
            f.writelines(index_lines[:idx]+['\n'])
            f.writelines(sorted(set(index_lines[idx:]), reverse=True))
    return save_dir


def update_index(file_path: str):
    index_dir = os.path.dirname(file_path)
    file_name = os.path.basename(file_path)

    index_lines = open(os.path.join(index_dir, 'index.rst')).readlines()
    index_lines.append(f'   {file_name}\n')
    idx = index_lines.index('   :maxdepth: 3\n') + 1
    with open(os.path.join(index_dir, 'index.rst'), 'w') as f:
        f.writelines(index_lines[:idx]+['\n'])
        f.writelines(sorted(set(index_lines[idx:]), reverse=True))


def paper_from_email(latest_date: str):
    email_user = os.getenv('EMAIL_USER', None)
    auth_code = os.getenv('EMAIL_AUTH_CODE', None)

    assert email_user and auth_code, "Missing email user or auth code."

    email_reader = EmailReader(email_user, auth_code)
    emails = email_reader.parse_email_server(min_date=latest_date, part_dir=DATA_DIR)
    return emails


def paper_from_path(path: str, min_date: str, max_date: str=None, filetype: str='txt'):
    print('scan dir:', path)
    items = []
    max_date = max_date or '999999'
    names = sorted(os.listdir(path))
    for name in names:
        sub_path = os.path.join(path, name)
        if os.path.isdir(sub_path):
            items.extend(paper_from_path(sub_path, min_date, max_date))
            continue
        if not name.endswith(f'.{filetype}'):
            continue
        json_path = re.sub(f'.{filetype}$', '.json', sub_path)
        if os.path.exists(json_path):
            sub_path = json_path
        file_date = re.findall('\d{6}', name)[0]
        if file_date <= min_date or file_date > max_date:
            continue
        items.append({'time': file_date, 'parts': [sub_path]})
    return items


if __name__=='__main__':
    latest_date = get_latest_date()
    translator = YoudaoTranslator(api_key=os.getenv('YOUDAO_API_KEY', None),
                            api_secret=os.getenv('YOUDAO_API_SECRET', None),
                            cache_dir=os.path.join(HOME_DIR, '.cache', 'youdao'),
                            delta_t=1)
    parser = PaperParser(
        translator=translator,
        category_words={
            'Survey': ['survey'],
            'Benchmark': ['benchmark'],
            'Accelerate': ['Accelerate', 'Decoding', 'Efficient', 'Accelerating', 'KV cache'],
            'In-Context Learning': ['In-Context Learning', 'Memory Learning'],
            'Reasoning': ['Reasoning'],
            'ToolUse': ['tool', 'api'],
            'Retrieval-Augmented': ['Retrieval', 'Retriever', 'RAG'],
            'Agent': ['Agent']
        })

    # items = paper_from_email(latest_date=latest_date)
    items = paper_from_path(path=DATA_DIR, min_date=latest_date, filetype='txt')
    max_date = latest_date
    for item in tqdm(items, position=0, desc=f'Processing', leave=False, colour='green', ncols=80):
        if len(item['parts']) == 0:
            print("未发现附件", item)
            continue
        # print('============', item['time'], '============')
        save_dir = get_save_dir(item['time'])
        output_file = os.path.join(save_dir, item['time']+'.rst')
        parser.extra_paper(input_file=item['parts'][0], output_file=output_file, title=item['time'], date=item['time'])

        update_index(file_path=output_file)

        if item['time'] > max_date:
            max_date = item['time']
            update_latest_date(latest_date=max_date)
