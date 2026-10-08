from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1] / "app"


def all_py_text():
    for path in ROOT.rglob("*.py"):
        yield path, path.read_text(encoding="utf-8")


def test_main_menu_labels_match_handlers():
    files = list(all_py_text())
    text = "\n".join(s for _, s in files)
    expected = [
        "📚 KITOBLAR",
        "🧠 TEST",
        "🏆 TOP",
        "👤 PROFIL",
        "ℹ️ YORDAM",
        "🛠 ADMIN",
    ]
    for label in expected:
        assert label in text, label


def test_back_buttons_have_handlers():
    files = list(all_py_text())
    text = "\n".join(s for _, s in files)
    expected = [
        "⬅️ ASOSIY MENYU",
        "⬅️ KITOBLAR",
        "⬅️ TESTLAR",
        "⬅️ ADMIN PANEL",
        "⬅️ KONTENT",
        "⬅️ FOYDALANUVCHILAR",
        "⬅️ KANALLAR",
        "⬅️ REYTING",
        "⬅️ TEST BOSHQARUVI",
        "⬅️ SOZLAMALAR",
    ]
    for label in expected:
        assert f'F.text == "{label}"' in text, label


def test_no_referral_or_time_based_leaderboards():
    files = list(all_py_text())
    text = "\n".join(s.lower() for _, s in files)
    for forbidden in ("referral", "weekly top", "monthly top", "season top"):
        assert forbidden not in text


def test_no_html_parse_mode():
    files = list(all_py_text())
    text = "\n".join(s.lower() for _, s in files)
    assert "parse_mode.html" not in text
    assert "parse_mode=\"html\"" not in text


def test_channel_post_reaction_exists():
    reaction_file = (ROOT / "handlers" / "channel_reactions.py").read_text(encoding="utf-8")
    assert "router.channel_post" in reaction_file
    assert "set_message_reaction" in reaction_file
    assert "ReactionTypeEmoji" in reaction_file
