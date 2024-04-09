import os
import re
import time
import copy
import requests
from datetime import datetime


PATTERN = re.compile(r'.*?Date:(?P<date>.*?GMT).*?Title:(?P<title>.*?)Authors:(?P<authors>.*?)Categories.*?\\\\(?P<abstract>.*?)\\\\.*?(?P<url>https://arxiv.org/.*?)[ ,].*?', re.DOTALL)
PATTERN_revised = re.compile(r'.*?(?P<date>replaced.*?GMT).*?Title:(?P<title>.*?)Authors:(?P<authors>.*?)(?P<abstract>Categories.*?).*?(?P<url>https://arxiv.org/.*?)[ ,].*?', re.DOTALL)

TEMPLATE = """`[{arxiv_id}] {title} <{url}>`__

::

    {date}
    {authors}

{abstract}

------------
"""


class PaperParser:
    def __init__(self, key_words: list=['LLM', 'large language model']) -> None:
        self.key_words = key_words

    def extra_paper(self, input_file: str, output_file: str, title: str=None):
        print(input_file)
        lines = open(input_file, encoding='utf-8').readlines()
        text = ''.join(lines)
        text_list = re.split('---------------+', text)

        outfile = open(output_file, mode='w', encoding='utf-8')
        outfile.write(f"{title}\n========\n\n")
        redundant = ''
        num = 0
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

                # 只考虑包含关键词的
                title_abstract = title.lower() + '\n' + abstract.lower()
                if not any([kw.lower() in title_abstract for kw in self.key_words]):
                    # print("================= SKIP =================")
                    # print("Title:", title)
                    # print("Abstract:", abstract)
                    # print("=========================================")
                    continue

                arxiv_id = re.findall('https://arxiv.org/abs/(\d+\.\d+)', paper['url'])[0]

                out_content = TEMPLATE.format(arxiv_id=arxiv_id,
                                        url=paper['url'],
                                        title=title,
                                        date=paper['date'],
                                        authors=authors,
                                        abstract=abstract)
                # print(out_content)
                outfile.write(out_content+'\n')
                outfile.flush()
                # print(f"num {num}, {input_file}\n{title}\n")
            else:
                redundant += content.strip() + '\n'
        print("-------------------------------- Redundant --------------------------------")
        print(redundant.strip())
        print("---------------------------------------------------------------------------\n")
        outfile.close()
