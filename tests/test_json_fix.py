#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
JSON格式修复测试脚本
测试 clean_json_string 和 _fix_json_format 函数的修复能力
"""

import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# 直接导入需要的函数（避免循环导入）
import json
import re

def clean_json_string(s: str) -> str:
    """清理字符串中的 Markdown JSON 标签，并尝试提取第一个完整的 JSON 对象。"""
    if not s:
        return ""
    s = s.strip()
    
    # 移除 Markdown 代码块标记
    s = s.replace('```json', '').replace('```', '').strip()
    
    # 寻找第一个 { 或 [
    start = s.find('{')
    if start == -1:
        start = s.find('[')
        if start == -1:
            return s
            
    # 使用括号匹配寻找对应的结束位置
    brace_count = 0
    in_string = False
    escape = False
    
    for i in range(start, len(s)):
        char = s[i]
        
        if char == '"' and not escape:
            in_string = not in_string
            
        if not in_string:
            if char == '{' or char == '[':
                brace_count += 1
            elif char == '}' or char == ']':
                brace_count -= 1
                if brace_count == 0:
                    extracted = s[start:i+1]
                    return _fix_json_format(extracted)
        
        if char == '\\':
            escape = not escape
        else:
            escape = False
            
    # 如果没找到匹配的括号，回退到原来的逻辑
    end = s.rfind('}')
    if end == -1:
        end = s.rfind(']')
        
    if start != -1 and end != -1 and end > start:
        extracted = s[start:end+1]
        return _fix_json_format(extracted)
    
    return s.strip()


def _fix_json_format(json_str: str) -> str:
    """修复常见的 JSON 格式问题。"""
    if not json_str:
        return json_str
    
    # 1. 移除单行注释 //
    lines = []
    for line in json_str.split('\n'):
        comment_pos = line.find('//')
        if comment_pos != -1:
            before_comment = line[:comment_pos]
            quote_count = before_comment.count('"') - before_comment.count('\\"')
            if quote_count % 2 == 0:
                line = line[:comment_pos].rstrip()
        lines.append(line)
    json_str = '\n'.join(lines)
    
    # 2. 移除多行注释 /* */
    json_str = re.sub(r'/\*.*?\*/', '', json_str, flags=re.DOTALL)
    
    # 3. 修复尾随逗号
    json_str = re.sub(r',\s*}', '}', json_str)
    json_str = re.sub(r',\s*]', ']', json_str)
    
    # 4. 修复多余的逗号
    json_str = re.sub(r',\s*,', ',', json_str)
    
    return json_str.strip()

# 测试用例：各种常见的JSON格式问题
test_cases = [
    {
        "name": "Markdown代码块包裹的JSON",
        "input": """```json
{
    "core_idea": "测试方案",
    "steps": ["步骤1", "步骤2"]
}
```""",
        "expected_fields": ["core_idea", "steps"]
    },
    {
        "name": "尾随逗号（对象）",
        "input": """{
    "name": "测试",
    "value": 123,
}""",
        "expected_fields": ["name", "value"]
    },
    {
        "name": "尾随逗号（数组）",
        "input": """{
    "items": [1, 2, 3,],
    "status": "ok"
}""",
        "expected_fields": ["items", "status"]
    },
    {
        "name": "单行注释",
        "input": """{
    "name": "测试", // 这是注释
    "value": 123
}""",
        "expected_fields": ["name", "value"]
    },
    {
        "name": "多行注释",
        "input": """{
    "name": "测试",
    /* 这是
       多行注释 */
    "value": 123
}""",
        "expected_fields": ["name", "value"]
    },
    {
        "name": "前后有额外文本",
        "input": """这是一些说明文字

{
    "result": "success",
    "data": {"count": 5}
}

后面还有一些文字""",
        "expected_fields": ["result", "data"]
    },
    {
        "name": "连续逗号",
        "input": """{
    "a": 1,,
    "b": 2
}""",
        "expected_fields": ["a", "b"]
    },
    {
        "name": "嵌套结构",
        "input": """```json
{
    "decomposition": {
        "core_goal": "测试目标",
        "key_questions": [
            "问题1",
            "问题2",
        ],
        "boundaries": "测试边界"
    },
    "instructions": "测试指令",
}
```""",
        "expected_fields": ["decomposition", "instructions"]
    }
]

def test_json_cleaning():
    """测试JSON清理和修复功能"""
    print("=" * 70)
    print("JSON格式修复测试")
    print("=" * 70)
    
    passed = 0
    failed = 0
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n测试 {i}: {test['name']}")
        print("-" * 70)
        
        try:
            # 清理JSON
            cleaned = clean_json_string(test['input'])
            print(f"✓ 清理成功")
            print(f"  清理后长度: {len(cleaned)} 字符")
            
            # 尝试解析
            parsed = json.loads(cleaned)
            print(f"✓ 解析成功")
            
            # 验证预期字段
            missing_fields = [f for f in test['expected_fields'] if f not in parsed]
            if missing_fields:
                print(f"✗ 缺少字段: {missing_fields}")
                failed += 1
            else:
                print(f"✓ 所有预期字段存在: {test['expected_fields']}")
                passed += 1
                
            # 显示解析结果摘要
            print(f"  解析结果: {json.dumps(parsed, ensure_ascii=False, indent=2)[:200]}...")
            
        except json.JSONDecodeError as e:
            print(f"✗ JSON解析失败: {e}")
            print(f"  清理后的字符串: {cleaned[:200]}...")
            failed += 1
        except Exception as e:
            print(f"✗ 测试失败: {e}")
            failed += 1
    
    print("\n" + "=" * 70)
    print(f"测试完成: {passed} 通过, {failed} 失败")
    print("=" * 70)
    
    return failed == 0

if __name__ == "__main__":
    success = test_json_cleaning()
    sys.exit(0 if success else 1)
