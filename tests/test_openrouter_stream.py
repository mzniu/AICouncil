import json
import unittest
from unittest.mock import MagicMock, patch
from src.agents.langchain_llm import AdapterLLM, ModelConfig

class TestOpenRouterStream(unittest.TestCase):
    def setUp(self):
        # 配置为 openrouter 类型
        self.llm = AdapterLLM(backend_config=ModelConfig(type="openrouter", model="test-model"))

    @patch("src.agents.model_adapter.call_model")
    def test_openrouter_stream_deduplication(self, mock_call_model):
        """测试 OpenRouter 流式输出中的去重逻辑（防止汇总包导致双份内容）"""
        # 模拟 OpenRouter 的流式响应行，包含增量 delta 和最后的汇总 response
        lines = [
            b'data: {"type":"response.created","response":{"output_text":""}}',
            b'data: {"type":"response.output_text.delta","delta":"Hello"}',
            b'data: {"type":"response.output_text.delta","delta":" world"}',
            # 模拟最后发送的完整汇总包，此时 has_yielded_incremental 应为 True，该包应被忽略
            b'data: {"type":"response.done","response":{"output_text":"Hello world"}}',
            b'data: [DONE]'
        ]

        mock_response = MagicMock()
        mock_response.iter_lines.return_value = lines
        mock_response.status_code = 200
        mock_call_model.return_value = mock_response

        chunks = list(self.llm._stream("test prompt"))
        
        # 提取所有文本块
        texts = [chunk.text for chunk in chunks if chunk.text]
        full_text = "".join(texts)
        
        # 验证内容是否正确（不应重复）
        self.assertEqual(full_text, "Hello world")
        # 验证是否只有两个增量块被产生
        self.assertEqual(len(texts), 2)

    @patch("src.agents.model_adapter.call_model")
    def test_openrouter_reasoning_and_content(self, mock_call_model):
        """测试 OpenRouter 同时包含推理和正文的流式输出"""
        lines = [
            # 推理部分
            b'data: {"type":"response.reasoning_text.delta","delta":"Thinking hard..."}',
            # 正文部分
            b'data: {"type":"response.output_text.delta","delta":"The answer is 42"}',
            # 汇总包（应被忽略）
            b'data: {"output":[{"type":"message","content":[{"type":"output_text","text":"The answer is 42"}]}]}',
            b'data: [DONE]'
        ]

        mock_response = MagicMock()
        mock_response.iter_lines.return_value = lines
        mock_response.status_code = 200
        mock_call_model.return_value = mock_response

        chunks = list(self.llm._stream("test prompt"))
        
        reasoning_chunks = [c.generation_info.get("reasoning") for c in chunks if c.generation_info and "reasoning" in c.generation_info]
        content_chunks = [c.text for c in chunks if c.text]
        
        self.assertEqual("".join(reasoning_chunks), "Thinking hard...")
        self.assertEqual("".join(content_chunks), "The answer is 42")

    @patch("src.agents.model_adapter.call_model")
    def test_openrouter_fallback_json(self, mock_call_model):
        """测试非 SSE 格式（直接 JSON 块）的解析"""
        # 模拟某些情况下直接返回 JSON 字符串而不是 data: 前缀的情况
        lines = [
            b'{"output": "Direct JSON output"}',
        ]

        mock_response = MagicMock()
        mock_response.iter_lines.return_value = lines
        mock_response.status_code = 200
        mock_call_model.return_value = mock_response

        chunks = list(self.llm._stream("test prompt"))
        texts = [chunk.text for chunk in chunks if chunk.text]
        
        self.assertEqual("".join(texts), "Direct JSON output")

    @patch("src.agents.model_adapter.call_model")
    def test_openrouter_user_log_format(self, mock_call_model):
        """测试用户提供的实际日志格式"""
        lines = [
            b'data: {"type":"response.created","response":{"output_text":"","output":[]}}',
            b'data: {"type":"response.in_progress","response":{"output_text":"","output":[]}}',
            b'data: {"type":"response.output_item.added","item":{"type":"reasoning","summary":[]}}',
            b'data: {"type":"response.reasoning_text.delta","delta":"Reviewing..."}',
            b'data: {"type":"response.output_text.delta","delta":"Final Answer"}',
            b'data: {"type":"response.done","response":{"output_text":"Final Answer"}}',
            b'data: [DONE]'
        ]

        mock_response = MagicMock()
        mock_response.iter_lines.return_value = lines
        mock_response.status_code = 200
        mock_call_model.return_value = mock_response

        chunks = list(self.llm._stream("test prompt"))
        
        reasoning = "".join([c.generation_info.get("reasoning") for c in chunks if c.generation_info and "reasoning" in c.generation_info])
        content = "".join([c.text for c in chunks if c.text])
        
        self.assertEqual(reasoning, "Reviewing...")
        self.assertEqual(content, "Final Answer")

    @patch("src.agents.model_adapter.call_model")
    def test_openrouter_deduplication_with_done_chunk(self, mock_call_model):
        """测试 OpenRouter 在增量输出后发送 .done 块时的去重逻辑"""
        # 模拟 OpenRouter 流程：delta -> delta -> content_part.done (包含全量)
        lines = [
            b'data: {"type":"response.output_text.delta","delta":"Hello"}',
            b'data: {"type":"response.output_text.delta","delta":" World"}',
            b'data: {"type":"response.content_part.done","part":{"type":"output_text","text":"Hello World"}}',
            b'data: {"type":"response.completed","response":{"output_text":"Hello World"}}',
            b'data: [DONE]'
        ]
        
        mock_response = MagicMock()
        mock_response.iter_lines.return_value = lines
        mock_response.status_code = 200
        mock_call_model.return_value = mock_response

        chunks = list(self.llm._stream("test prompt"))
        
        # 应该只有 2 个增量块，没有重复的全量块
        texts = [c.text for c in chunks if c.text]
        self.assertEqual(texts, ["Hello", " World"])
        self.assertEqual(len(texts), 2)

if __name__ == "__main__":
    unittest.main()
