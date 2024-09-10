import time
import json
import requests


server_url = 'http://gcrazcdl0024.westus2.cloudapp.azure.com'

exp_id = 'test-cz'
dataset_name = 'princeton-nlp/SWE-bench'
with open('./outputs/dummy_output.jsonl') as f:
    outputs = [json.loads(line) for line in f.readlines()]


def run_evaluation(exp_id: str, task_id: str, dataset_name: str, instance_id: str, model_patch: str):
    # Remove the task with the same name (better not use this feature, set unique task ids instead)
    requests.delete(f'{server_url}/experiments/{exp_id}/{task_id}')
    print('Removed')
    # Submit evaluation request
    post = requests.post(f'{server_url}/experiments/{exp_id}/{task_id}/request', data={
        'dataset_name': dataset_name,
        'instance_id': instance_id,
        'model_patch':model_patch,
    })
    assert post.status_code == 200
    print('Submitted')
    # Get evaluation results
    results = requests.get(f'{server_url}/experiments/{exp_id}/{task_id}/stdout')  # Can be stderr / patch / log / report
    while results.status_code == 404:
        time.sleep(1)
        results = requests.get(f'{server_url}/experiments/{exp_id}/{task_id}/stdout')
    print('Finished')
    return results.text


for i, output in enumerate(outputs):
    task_id = f'tmp-task-{i:0>3}'
    instance_id = output['instance_id']
    model_patch = output['model_patch']
    print(f'==================== {task_id} | {instance_id} ====================')
    print(run_evaluation(exp_id, task_id, dataset_name, instance_id, model_patch))
