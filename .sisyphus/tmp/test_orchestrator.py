import sys
sys.path.insert(0, 'E:/Workspace/music_agent')

print('Starting test...')

from src.agent import MockLLMClient
from src.tools import build_default_registry
from src.manager.session_state import SessionState
from src.agent.orchestrator import Orchestrator

print('Imports done')

llm = MockLLMClient()
tools = build_default_registry()
orchestrator = Orchestrator(llm=llm, tools=tools)
state = SessionState(session_id='test-session')

print('Calling handle_turn...')

result = orchestrator.handle_turn('hip hop', state)

print('\\nResult:')
print('  recommendations:', len(result.get('recommendations', [])))

for i, rec in enumerate(result.get('recommendations', [])):
    print(f"\\n  {i+1}. {rec.get('name')}")
    print(f"     is_playable: {rec.get('is_playable')}")
    print(f"     audio_url: {rec.get('audio_url', 'N/A')[:60] if rec.get('audio_url') else 'N/A'}")
    print(f"     reason: {rec.get('reason', 'N/A')[:80]}...")