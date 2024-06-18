import os
import re
import json
import requests
from lxml import etree
from tqdm import tqdm

from translate import YoudaoTranslator

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
CACHE_DIR = os.path.join(BASE_DIR, '.cache')

PATTERN = re.compile(r'.*?Date:(?P<date>.*?GMT).*?Title:(?P<title>.*?)Authors:(?P<authors>.*?)Categories.*?\\\\(?P<abstract>.*?)\\\\.*?(?P<url>https://arxiv.org/.*?)[ ,].*?', re.DOTALL)
PATTERN_revised = re.compile(r'.*?(?P<date>replaced.*?GMT).*?Title:(?P<title>.*?)Authors:(?P<authors>.*?)(?P<abstract>Categories.*?).*?(?P<url>https://arxiv.org/.*?)[ ,].*?', re.DOTALL)

TEMPLATE = """
`[{arxiv_id}] {title} <{url}>`__ {title_zh}

::

    {submitdate}
    {authors}

{abstract}

------------
""".strip()


def parse_abstract(byte_content):
    e_html = etree.HTML(byte_content)
    elements = e_html.xpath("//blockquote[@class='abstract mathjax']")

    abstract = ''
    for element in elements:
        abstract += element.xpath("string()").strip()
    abstract = re.sub("^Abstract:", "", abstract).strip()
    return abstract


def parse_history(byte_content):
    e_html = etree.HTML(byte_content)
    elements = e_html.xpath("//div[@class='submission-history']")

    text = ''
    for element in elements:
        text += element.xpath("string()").strip()
    history = ''
    for i, content in enumerate(re.split('\[v\d+\]', text)):
        content = content.strip() + '\n'
        if i > 0:
            history += f'[v{i}] {content}'
        else:
            history += content
    return history.strip()


class PaperParser:
    def __init__(self,
                 translator: YoudaoTranslator=None,
                 filter_words: list=['LLM', 'large language model'],
                 category_words: dict={}) -> None:
        self.translator = translator
        self.filter_words = filter_words
        self.category_words = category_words
    
    def update_insert_file(self, filepth, title, items):
        if filepth is None or len(items) == 0:
            return None
        head_content = []
        end_head = False
        last_content = []
        with open(filepth, "r", encoding='utf-8') as file:
            for line in file:
                if not end_head:
                    head_content.append(line)
                else:
                    last_content.append(line)
                if '======' in line:
                    end_head = True
        all_content = ''.join(head_content)
        all_content += '\n\n' + f'**{title}({len(items)})**' + '\n\n'
        all_content += '\n\n'.join(items) + '\n'
        all_content += ''.join(last_content)
        with open(filepth, "w", encoding='utf-8') as file:
            file.write(all_content)

    def add_category_items(self, category_items, content, item):
        added = False
        for key, items in category_items.items():
            words = self.category_words[key]
            if any([w.lower() in content.lower() for w in words]):
                items.append(item)
                added = True
        return added

    def extra_paper_from_json(self, input_file: str, output_file: str, title: str=None):
        lines = open(input_file, encoding='utf-8').readlines()
        file_name = os.path.basename(input_file)
        outfile = open(output_file, mode='w', encoding='utf-8')
        outfile.write(f"{title}\n========\n\n")
        outfile.flush()

        category_items = {key: [] for key in self.category_words.keys()}
        other_items = []

        index_contents = []

        for content in tqdm(lines, position=1, desc=file_name, leave=False, colour='green', ncols=80):
            item = json.loads(content.strip())
            # 只考虑包含关键词的
            title_abstract = item['title'].lower() + '\n' + item['abstract'].lower()
            if not any([kw.lower() in title_abstract for kw in self.filter_words]):
                continue
            item.pop('datadate')
            title_zh = ''
            try:
                if self.translator is not None:
                    title_zh = self.translator.translate(text=item['title'])
            except Exception as e:
                print(f"translate error {e}")
            out_content = TEMPLATE.format(title_zh=title_zh, **item)
            added = self.add_category_items(category_items, item['title'], out_content)
            if not added:
                other_items.append(out_content)
                index_contents.append(f"`[{item['arxiv_id']}] {item['title']} <{item['url']}>`__ {title_zh}".strip())
        
        category_items['Other'] = other_items
        category_items['Index'] = index_contents
        for key, items in category_items.items():
            if len(items) == 0:
                continue
            sub_title = f'{key} ({len(items)})'
            overline = '-'*len(sub_title)
            outfile.write(f'{overline}\n{sub_title}\n{overline}\n\n')
            outfile.write('\n\n'.join(items)+'\n\n')
            outfile.flush()
        outfile.close()

    def extra_paper(self, input_file: str, output_file: str, title: str=None, date: str=None):
        if input_file.endswith('.json'):
            self.extra_paper_from_json(input_file, output_file, title)
            return None

        lines = open(input_file, encoding='utf-8').readlines()
        text = ''.join(lines)
        text_list = re.split('---------------+', text)

        all_out = open(input_file.replace('.txt', '.json'), mode='w', encoding='utf-8')
        redundant = ''
        file_name = os.path.basename(input_file)
        for content in tqdm(text_list, position=1, desc=file_name, leave=False, colour='green', ncols=80):
            result = PATTERN.match(content)
            result = result or PATTERN_revised.match(content)
            if result:
                paper = result.groupdict()
                paper = {k: v.strip() for k, v in paper.items()}
                title = paper['title'].replace('\n', '').replace('  ', ' ')
                authors = ' '.join([a.strip() for a in paper['authors'].split('\n')])
                abstract = ''.join([a.strip()+'\n' if a.strip().endswith('.') else a.strip()+' ' for a in paper['abstract'].strip().split('\n')]).strip()
                history = ''
                if 'replaced with revised version' in paper['date']:
                    try:
                        response = requests.get(url=paper['url'], timeout=5)
                        abstract = parse_abstract(response.content)
                        history = parse_history(response.content)
                    except Exception as e:
                        print("获取历史版本信息错误", title)
                        print("错误异常信息", e)
                arxiv_id = re.findall('https://arxiv.org/abs/(\d+\.\d+)', paper['url'])[0]
                submitdate = paper['date']
                if history:
                    submitdate = submitdate + '\n    ' + history.replace('\n', '\n    ')
                item = dict(
                    datadate=date,
                    arxiv_id=arxiv_id,
                    url=paper['url'],
                    title=title,
                    submitdate=submitdate,
                    authors=authors,
                    abstract=abstract
                )
                all_out.write(json.dumps(item)+'\n')
        print("\n-------------------------------- Redundant --------------------------------")
        print(redundant.strip())
        print("---------------------------------------------------------------------------\n")
        all_out.close()
        self.extra_paper_from_json(input_file.replace('.txt', '.json'), output_file, date)
