import anthropic
import os
import json
import argparse
from datetime import datetime
import re

parser = argparse.ArgumentParser()
parser.add_argument("--start", default=0, type=int)
parser.add_argument("--end", default=-1, type=int)
parser.add_argument("--version", default="claude-v1", type=str)
parser.add_argument("--answered", default=None, type=str)

args = parser.parse_args()
API_KEY = os.getenv('CLAUDE_KEY')

def run_prompt(full_prompt: str):
    c = anthropic.Client(API_KEY)
    response = c.completion_stream(
        prompt=f"{anthropic.HUMAN_PROMPT} Question: {full_prompt} \n Please think step by step, and then conclude the answer as `therefore, the answer is ...' {anthropic.AI_PROMPT}",
        stop_sequences=[anthropic.HUMAN_PROMPT],
        max_tokens_to_sample=1024,
        model=args.version,
        temperature=0.0,
        stream=False,
    )

    tmps = []
    for tmp in response:
        tmps.append(tmp)
    return tmps[0]

def run_bool_prompt(full_prompt: str):
    c = anthropic.Client(API_KEY)
    response = c.completion_stream(
        prompt=f"{anthropic.HUMAN_PROMPT} Question: {full_prompt} \n PPlease think step by step, and then conclude the answer as `therefore, the answer is True/False' {anthropic.AI_PROMPT}",
        stop_sequences=[anthropic.HUMAN_PROMPT],
        max_tokens_to_sample=1024,
        model=args.version,
        temperature=0.0,
        stream=False,
    )

    tmps = []
    for tmp in response:
        tmps.append(tmp)
    return tmps[0]

def run_option_prompt(full_prompt: str):
    c = anthropic.Client(API_KEY)
    response = c.completion_stream(
        prompt=f"{anthropic.HUMAN_PROMPT} Question: {full_prompt} \n Please think step by step, and then conclude the answer as `therefore, the answer is (a)/(b)/(c)/(d)'. {anthropic.AI_PROMPT}",
        stop_sequences=[anthropic.HUMAN_PROMPT],
        max_tokens_to_sample=1024,
        model=args.version,
        temperature=0.0,
        stream=False,
    )

    tmps = []
    for tmp in response:
        tmps.append(tmp)
    return tmps[0]


def main():
    now = datetime.now()
    dt_string = now.strftime("%m_%d_%H_%M")

    with open('theoremqa_test.json', 'r') as f:
        test_set = json.load(f)

    answered_set = dict()
    if args.answered:
        with open(args.answered, 'r') as f:
            for line in f:
                answered_set[json.loads(line)['id']] = line.strip('\n')
    print('answered set:', len(answered_set))

    if args.end == -1:
        test_set = test_set[args.start:]
    else:
        test_set = test_set[args.start : args.end]

    filename = f'outputs/{args.version}_s{args.start}_e{args.end}_{dt_string}.jsonl'
    writer = open(filename, 'w')
    for example in test_set:

        if answered_set and example['id'] in answered_set:
            writer.write(answered_set[example['id']] + '\n')
            continue

        if example['Answer_type'] == 'bool':
            answer = run_bool_prompt(example['Question'])
        elif example['Answer_type'] == 'option':
            answer = run_option_prompt(example['Question'])
        else:
            answer = run_prompt(example['Question'])
        result = answer['completion']

        prediction = None
        for sent in result.split('\n')[::-1]:
            if example['Answer_type'] == 'bool':
                if 'true' in sent.lower() or 'correct' in sent.lower():
                    prediction = 'True'
                    break
                if 'false' in sent.lower() or 'wrong' in sent.lower():
                    prediction = 'False'
                    break
            elif example['Answer_type'] == 'option':
                if '(a)' in sent.lower() or '(b)' in sent.lower() or '(c)' in sent.lower() or '(d)' in sent.lower():
                    prediction = sent
                    break
            else:
                if ' is ' in sent.lower() or ' be ' in sent.lower() or ' are ' in sent.lower() or ' is: ' in sent.lower():
                    prediction = re.split(' be | is | are | is: ', sent)[-1].strip('.')
                    break
                elif re.search('[0-9]', sent):
                    prediction = sent
                    break
                else:
                    continue

        if prediction is None:
            print(result)

        tmp = {
            'id': example['id'],
            'question': example['Question'],
            'answer': example['Answer'],
            'rationale': result,
            'prediction': prediction,
            'answer_type': example['Answer_type'],
            }

        writer.write(json.dumps(tmp) + '\n')

    writer.close()
    print()


if __name__ == "__main__":
    main()
