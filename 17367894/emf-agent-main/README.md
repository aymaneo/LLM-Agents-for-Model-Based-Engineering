# Quick Test

Run the agent:

```bash
pip install -r requirements.txt

python simple_emf_agent.py \
  --server /Users/aymane/Documents/AI/LLM-Agents-for-Model-Based-Engineering/17367894/emf-agent-main/emf_agent/emf_mcp_stateless.py \
  --recursion-limit 120
```

Then paste a prompt like this (adjust the metamodel path if needed):

```
Start a session with "/Users/aymane/Documents/AI/LLM-Agents-for-Model-Based-Engineering/Paper Artifacts SAM 2025/atl_zoo-master/Families2Persons/Families.ecore". After the session is ready, create a Family instance called SmithFamily, add Member objects John (father), Jane (mother), and Mike (son), link them to the family, and show me the final state of the family and each member.
```

