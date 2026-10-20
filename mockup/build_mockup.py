"""Inline mockup/data.json into mockup/template.html -> mockup/ai-model-market.html (the page that gets published)."""
from pathlib import Path

HERE = Path(__file__).resolve().parent
data = (HERE / "data.json").read_text().replace("</", "<\\/")
(HERE / "ai-model-market.html").write_text((HERE / "template.html").read_text().replace("/*DATA*/", data))
print("wrote", HERE / "ai-model-market.html")
