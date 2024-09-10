import os
import json
import shutil
import logging

from flask import Flask, Response, request


app = Flask(__name__)
app.logger.setLevel(logging.INFO)


work_dir = os.path.join(os.path.dirname(__file__), 'uploads')
os.makedirs(work_dir, exist_ok=True)
task_contents = {
    'request': 'request.json',
    'patch': 'patch.diff',
    'stdout': 'stdout',
    'stderr': 'stderr',
    'log': 'run_instance.log',
    'report': 'report.json',
}


class Experiment(object):

    def __init__(self, exp_id: str):
        super().__init__()
        self.id = exp_id
        self.tasks: dict[str, Task] = {}
        self.num_waiting = 0
        self.num_running = 0
        self.num_finished = 0
        app.logger.info(f'Experiment created: {self.id}')

    def status(self):
        return f'WAITING: {self.num_waiting} | RUNNING: {self.num_running} | FINISHED: {self.num_finished}'


class Task(object):

    def __init__(self, exp: Experiment, task_id: str):
        super().__init__()
        self.exp = exp
        self.id = task_id
        self.path = os.path.join(work_dir, exp.id, task_id)
        os.makedirs(self.path, exist_ok=True)
        self.dataset_name = ''
        self.instance_id = ''
        self.evaluator = ''
        self.waiting = False
        self.running = False
        self.finished = False
        app.logger.info(f'Task created: {self.exp.id}/{self.id}')

    def set_request(self, dataset: str, inst_id: str, patch: str):
        waitlist[self.id] = self
        self.waiting = True
        self.exp.num_waiting += 1
        self.dataset_name = dataset
        self.instance_id = inst_id
        with open(os.path.join(self.path, 'request.json'), 'w') as f:
            f.write(json.dumps({
                'experiment_id': f'{self.exp.id}/{self.id}',
                'dataset_name': dataset,
                'instance_id': inst_id,
                'model_patch': patch,
            }, indent='\t'))

    def run(self, evaluator: str):
        del waitlist[self.id]
        self.waiting = False
        self.exp.num_waiting -= 1
        self.running = True
        self.exp.num_running += 1
        self.evaluator = evaluator
        app.logger.info(f'Task running: {self.exp.id}/{self.id}')

    def finish(self, patch: str, stdout: str, stderr: str, log: str, report: str):
        with open(os.path.join(self.path, 'patch.diff'), 'w') as f:
            f.write(patch)
        with open(os.path.join(self.path, 'stdout'), 'w') as f:
            f.write(stdout)
        with open(os.path.join(self.path, 'stderr'), 'w') as f:
            f.write(stderr)
        with open(os.path.join(self.path, 'run_instance.log'), 'w') as f:
            f.write(log)
        with open(os.path.join(self.path, 'report.json'), 'w') as f:
            f.write(report)
        self.running = False
        self.exp.num_running -= 1
        self.finished = True
        self.exp.num_finished += 1
        app.logger.info(f'Task finished: {self.exp.id}/{self.id}')

    def get_content(self, content: str):
        with open(os.path.join(self.path, task_contents[content])) as f:
            data = f.read()
        return data

    def remove(self):
        shutil.rmtree(self.path)


experiments: dict[str, Experiment] = {}
for exp_id in os.listdir(work_dir):
    exp = Experiment(exp_id)
    for task_id in os.listdir(os.path.join(work_dir, exp_id)):
        if all([
            os.path.exists(os.path.join(work_dir, exp_id, task_id, content))
            for content in task_contents.values()
        ]):
            task = Task(exp, task_id)
            request_info = json.loads(task.get_content('request'))
            task.dataset_name = request_info['dataset_name']
            task.instance_id = request_info['instance_id']
            task.finished = True
            exp.tasks[task_id] = task
            exp.num_finished += 1
    experiments[exp_id] = exp
waitlist: dict[str, Task] = {}


@app.get('/')
def home_page():
    buf = '<h1>SWE-Bench Server</h1>'
    buf += '<section>'
    buf += '<h3><a href="/waitlist">Waitlist</a></h3>'
    buf += '</section>'
    buf += '<section>'
    buf += '<h3>Experiments</h3>'
    for exp_id, exp in experiments.items():
        buf += f'<p><a href="/experiments/{exp_id}">{exp_id}</a> | {exp.status()}</p>'
    buf += '</section>'
    return buf


@app.get('/waitlist')
def task_waitlist():
    return Response(json.dumps([{
        'exp_id': task.exp.id,
        'task_id': task.id,
        'instance_id': task.instance_id,
    } for task in waitlist.values()], indent=4), mimetype='text/plain')


@app.get('/experiments/<exp_id>')
def exp_page(exp_id: str):
    if exp_id not in experiments:
        return f'<p>Experiment not found: "{exp_id}"</p>', 404
    exp = experiments[exp_id]
    buf = f'<h1>{exp.id}</h1><p>{exp.status()}</p>'
    for section in ['waiting', 'running', 'finished']:
        buf += '<section>'
        buf += f'<h3>{section.upper()}</h3>'
        for task_id, task in exp.tasks.items():
            if getattr(task, section):
                buf += f'<p><a href="/experiments/{exp_id}/{task_id}">{task_id}</a></p>'
        buf += '</section>'
    return buf


