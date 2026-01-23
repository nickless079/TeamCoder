import dotenv
dotenv.load_dotenv()

import argparse
import sys
import os
from datetime import datetime

# 导入常量和配置
from constants.paths import *
from constants.verboseType import *

# 导入工厂类
from models.ModelFactory import ModelFactory
from datasets.DatasetFactory import DatasetFactory
from workflow.WorkflowFactory import WorkflowFactory

# 导入结果处理
from utils.results import Results

# 导入策略配置和 Prompt 加载器
from strategies.config import get_strategy_config, list_strategies
from strategies.prompt_loader import prompt_loader

# 命令行参数解析
parser = argparse.ArgumentParser(description="TeamCoder: CTO监督下的多智能体协作代码生成框架")

parser.add_argument(
    "--dataset",
    type=str,
    default="HumanEval",
    choices=[
        "HumanEval",
        "MBPP",
        "APPS",
        "xCodeEval",
    ],
    help="选择要使用的数据集"
)

parser.add_argument(
    "--language",
    type=str,
    default="Python3",
    choices=[
        "C",
        "C#",
        "C++",
        "Go",
        "PHP",
        "Python3",
        "Ruby",
        "Rust",
    ],
    help="选择编程语言"
)

parser.add_argument(
    "--model_provider",
    type=str,
    default="Ollama",
    choices=[
        "OpenAI",
        "Anthropic",
        "Gemini",
        "Groq",
        "Ollama",
        "Alibaba",  # 添加阿里云百炼平台选项
    ],
    help="选择模型提供商"
)

parser.add_argument(
    "--model",
    type=str,
    default="qwen3:4b",
    help="选择具体的模型"
)

parser.add_argument(
    "--temperature",
    type=float,
    default=0,
    help="模型温度参数"
)

parser.add_argument(
    "--top_p",
    type=float,
    default=0.95,
    help="模型top_p参数"
)

parser.add_argument(
    "--pass_at_k",
    type=int,
    default=1,
    help="评估时的pass@k值"
)

parser.add_argument(
    "--verbose",
    type=str,
    default="2",
    choices=["0", "1", "2"],
    help="输出详细程度: 0=最少, 1=中等, 2=全部"
)

parser.add_argument(
    "--store_log_in_file",
    type=str,
    default="yes",
    choices=["yes", "no"],
    help="是否将日志存储到文件中"
)

parser.add_argument(
    "--web_search",
    type=str,
    default="yes",
    choices=["yes", "no"],
    help="是否启用网络搜索"
)

parser.add_argument(
    "--docker_execution",
    type=str,
    default="yes",
    choices=["yes", "no"],
    help="是否使用Docker执行验证"
)

parser.add_argument(
    "--api_base",
    type=str,
    default="http://localhost:11434",
    help="API基础URL（用于Ollama等本地模型）"
)

parser.add_argument(
    "--api_key",
    type=str,
    default="",
    help="API密钥（用于OpenAI、阿里云百炼等需要认证的API）"
)

parser.add_argument(
    "--start_index",
    type=int,
    default=0,
    help="从数据集的第几个问题开始处理（从0开始计数）"
)

parser.add_argument(
    "--strategy",
    type=str,
    default="teamcoder",
    choices=list_strategies(),
    help="选择要使用的策略"
)

args = parser.parse_args()

# 解析参数
DATASET = args.dataset
LANGUAGE = args.language
MODEL_PROVIDER_NAME = args.model_provider
MODEL_NAME = args.model
TEMPERATURE = args.temperature
TOP_P = args.top_p
PASS_AT_K = args.pass_at_k
VERBOSE = int(args.verbose)
STORE_LOG_IN_FILE = args.store_log_in_file.lower() == "yes"
WEB_SEARCH = args.web_search.lower() == "yes"
DOCKER_EXECUTION = args.docker_execution.lower() == "yes"
API_BASE = args.api_base
API_KEY = args.api_key
START_INDEX = args.start_index
STRATEGY = args.strategy

# 根据策略获取配置
strategy_config = get_strategy_config(STRATEGY)
WORKFLOW_TYPE = strategy_config["workflow_type"]
PROMPTS_PACKAGE = strategy_config["prompts_package"]

# 初始化 Prompt 加载器
prompt_loader.initialize(STRATEGY, PROMPTS_PACKAGE)

# 设置运行名称和目录
RUN_NAME = f"results/{STRATEGY}/{DATASET}/{MODEL_NAME}/{LANGUAGE}-{TEMPERATURE}-{TOP_P}-{PASS_AT_K}"

run_no = 1
while os.path.exists(f"{RUN_NAME}/Run-{run_no}"):
    run_no += 1

RUN_NAME = f"{RUN_NAME}/Run-{run_no}"

if not os.path.exists(RUN_NAME):
    os.makedirs(RUN_NAME)

RESULTS_PATH = f"{RUN_NAME}/Results.jsonl"
SUMMARY_PATH = f"{RUN_NAME}/Summary.txt"
LOGS_PATH = f"{RUN_NAME}/Log.txt"

# 设置日志输出
if STORE_LOG_IN_FILE:
    sys.stdout = open(
        LOGS_PATH,
        mode="a",
        encoding="utf-8",
        buffering=1  # 行缓冲，确保每行输出后立即写入文件
    )

if VERBOSE >= VERBOSE_MINIMAL:
    print(f"""
##################################################
TeamCoder实验开始 {RUN_NAME}, 时间: {datetime.now()}
策略: {STRATEGY} ({strategy_config['description']})
Workflow: {WORKFLOW_TYPE}
Prompts: {PROMPTS_PACKAGE}
##################################################
""")

# 初始化模型
model_class = ModelFactory.get_model_class(MODEL_PROVIDER_NAME)
if MODEL_PROVIDER_NAME.lower() == "ollama":
    model = model_class(
        model_name=MODEL_NAME, 
        temperature=TEMPERATURE, 
        top_p=TOP_P,
        api_base=API_BASE
    )
elif MODEL_PROVIDER_NAME.lower() in ["alibaba", "aliyun", "bailian"]:
    model = model_class(
        model_name=MODEL_NAME, 
        temperature=TEMPERATURE, 
        top_p=TOP_P,
        api_base=API_BASE,
        api_key=API_KEY
    )
else:
    model = model_class(
        model_name=MODEL_NAME, 
        temperature=TEMPERATURE, 
        top_p=TOP_P,
        api_key=API_KEY if API_KEY else None
    )

# 初始化数据集
dataset = DatasetFactory.get_dataset_class(DATASET)()

# 初始化结果记录器
results = Results(RESULTS_PATH)

# 初始化工作流
workflow = WorkflowFactory.get_workflow(
    model=model,
    dataset=dataset,
    language=LANGUAGE,
    pass_at_k=PASS_AT_K,
    results=results,
    verbose=VERBOSE,
    web_search=WEB_SEARCH,
    docker_execution=DOCKER_EXECUTION,
    workflow_type=WORKFLOW_TYPE,
    start_index=START_INDEX
)

# 运行工作流
workflow.run()

if VERBOSE >= VERBOSE_MINIMAL:
    print(f"""
##################################################
TeamCoder实验结束 {RUN_NAME}, 时间: {datetime.now()}
##################################################
""")

# 生成摘要
from utils.summary import gen_summary
gen_summary(RESULTS_PATH, SUMMARY_PATH)
print('over\nover\n')
# 关闭日志文件
if STORE_LOG_IN_FILE:
    sys.stdout.close() 