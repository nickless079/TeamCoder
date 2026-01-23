from typing import Dict, List, Any, Optional
from ..BaseAgent import BaseAgent

class ArbiterAgent(BaseAgent):
    """
    仲裁者Agent，负责：
    1. 建立绝对的'真理规则'（Oracle函数）
    2. 审查候选测试用例
    3. 生成最终的黄金测试套件
    """

    def __init__(self, model, verbose: int = 0):
        super().__init__(model, verbose, True, "ArbiterAgent")

    def arbitrate_fatal_point(
        self,
        problem_description: str,
        sample_io: List[str],
        initial_attention_analysis: str,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        仲裁致命点分析，生成最终的Fatal Point Analysis
        
        Args:
            problem_description: 问题描述
            sample_io: 样例输入输出
            initial_attention_analysis: AttentionAgent的初始分析
            session_id: 会话ID，用于保持上下文
            
        Returns:
            仲裁结果字典，包含：
            - arbitration_thought: 仲裁思考过程
            - reasoning: 最终分析推理
            - final_fatal_point_json: 最终JSON格式的致命点分析
        """
        if self.verbose >= 1:
            print(f"\n🏛️ {self.agent_name}: 开始仲裁致命点分析...")

        # 构建提示词
        messages = self.prompt_module.get_messages(
            task_type="arbitrate_fatal_point",
            problem_description=problem_description,
            sample_io=sample_io,
            initial_attention_analysis=initial_attention_analysis
        )

        # 调用模型
        response = self._call_model(messages, session_id)

        if self.verbose >= 2:
            print(f"原始响应: {response}")

        # 解析响应
        result = self._process_fatal_point_response(response)
        
        if self.verbose >= 1:
            print(f"✅ 致命点仲裁完成")

        return result

    def arbitrate_test_cases(
        self,
        problem_description: str,
        sample_io: List[str],
        attention_analysis: str,
        candidate_testcases: List[Dict],
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        仲裁测试用例，生成最终正确的测试套件
        
        Args:
            problem_description: 问题描述
            sample_io: 样例输入输出
            attention_analysis: 注意力分析结果
            candidate_testcases: 候选测试用例列表
            session_id: 会话ID，用于保持上下文
            
        Returns:
            仲裁结果字典，包含：
            - corrected_tests: 最终测试用例列表
            - final_theory: 最终理论规则
            - arbitration_thought: 仲裁思考过程
        """
        if self.verbose >= 1:
            print(f"\n🏛️ {self.agent_name}: 开始仲裁测试用例...")

        # 构建提示词
        messages = self.prompt_module.get_messages(
            task_type="arbitrate_tests",
            problem_description=problem_description,
            sample_io=sample_io,
            attention_analysis=attention_analysis,
            candidate_testcases=candidate_testcases
        )

        # 调用模型
        response = self._call_model(messages, session_id)

        if self.verbose >= 2:
            print(f"原始响应: {response}")

        # 解析响应
        result = self._process_response(response)
        
        if self.verbose >= 1:
            corrected_count = len(result.get('corrected_tests', []))
            print(f"✅ 仲裁完成，生成 {corrected_count} 个最终测试用例")

        return result

    def _process_response(self, response: str) -> Dict[str, Any]:
        """
        解析仲裁响应
        
        Args:
            response: 模型响应
            
        Returns:
            解析后的结果字典
        """
        result = {
            'arbitration_thought': '',
            'final_theory': '',
            'corrected_tests': []
        }

        # 提取仲裁思考过程
        arbitration_match = re.search(r'<ARBITRATION_THOUGHT>(.*?)</ARBITRATION_THOUGHT>', response, re.DOTALL)
        if arbitration_match:
            result['arbitration_thought'] = arbitration_match.group(1).strip()

        # 提取最终理论
        theory_match = re.search(r'<FINAL_THEORY>(.*?)</FINAL_THEORY>', response, re.DOTALL)
        if theory_match:
            result['final_theory'] = theory_match.group(1).strip()

        # 提取最终测试用例
        tests_match = re.search(r'<CORRECTED_TESTS>(.*?)</CORRECTED_TESTS>', response, re.DOTALL)
        if tests_match:
            tests_content = tests_match.group(1).strip()
            
            # 尝试解析JSON格式
            try:
                if tests_content.startswith('[') and tests_content.endswith(']'):
                    result['corrected_tests'] = json.loads(tests_content)
                else:
                    # 如果不是JSON格式，解析assertion格式
                    result['corrected_tests'] = self._parse_assertion_format(tests_content)
            except json.JSONDecodeError:
                # JSON解析失败，尝试解析assertion格式
                result['corrected_tests'] = self._parse_assertion_format(tests_content)

        return result

    def _process_fatal_point_response(self, response: str) -> Dict[str, Any]:
        """
        解析致命点仲裁响应
        
        Args:
            response: 模型响应
            
        Returns:
            解析后的结果字典
        """
        result = {
            'arbitration_thought': '',
            'final_fatal_point_json': {},
            'raw_response': response
        }

        # 提取仲裁思考过程
        arbitration_match = re.search(r'<ARBITRATION_THOUGHT>(.*?)</ARBITRATION_THOUGHT>', response, re.DOTALL)
        if arbitration_match:
            result['arbitration_thought'] = arbitration_match.group(1).strip()

        # 提取最终JSON
        json_match = re.search(r'<FINAL_FATAL_POINT_JSON>(.*?)</FINAL_FATAL_POINT_JSON>', response, re.DOTALL)
        if json_match:
            json_content = json_match.group(1).strip()
            
            # 尝试解析JSON
            try:
                # 提取```json代码块中的内容
                code_block_match = re.search(r'```json\s*(.*?)\s*```', json_content, re.DOTALL)
                if code_block_match:
                    json_str = code_block_match.group(1).strip()
                else:
                    json_str = json_content
                
                result['final_fatal_point_json'] = json.loads(json_str)
            except json.JSONDecodeError as e:
                if self.verbose >= 1:
                    print(f"警告：JSON解析失败: {e}")
                result['final_fatal_point_json'] = {}

        return result

    def _parse_assertion_format(self, content: str) -> List[Dict]:
        """
        解析assertion格式的测试用例
        
        Args:
            content: assertion格式的内容
            
        Returns:
            测试用例列表
        """
        tests = []
        
        # 匹配assert语句
        assert_pattern = r'assert\s+([^=]+)==([^=]+)'
        matches = re.findall(assert_pattern, content)
        
        for match in matches:
            test_call = match[0].strip()
            expected = match[1].strip()
            
            # 构建测试用例字典
            test_dict = {
                "assertion": f"assert {test_call} == {expected}",
                "description": f"Test case for {test_call}"
            }
            tests.append(test_dict)
        
        return tests 