# Email to Tyler — submission

**To:** tyler.parks@wipro.com
**Subject:** Junior FDE Pre-screening — Atlas multi-agent system — Manasi Mathkar

---

Hi Tyler,

Submitting my Junior FDE pre-screening assignment for the multi-agent system. Quick links:

- **🌐 Live demo:** https://wipro-manasi.jc3b1dk9p8244.us-west-2.cs.amazonlightsail.com
- **📂 GitHub repo:** https://github.com/manasimathkar/atlas-multi-agent
- **📄 Written report (1–2 pages):** in the repo at `docs/Atlas_Report.docx`
- **🏗 Architecture diagram:** in the repo at `docs/architecture.svg` (also embedded at the top of the README)

**What I built — Atlas:** a research brief generator powered by five collaborating agents (Planner, Researchers, Writer, Critic, Security) orchestrated with LangGraph. The Planner decomposes a question into sub-questions, parallel Researchers each call Tavily and summarize with citations, the Writer synthesizes a brief, the Critic fact-checks against sources and can loop back for a revision, and the Security agent runs prompt-injection / PII / policy checkpoints on the input, every fetched web page, and the final output. The frontend is a FastAPI server with a custom HTML/JS UI; deployment is a Docker image on AWS Lightsail Containers (Oregon).

**To try it:** open the live URL, click the **🔋 Batteries** sample chip → **Run research** (a sourced brief renders in ~30–60s). Then click the red **⚠ Test injection** chip → **Run research** to see the input guardrail block a prompt-injection attempt.

Looking forward to walking through the architecture, security model, and trade-offs in the presentation on Thursday at 1:30 PM ET.

Thanks,
Manasi Mathkar
manasimathkar03@gmail.com
