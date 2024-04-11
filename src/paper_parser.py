import os
import re
import time
import copy
import json
import requests
from lxml import etree
from datetime import datetime


PATTERN = re.compile(r'.*?Date:(?P<date>.*?GMT).*?Title:(?P<title>.*?)Authors:(?P<authors>.*?)Categories.*?\\\\(?P<abstract>.*?)\\\\.*?(?P<url>https://arxiv.org/.*?)[ ,].*?', re.DOTALL)
PATTERN_revised = re.compile(r'.*?(?P<date>replaced.*?GMT).*?Title:(?P<title>.*?)Authors:(?P<authors>.*?)(?P<abstract>Categories.*?).*?(?P<url>https://arxiv.org/.*?)[ ,].*?', re.DOTALL)

TEMPLATE = """
`[{arxiv_id}] {title} <{url}>`__

::

    {date}
    {authors}

{abstract}

{history}

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
        if i > 0:
            history += f'[v{i}] {content.strip()}'
        else:
            history += content.strip()
    return history


class PaperParser:
    def __init__(self, key_words: list=['LLM', 'large language model']) -> None:
        self.key_words = key_words

    def extra_paper(self, input_file: str, output_file: str, title: str=None, date: str=None):
        print(input_file)
        lines = open(input_file, encoding='utf-8').readlines()
        text = ''.join(lines)
        text_list = re.split('---------------+', text)

        all_out = open(input_file.replace('.txt', '.json'), mode='w', encoding='utf-8')
        outfile = open(output_file, mode='w', encoding='utf-8')
        outfile.write(f"{title}\n========\n\n")
        redundant = ''
        num = 0
        is_first = True
        for content in text_list:
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

                item = dict(
                    date=date,
                    arxiv_id=arxiv_id,
                    url=paper['url'],
                    title=title,
                    date=paper['date'],
                    authors=authors,
                    abstract=abstract,
                    history=history
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
                item.pop('date')
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
        print("-------------------------------- Redundant --------------------------------")
        print(redundant.strip())
        print("---------------------------------------------------------------------------\n")
        outfile.close()
