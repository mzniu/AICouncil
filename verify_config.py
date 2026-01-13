"""快速验证配置加载"""
from src.config_manager import get_config

print("=" * 60)
print("关键配置验证")
print("=" * 60)

configs = [
    ('LOG_FILE', 'aicouncil.log'),
    ('LOG_LEVEL', 'INFO'),
    ('MODEL_BACKEND', 'ollama'),
    ('MODEL_NAME', 'qwen3:4b'),
    ('DEEPSEEK_API_KEY', 'sk-28126bb067bf4b4c9a526cba8eae460d'),
    ('OPENROUTER_API_KEY', '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'),
    ('GOOGLE_API_KEY', 'AIzaSyChtV3rsgX0l_QudP9IaPIUIYOUsPaYM_g'),
    ('GOOGLE_SEARCH_ENGINE_ID', '003ac4d2b6f0b4cc4'),
    ('SEARCH_PROVIDER', 'baidu,yahoo,google'),
    ('TAVILY_API_KEY', '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'),
    ('BROWSER_PATH', r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'),
]

all_correct = True
for key, expected_value in configs:
    actual_value = get_config(key)
    if actual_value == expected_value:
        print(f"✅ {key}: 正确")
    else:
        print(f"❌ {key}: 不匹配")
        print(f"   期望: {expected_value}")
        print(f"   实际: {actual_value}")
        all_correct = False

print("\n" + "=" * 60)
if all_correct:
    print("✅ 所有配置都正确加载！")
else:
    print("⚠️  部分配置未正确加载")
print("=" * 60)
