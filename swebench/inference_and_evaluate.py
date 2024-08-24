import logging

import vllm
import docker

from .inference.run_llama import load_data, load_model, load_tokenizer, extract_diff
from .harness.run_evaluation import build_env_images, run_instance, make_test_spec, should_remove, list_images


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


client = docker.from_env()

model_name_or_path = '/mnt/cz/models/Phi-3-mini-128k-instruct'
dataset_path = 'princeton-nlp/SWE-bench_oracle'
instance_id = 42

tokenizer = load_tokenizer(model_name_or_path)

dataset = load_data(
    dataset_path,
    split='test',
    tokenizer=tokenizer,
    min_len=None,
    max_len=None,
    model_name_or_path=model_name_or_path,
    peft_path=None,
    existing_ids=set(),
    shard_id=None,
    num_shards=None,
)

sampling_params = vllm.SamplingParams(
    max_tokens=200,
    temperature=0,
    top_p=1.0,
)
instance = dataset[instance_id]

model = load_model(model_name_or_path)


prompt = instance["text"]
output = model.generate(
    prompts=[prompt],
    sampling_params=sampling_params,
)[0].outputs[0].text
logger.info(output[:200])
diff = extract_diff(output)
res = {
    "instance_id": instance["instance_id"],
    "full_output": output,
    "model_patch": diff,
    "model_name_or_path": model_name_or_path,
}

build_env_images(client, dataset[instance_id:instance_id + 1], force_rebuild=False, max_workers=4)
test_spec = make_test_spec(instance)
run_instance(
    test_spec=test_spec,
    pred=res,
    rm_image=should_remove(
        test_spec.instance_image_key,
        cache_level='env',
        clean=True,
        existing_images=list_images(client),
    ),
    force_rebuild=False,
    client=client,
    run_id='test1',
    timeout=1800,
)
