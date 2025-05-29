import os
import re
import requests
import openai
from .models import Result

OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
openai.api_key = OPENAI_API_KEY
oai_clinet = openai.Client()

arxiv_pattern = r"https?://(?:www\.)?arxiv\.org/abs/(\d{4}\.\d{4,5})(?:v\d+)?"


def fetch_arxiv_info(arxiv_id):
    """arXiv IDからタイトルとアブストラクトを取得する関数"""
    url = f"http://export.arxiv.org/api/query?id_list={arxiv_id}"
    response = requests.get(url)
    if response.status_code == 200:
        # XMLの解析
        from xml.etree import ElementTree as ET
        root = ET.fromstring(response.text)

        title = ""
        abstract = ""

        titles = root.findall(".//{http://www.w3.org/2005/Atom}title")
        if len(titles) > 0:
            title = titles[-1].text.strip()

        abstracts = root.findall(".//{http://www.w3.org/2005/Atom}summary")
        if len(abstracts) > 0:
            abstract = abstracts[-1].text.strip()

        return title, abstract
    return None, None


def summarize(title, abstract):
    system_prompt = (
        "あなたは優秀な博士課程の研究員です。研究に関する深い洞察ができ、それを平易な言葉で表現することができます。"
        "与えられた論文の概要に基づいて、文中に書かれている内容から概要・課題・貢献・結論について簡潔かつ正確に述べてください。"
        "概要は、どのような課題に対してどんな手段で解決したかについて150文字程度で記載してください。"
        "英語で表記するところのみ英語のままにしつつ、**日本語**に翻訳して回答してください。「ですます調」ではなく「である調」にして回答してください。"
    )
    message = (
        f"タイトル: {title}\n"
        f"概要: {abstract}"
    )

    ret = oai_clinet.beta.chat.completions.parse(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message}
        ],
        response_format=Result,
    )
    resp = ret.choices[0].message.parsed

    return f"*タイトル* :{title}\n*概要* :{resp.overview}\n*課題* :{resp.problem}\n*貢献* :{resp.contribution}\n*結論* :{resp.conclusion}"


def handle_arxiv_request(text):
    match = re.search(arxiv_pattern, text)
    if match:
        arxiv_id = match.group(1)
        title, abstract = fetch_arxiv_info(arxiv_id)
        if title and abstract:
            return summarize(title, abstract)
        else:
            return "arXivから情報を取得できませんでした。"
    else:
        return (
            "フォーマットが正しくありません。\n"
            "`https://arxiv.org/abs/XXXX.XXXXX` という形式で送信してください。"
        )