import os
import re
import json
import requests
from lxml import etree
from tqdm import tqdm

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
CACHE_DIR = os.path.join(BASE_DIR, '.cache')

PATTERN = re.compile(r'.*?Date:(?P<date>.*?GMT).*?Title:(?P<title>.*?)Authors:(?P<authors>.*?)Categories.*?\\\\(?P<abstract>.*?)\\\\.*?(?P<url>https://arxiv.org/.*?)[ ,].*?', re.DOTALL)
PATTERN_revised = re.compile(r'.*?(?P<date>replaced.*?GMT).*?Title:(?P<title>.*?)Authors:(?P<authors>.*?)(?P<abstract>Categories.*?).*?(?P<url>https://arxiv.org/.*?)[ ,].*?', re.DOTALL)

TEMPLATE = """
`[{arxiv_id}] {title} <{url}>`__

::

    {submitdate}
    {authors}

{abstract}

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
    def __init__(self, key_words: list=['LLM', 'large language model']) -> None:
        self.key_words = key_words

    def extra_paper_from_json(self, input_file: str, output_file: str, title: str=None):
        lines = open(input_file, encoding='utf-8').readlines()
        file_name = os.path.basename(input_file)
        outfile = open(output_file, mode='w', encoding='utf-8')
        outfile.write(f"{title}\n========\n\n")
        for content in tqdm(lines, position=1, desc=file_name, leave=False, colour='green', ncols=80):
            item = json.loads(content.strip())
            # 只考虑包含关键词的
            title_abstract = item['title'].lower() + '\n' + item['abstract'].lower()
            if not any([kw.lower() in title_abstract for kw in self.key_words]):
                continue
            item.pop('datadate')
            out_content = TEMPLATE.format(**item)
            # print(out_content)
            if not is_first:
                outfile.write('\n' + '-'*12 + '\n\n')
            outfile.write(out_content+'\n')
            outfile.flush()
            is_first = False
        outfile.close()

    def extra_paper(self, input_file: str, output_file: str, title: str=None, date: str=None):
        if input_file.endswith('.json'):
            self.extra_paper_from_json(input_file, output_file, title)

        lines = open(input_file, encoding='utf-8').readlines()
        text = ''.join(lines)
        text_list = re.split('---------------+', text)

        all_out = open(input_file.replace('.txt', '.json'), mode='w', encoding='utf-8')
        outfile = open(output_file, mode='w', encoding='utf-8')
        outfile.write(f"{title}\n========\n\n")
        redundant = ''
        num = 0
        is_first = True
        file_name = os.path.basename(input_file)
        for content in tqdm(text_list, position=1, desc=file_name, leave=False, colour='green', ncols=80):
            result = PATTERN.match(content)
            result = result or PATTERN_revised.match(content)
            if result:
                num += 1
                paper = result.groupdict()
                paper = {k: v.strip() for k, v in paper.items()}
                title = paper['title'].replace('\n', '').replace('  ', ' ')
                authors = ' '.join([a.strip() for a in paper['authors'].split('\n')])
                abstract = ''.join([a.strip()+'\n' if a.strip().endswith('.') else a.strip()+' ' for a in paper['abstract'].strip().split('\n')]).strip()

                history = ''
                if 'replaced with revised version' in paper['date']:
                    response = requests.get(url=paper['url'])
                    abstract = parse_abstract(response.content)
                    history = parse_history(response.content)

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

                # 只考虑包含关键词的
                title_abstract = title.lower() + '\n' + abstract.lower()
                if not any([kw.lower() in title_abstract for kw in self.key_words]):
                    # print("================= SKIP =================")
                    # print("Title:", title)
                    # print("Abstract:", abstract)
                    # print("=========================================")
                    continue
                item.pop('datadate')
                out_content = TEMPLATE.format(**item)
                # print(out_content)
                if not is_first:
                    outfile.write('\n' + '-'*12 + '\n\n')
                outfile.write(out_content+'\n')
                outfile.flush()
                all_out.flush()
                is_first = False
                # print(f"num {num}, {input_file}\n{title}\n")
            else:
                redundant += content.strip() + '\n'
        print("\n-------------------------------- Redundant --------------------------------")
        print(redundant.strip())
        print("---------------------------------------------------------------------------\n")
        outfile.close()
