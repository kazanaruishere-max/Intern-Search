from pkl_research.cv import analyze_cv, extract_text, fit_for_roles

AI_CV = """
Nama X
AI Engineer candidate
Summary: focused on AI development, LLM tooling, machine learning, and chatbots using Python, TensorFlow, ChromaDB, and Gemini. Built multi-agent LLM systems with RAG and vector databases.
Skills: Python, TensorFlow, PyTorch, LLM, NLP, computer vision, OpenAI, prompt engineering.
Projects:
SafeBot AI - built an AI chatbot using Gemini LLM and machine learning to detect fraud. Python + Next.js dashboard.
"""

GAME_CV = """
Nama Y
Game developer
Summary: game designer and programmer using Unity, C#, Godot, and GDScript. Built 2D games and participated in game jams.
Skills: Unity, Unreal, C#, Godot, Blender, 3D, game design.
Projects: Cora Quest - 2D eco game built in Godot/GDScript for a game jam. Designed levels and gameplay.
"""

FULLSTACK_CV = """
Nama Z
Fullstack developer
Summary: fullstack web developer using Next.js, React, Node.js, Express, TypeScript, and PostgreSQL. Build frontend and backend APIs.
Skills: Next.js, React, Vue, Node.js, Express, Laravel, MySQL, Postgres, Tailwind, REST.
Projects: Dashboard app - fullstack frontend and backend with database and REST API.
"""


def test_extract_text_txt(tmp_path):
    path = tmp_path / "cv.txt"
    path.write_text("Halo ini CV", encoding="utf-8")
    assert "CV" in extract_text(path)


def test_ai_cv_ranks_ai_top():
    analysis = analyze_cv(AI_CV)
    assert analysis["scores"]["ai"] > analysis["scores"]["software"]
    assert analysis["scores"]["ai"] > analysis["scores"]["game"]
    assert analysis["scores"]["ai"] >= 90


def test_game_cv_ranks_game_top():
    analysis = analyze_cv(GAME_CV)
    assert analysis["scores"]["game"] > analysis["scores"]["ai"]
    assert analysis["scores"]["game"] > analysis["scores"]["fullstack"]


def test_fullstack_cv_ranks_fullstack_top():
    analysis = analyze_cv(FULLSTACK_CV)
    assert analysis["scores"]["fullstack"] > analysis["scores"]["game"]
    assert analysis["scores"]["fullstack"] >= 80


def test_bare_ai_not_false_positive():
    # "terbaik"/"aplikasi" tidak boleh menaikkan skor AI
    analysis = analyze_cv("Kami membuat website terbaik untuk aplikasi pelanggan yang baik.")
    assert analysis["scores"]["ai"] < 50


def test_at_least_4_scores():
    analysis = analyze_cv(AI_CV)
    assert set(analysis["scores"]) == {"software", "ai", "fullstack", "game"}
    assert len(analysis["ats"]) >= 4


def test_fit_for_roles():
    analysis = analyze_cv(AI_CV)
    assert fit_for_roles(analysis, ["ai"]) >= 90
    assert fit_for_roles(analysis, ["game"]) < 50
    assert fit_for_roles(analysis, []) == 0.0