@app.get('/experiments/<exp_id>/<task_id>')
def task_page(exp_id: str, task_id: str):
    if exp_id not in experiments:
        return f'<p>Experiment not found: "{exp_id}"</p>', 404
    exp = experiments[exp_id]
    if task_id not in exp.tasks:
        return f'<p>Task not found: "{exp_id}/{task_id}"</p>', 404
    task = exp.tasks[task_id]
    buf = f'<h1>{task.id}</h1>'
    buf += f'<p>Dataset: {task.dataset_name}</p>'
    buf += f'<p>Instance: {task.instance_id}</p>'
    if task.waiting:
        buf += '<p><b>WAITING</b></p>'
    elif task.running:
        buf += '<p><b>RUNNING</b></p>'
        buf += f'<p>Evaluator: {task.evaluator}</p>'
    elif task.finished:
        buf += '<p><b>FINISHED</b></p>'
        buf += f'<p>Evaluator: {task.evaluator}</p>'
        buf += f'<p><a href="/experiments/{exp_id}/{task_id}/patch">patch.diff</a></p>'
        buf += f'<p><a href="/experiments/{exp_id}/{task_id}/stdout">stdout</a></p>'
        buf += f'<p><a href="/experiments/{exp_id}/{task_id}/stderr">stderr</a></p>'
        buf += f'<p><a href="/experiments/{exp_id}/{task_id}/log">run_instance.log</a></p>'
        buf += f'<p><a href="/experiments/{exp_id}/{task_id}/report">report.json</a></p>'
    else:
        buf += '<p><b>UNKNOWN STATUS</b></p>'
    return buf


@app.delete('/experiments/<exp_id>/<task_id>')
def task_delete(exp_id: str, task_id: str):
    if exp_id not in experiments:
        return f'<p>Experiment not found: "{exp_id}"</p>', 404
    exp = experiments[exp_id]
    if task_id not in exp.tasks:
        return f'<p>Task not found: "{exp_id}/{task_id}"</p>', 404
    exp.tasks[task_id].remove()
    del exp.tasks[task_id]
    if task_id in waitlist:
        del waitlist[task_id]
    return f'<p>Task removed: {exp_id}/{task_id}'


@app.post('/experiments/<exp_id>/<task_id>/request')
def task_request(exp_id: str, task_id: str):
    if exp_id in experiments:
        exp = experiments[exp_id]
    else:
        exp = Experiment(exp_id)
        experiments[exp_id] = exp
    if task_id in exp.tasks:  # and not request.form.get('exists_ok', False):
        return f'<p>Task already exists: "{exp_id}/{task_id}"</p>', 400
    task = Task(exp, task_id)
    task.set_request(request.form['dataset_name'], request.form['instance_id'], request.form['model_patch'])
    exp.tasks[task_id] = task
    return f'<p>Task created: <a href="/experiments/{exp_id}/{task_id}">{task_id}</a></p>'


@app.post('/experiments/<exp_id>/<task_id>/run')
def task_run(exp_id: str, task_id: str):
    if exp_id not in experiments:
        return f'<p>Experiment not found: "{exp_id}"</p>', 404
    exp = experiments[exp_id]
    if task_id not in exp.tasks:
        return f'<p>Task not found: "{exp_id}/{task_id}"</p>', 404
    task = exp.tasks[task_id]
    if task.waiting:
        evaluator = request.form['evaluator']
        task.run(evaluator)
        return f'<p>Task running: <a href="/experiments/{exp_id}/{task_id}">{task_id}</a></p>'
    else:
        return f'<p>Task not waiting: "{exp_id}/{task_id}"</p>', 400


@app.post('/experiments/<exp_id>/<task_id>/result')
def task_result(exp_id: str, task_id: str):
    if exp_id not in experiments:
        return f'<p>Experiment not found: "{exp_id}"</p>', 404
    exp = experiments[exp_id]
    if task_id not in exp.tasks:
        return f'<p>Task not found: "{exp_id}/{task_id}"</p>', 404
    task = exp.tasks[task_id]
    if task.running:
        patch = request.form['patch']
        stdout = request.form['stdout']
        stderr = request.form['stderr']
        log = request.form['log']
        report = request.form['report']
        task.finish(patch, stdout, stderr, log, report)
        return f'<p>Task finished: <a href="/experiments/{exp_id}/{task_id}">{task_id}</a></p>'
    else:
        return f'<p>Task not running: "{exp_id}/{task_id}"</p>', 400


@app.get('/experiments/<exp_id>/<task_id>/<content>')
def task_content(exp_id: str, task_id: str, content: str):
    if exp_id not in experiments:
        return f'<p>Experiment not found: "{exp_id}"</p>', 404
    exp = experiments[exp_id]
    if task_id not in exp.tasks:
        return f'<p>Task not found: "{exp_id}/{task_id}"</p>', 404
    task = exp.tasks[task_id]
    if content not in task_contents:
        return f'<p>Content not found: "{exp_id}/{task_id}/{content}"</p>', 404
    try:
        return Response(task.get_content(content), mimetype='text/plain')
    except FileNotFoundError as e:
        return f'<p>Content not found: "{exp_id}/{task_id}/{content}"</p>', 404
