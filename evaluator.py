import os
import time
import json
import socket
import logging
import argparse
import requests
import subprocess


logger = logging.getLogger(__file__)


def run_evaluate(
    server_url: str,
    work_dir: str,
    run_id: str,
    evaluator_id: str,
    task_id: str,
    dataset_name: str,
    instance_id: str,
    model_patch: str,
):
    instance_path = os.path.join(work_dir, task_id.replace("/", "__"), instance_id.replace("/", "__"))
    os.makedirs(instance_path, exist_ok=True)
    predictions_path = os.path.join(instance_path, 'predictions.jsonl')
    with open(predictions_path, 'w') as f:
        f.write(json.dumps({
            "dataset_name": dataset_name,
            "instance_id": instance_id,
            "model_patch": model_patch.replace('<patch>', '').strip(),
            "model_name_or_path": task_id,
        }))
    proc = subprocess.Popen([
        'python', '-m', 'swebench.harness.run_evaluation',
        '--dataset_name', dataset_name,
        '--predictions_path', predictions_path,
        '--max_workers', '1',
        '--instance_ids', instance_id,
        '--cache_level', 'instance',
        '--run_id', run_id,
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    post = requests.post(f'{server_url}/experiments/{task_id}/run', data={
        'evaluator': evaluator_id,
    })
    assert post.status_code == 200
    logger.info(f'[Submitted] task_id: {task_id} | instance_id: {instance_id}')
    return proc, instance_path


def read_file(instance_path: str, file_name: str):
    file_path = os.path.join(instance_path, file_name)
    if os.path.exists(file_path):
        with open(file_path) as f:
            content = f.read()
    else:
        content = ''
    return content


def upload_result(
    server_url: str,
    task_id: str,
    proc: subprocess.Popen,
    instance_path: str,
):
    stdout, stderr = proc.communicate()
    post = requests.post(f'{server_url}/experiments/{task_id}/result', data={
        'patch': read_file(instance_path, 'patch.diff'),
        'stdout': stdout.decode(),
        'stderr': stderr.decode(),
        'log': read_file(instance_path, 'run_instance.log'),
        'report': read_file(instance_path, 'report.json'),
    })
    assert post.status_code == 200
    logger.info(f'[Finished] task_id: {task_id}')


def main(args):
    server_url = args.server
    max_procs = args.num_proc
    scope = [''] if args.scope is None else args.scope.split(',')
    evaluator_id = args.evaluator_id
    run_id = args.run_id
    work_dir = os.path.join(os.path.dirname(__file__), 'logs', 'run_evaluation', run_id)
    os.makedirs(work_dir, exist_ok=True)

    proc_dict: dict[str, tuple[subprocess.Popen, str]] = {}
    while True:
        # Upload results
        finished_tasks = []
        for task_id, (proc, instance_path) in proc_dict.items():
            if proc.poll() is not None:
                upload_result(server_url, task_id, proc, instance_path)
                finished_tasks.append(task_id)
        for task_id in finished_tasks:
            del proc_dict[task_id]
        # Get newest waitlist
        waitlist = json.loads(requests.get(f'{server_url}/waitlist').text)
        # Submit evaluation
        for task_info in waitlist:
            exp_id: str = task_info['exp_id']
            task_id: str = task_info['task_id']
            task_id = f'{exp_id}/{task_id}'
            instance_id: str = task_info['instance_id']
            if any([instance_id.startswith(repo_name) for repo_name in scope]) and len(proc_dict) < max_procs:
                request_info = json.loads(requests.get(f'{server_url}/experiments/{task_id}/request').text)
                dataset_name = request_info['dataset_name']
                model_patch = request_info['model_patch']
                if task_id not in proc_dict:
                    proc_dict[task_id] = run_evaluate(
                        server_url=server_url,
                        work_dir=work_dir,
                        run_id=run_id,
                        evaluator_id=evaluator_id,
                        task_id=task_id,
                        dataset_name=dataset_name,
                        instance_id=instance_id,
                        model_patch=model_patch,
                    )
        # Wait and loop
        time.sleep(1)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] %(message)s',
        datefmt='%m-%d %H:%M:%S',
    )

    parser = argparse.ArgumentParser()
    parser.add_argument("--server", type=str, required=True)
    parser.add_argument("--scope", type=str, default=None)
    parser.add_argument("--num-proc", type=int, default=16)
    parser.add_argument("--run-id", type=str, default='validate-server')
    parser.add_argument("--evaluator-id", type=str, default=socket.gethostname())
    main(parser.parse_args())
