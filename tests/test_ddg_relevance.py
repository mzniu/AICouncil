import sys
import pathlib
import os

# Ensure project root is on sys.path
ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.utils import search_utils

def test_ddg():
    query = "2024年全球AI大模型排名"
    print(f"\nTesting DuckDuckGo search for: {query}")
    result = search_utils.duckduckgo_search(query, max_results=5)
    print("\n--- DuckDuckGo Search Result ---")
    print(result)
    print("--------------------------\n")

if __name__ == "__main__":
    test_ddg()
