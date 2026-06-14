import os
from unittest.mock import MagicMock
from ice.core.pager import ContextPager

os.environ["ICE_POST_COMPRESSION_LIMIT"] = "1000"

pager = ContextPager(embedder=MagicMock(), max_tokens=100)
pager.enable_smart_sizing = False

system_msg = {"role": "system", "content": "CRITICAL."}
history = [{"role": "user", "content": "Filler."}]
current_request = [{"role": "user", "content": "Req."}]

assembled = pager.assemble_prompt(
    current_request=current_request,
    historical_messages=[system_msg] + history,
    retrieved_insights=["Insight."],
    reasoning_traces=["Reasoning."],
    model_id="test"
)

for m in assembled:
    print(f"Type: {type(m)}, Value: {m}")
