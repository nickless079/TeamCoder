import os

# 基础路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC_DIR = os.path.join(BASE_DIR, "src")
DATA_DIR = os.path.join(BASE_DIR, "data")
RESULTS_DIR = os.path.join(BASE_DIR, "results")

# 数据集路径
HUMAN_DATA_PATH = os.path.join(DATA_DIR, "HumanEval", "HumanEval.jsonl")
HUMAN_ET_DATA_PATH = os.path.join(DATA_DIR, "HumanEval", "HumanEvalET.jsonl")
HUMAN_INCREASED_IO_DATA_PATH = os.path.join(DATA_DIR, "HumanEval", "HumanEvalIncreasedSampleIO.jsonl")

MBPP_DATA_PATH = os.path.join(DATA_DIR, "MBPPEval", "MBPP.jsonl")
MBPP_ET_DATA_PATH = os.path.join(DATA_DIR, "MBPPEval", "MBPP_ET.jsonl")
MBPP_PY_DATA_PATH = os.path.join(DATA_DIR, "MBPPEval", "mbpp-py.jsonl")

APPS_DATA_PATH = os.path.join(DATA_DIR, "APPS", "selected300.jsonl")

XCODE_PROB_DESC_PATH = os.path.join(DATA_DIR, "xCodeEval", "problem_descriptions.jsonl")
XCODE_PROG_SYN_PATH = os.path.join(DATA_DIR, "xCodeEval", "prog_syn_val.jsonl")
XCODE_UNITTEST_PATH = os.path.join(DATA_DIR, "xCodeEval", "unittest_db.json")

# 提示模板路径
PROMPT_TEMPLATES_DIR = os.path.join(SRC_DIR, "prompts")

# 创建必要的目录
for directory in [RESULTS_DIR]:
    if not os.path.exists(directory):
        os.makedirs(directory) 