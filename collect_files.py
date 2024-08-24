import os
import json
import time
import urllib.error
import urllib.request
import requests

import datasets
import transformers
from tqdm import tqdm


data = datasets.load_dataset('princeton-nlp/SWE-bench')
tokenizer = transformers.AutoTokenizer.from_pretrained('microsoft/Phi-3-mini-128k-instruct')
headers = {
    'X-GitHub-Api-Version': '2022-11-28',
    'Authorization': 'YOUR_GITHUB_API_KEY',
    # 'User-Agent': 'request',
}


def request(url: str) -> str:
    mod_url = urllib.request.Request(url.replace(" ", "%20"), headers=headers)
    try:
        content = urllib.request.urlopen(mod_url).read().decode(encoding='UTF-8', errors='ignore')
        time.sleep(1)
    except urllib.error.HTTPError as e:
        print('GitHub rate limit exceeded. Retry after 5 seconds.')
        time.sleep(5)
        content = request(url)
    return content


def api(url: str) -> dict:
    return json.loads(request(url))


output_dir = os.path.join(os.path.split(__file__)[0], 'results')

split = 'train'
for split in ['train', 'test', 'dev']:
    split_dir = os.path.join(output_dir, split)
    os.makedirs(split_dir, exist_ok=True)
    instance_id = 0
    for row in tqdm(data[split], desc=split):
        repo_path = row['repo']  # 'DataDog/integrations-core'
        instance_id = row['instance_id']
        pull_id = instance_id.split('-')[-1]  # '10093'
        base_commit = row['base_commit']  # '160cfef6e1118061fa66d333e8c2a572f5d0a815'
        result_path = os.path.join(split_dir, f'{instance_id}.json')
        if os.path.exists(result_path):
            continue
        files = set()
        for commit in api(f'https://api.github.com/repos/{repo_path}/pulls/{pull_id}/commits'):
            commit_data = api(commit['url'])
            while 'files' not in commit_data:
                print('Incomplete API data. Retry after 5 seconds.')
                time.sleep(5)
                commit_data = api(commit['url'])
            for file in commit_data['files']:
                files.add(file['filename'])  # 'elastic/datadog_checks/elastic/elastic.py'
        data = []
        for file_path in files:
            try:
                content = request(f'https://raw.githubusercontent.com/{repo_path}/{base_commit}/{file_path}')
            except urllib.error.HTTPError as e:
                data.append({
                    'path': file_path,
                    'content': 'HTTPError',
                    'num_tokens': 0,
                })
                continue
            data.append({
                'path': file_path,
                'content': content,
                'num_tokens': len(tokenizer.encode(content)),
            })
        with open(result_path, 'w') as f:
            f.write(json.dumps(data, indent=4))
        # import ipdb; ipdb.set_trace()
