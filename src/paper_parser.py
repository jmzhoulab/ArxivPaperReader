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
                 key_words: list=['LLM', 'large language model'],
                 core_words: list=[],
                 survey_file: str=None,
                 benchmark_file: str=None) -> None:
        self.key_words = key_words
        self.core_words = core_words
        self.survey_file = survey_file
        self.benchmark_file = benchmark_file
    
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

    def extra_paper_from_json(self, input_file: str, output_file: str, title: str=None):
        lines = open(input_file, encoding='utf-8').readlines()
        file_name = os.path.basename(input_file)
        outfile = open(output_file, mode='w', encoding='utf-8')
        outfile.write(f"{title}\n========\n\n")
        outfile.flush()
        core_items = []
        other_items = []
        survey_itmes = []
        benchmark_itmes = []

        for content in tqdm(lines, position=1, desc=file_name, leave=False, colour='green', ncols=80):
            item = json.loads(content.strip())
            # 只考虑包含关键词的
            title_abstract = item['title'].lower() + '\n' + item['abstract'].lower()
            if not any([kw.lower() in title_abstract for kw in self.key_words]):
                continue
            item.pop('datadate')
            out_content = TEMPLATE.format(**item)
            if any([kw.lower() in item['title'].lower() for kw in self.core_words]):
                core_items.append(out_content)
            else:
                other_items.append(out_content)
            if 'survey' in item['title'].lower():
                survey_itmes.append(out_content)
            if 'benchmark' in item['title'].lower():
                benchmark_itmes.append(out_content)
        if self.core_words:
            outfile.write('**About ' + ', '.join(self.core_words) + f' papers({len(core_items)})**\n\n')
            outfile.write('\n\n'.join(core_items)+'\n\n')
            outfile.flush()
        
        self.update_insert_file(self.survey_file, title, survey_itmes)
        self.update_insert_file(self.benchmark_file, title, benchmark_itmes)
        
        outfile.write('**About other LLM '+ f' papers({len(other_items)})**\n\n')
        outfile.write('\n\n'.join(other_items))
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
        print("\n-------------------------------- Redundant --------------------------------")
        print(redundant.strip())
        print("---------------------------------------------------------------------------\n")
        all_out.close()
        self.extra_paper_from_json(input_file.replace('.txt', '.json'), output_file, title)
