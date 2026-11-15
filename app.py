
"""Word Passport — single-page Streamlit vocabulary app.
Run: streamlit run app.py
"""
import html
import random
import re
import unicodedata
from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Word Passport | Vocabulary", page_icon="📚", layout="centered", initial_sidebar_state="collapsed")

# Original CSV categories. These school-level names are an app design choice,
# not an official claim about the source document's school-level classification.
LEVELS = {
    "초등학교 · Elementary": "Elementary",
    "중학교 · MidHigh": "MidHigh",
    "고등학교 · Extended": "Extended",
}
# Hand-reviewed illustrative relationships. Unlisted words show no relationship.
# Related words are enrichment, not an automatically inferred CSV field.
RELATIONS = {
    "abandon": (["leave", "desert"], ["keep", "retain"]),
    "able": (["capable"], ["unable"]),
    "accept": (["receive", "agree to"], ["reject", "refuse"]),
    "active": (["energetic"], ["inactive", "passive"]),
    "ancient": (["old", "historic"], ["modern", "recent"]),
    "angry": (["mad", "furious"], ["calm", "pleased"]),
    "answer": (["reply", "response"], []),
    "beautiful": (["pretty", "lovely"], ["ugly"]),
    "begin": (["start", "commence"], ["finish", "end"]),
    "big": (["large", "huge"], ["small", "tiny"]),
    "bright": (["shining", "luminous"], ["dim", "dark"]),
    "calm": (["peaceful", "quiet"], ["agitated"]),
    "careful": (["cautious"], ["careless"]),
    "cheap": (["inexpensive"], ["expensive"]),
    "clean": (["tidy"], ["dirty"]),
    "close": (["shut"], ["open"]),
    "cold": (["chilly", "cool"], ["hot", "warm"]),
    "common": (["usual", "ordinary"], ["rare", "unusual"]),
    "dangerous": (["risky", "unsafe"], ["safe"]),
    "dark": (["dim"], ["bright", "light"]),
    "difficult": (["hard", "challenging"], ["easy", "simple"]),
    "early": (["ahead of time"], ["late"]),
    "easy": (["simple"], ["difficult", "hard"]),
    "empty": (["vacant"], ["full"]),
    "fast": (["quick", "rapid"], ["slow"]),
    "famous": (["well-known"], ["unknown", "obscure"]),
    "friend": (["companion", "pal"], ["enemy"]),
    "happy": (["glad", "joyful"], ["sad", "unhappy"]),
    "high": (["tall", "elevated"], ["low"]),
    "honest": (["truthful"], ["dishonest"]),
    "hot": (["warm"], ["cold"]),
    "important": (["significant", "major"], ["unimportant", "minor"]),
    "increase": (["grow", "rise"], ["decrease", "reduce"]),
    "kind": (["caring", "considerate"], ["cruel", "unkind"]),
    "large": (["big", "huge"], ["small"]),
    "late": (["delayed"], ["early"]),
    "love": (["affection"], ["hate"]),
    "new": (["recent", "fresh"], ["old"]),
    "noisy": (["loud"], ["quiet"]),
    "old": (["aged"], ["new", "young"]),
    "poor": (["needy"], ["rich", "wealthy"]),
    "quick": (["fast", "rapid"], ["slow"]),
    "rich": (["wealthy"], ["poor"]),
    "safe": (["secure"], ["dangerous", "unsafe"]),
    "sad": (["unhappy", "sorrowful"], ["happy", "glad"]),
    "short": (["brief"], ["long"]),
    "slow": (["unhurried"], ["fast", "quick"]),
    "small": (["little", "tiny"], ["big", "large"]),
    "strong": (["powerful"], ["weak"]),
    "success": (["achievement"], ["failure"]),
    "true": (["correct", "accurate"], ["false"]),
    "weak": (["feeble"], ["strong"]),
    "young": (["youthful"], ["old"]),
}

st.markdown("""<style>
.block-container{max-width:880px;padding-top:1.4rem;padding-bottom:3rem}
.wp-hero{padding:1.5rem 1.2rem;border-radius:20px;background:linear-gradient(125deg,#132a46,#24547b);color:white;margin-bottom:1rem}
.wp-hero h1{color:white;margin:0;font-size:clamp(1.65rem,5vw,2.6rem)}
.wp-hero p{color:#dcecf9;margin:.5rem 0 0}
.wp-card{border:1px solid #dce5ee;border-radius:18px;padding:1.5rem;text-align:center;margin:1rem 0;background:#f8fbff;color:#162c43}
.wp-word{font-size:clamp(2rem,8vw,3.5rem);font-weight:800;overflow-wrap:anywhere}
.wp-meaning{font-size:clamp(1.35rem,5vw,2rem);font-weight:650}
.wp-error{border:2px solid #d73535;border-left:9px solid #d73535;border-radius:12px;padding:1rem;margin:.6rem 0;background:#fff1f1;color:#782020}
.wp-warn{border:2px solid #e5a22c;border-radius:12px;padding:1rem;margin:.6rem 0;background:#fff8e8;color:#704a0b}
.wp-good{border:1px solid #b6d8c3;border-radius:12px;padding:1rem;margin:.6rem 0;background:#f0faf3;color:#225d35}
@media(max-width:600px){.block-container{padding-left:.85rem;padding-right:.85rem}.wp-card{padding:1.1rem}.wp-hero{padding:1.15rem}}
</style>""", unsafe_allow_html=True)

@st.cache_data(show_spinner=False)
def load_words():
    path = Path(__file__).resolve().parent / "vocabulary.csv"
    data = pd.read_csv(path, encoding="utf-8-sig", dtype=str).fillna("")
    needed = {"Word", "Level", "Korean meaning (뜻)"}
    if not needed.issubset(data.columns):
        raise ValueError(f"CSV에 필요한 열이 없습니다: {', '.join(sorted(needed - set(data.columns)))}")
    for c in needed:
        data[c] = data[c].astype(str).str.strip()
    data = data[(data["Word"] != "") & (data["Korean meaning (뜻)"] != "")]
    return data.reset_index(drop=True)


def clean(s):
    s = unicodedata.normalize("NFKC", str(s)).casefold().strip()
    return re.sub(r"[\s.,!?\-_'\"’]+", "", s)


def accepted_meanings(meaning):
    # CSV sometimes lists multiple glosses; permit common separators.
    values = [meaning]
    values.extend(re.split(r"[,;/、]|\s*\([^)]*\)\s*", meaning))
    values.extend(re.split(r"\s+(?:또는|혹은)\s+", meaning))
    return {clean(v) for v in values if clean(v)}


def is_correct(answer, item, direction):
    if direction == "EN → KO":
        return clean(answer) in accepted_meanings(item["meaning"])
    return clean(answer) == clean(item["word"])


def relation_block(word):
    syn, ant = RELATIONS.get(word.lower(), ([], []))
    if syn or ant:
        with st.expander("🔎 관련 어휘 · Synonyms & Antonyms", expanded=False):
            if syn:
                st.write("**유의어 (Synonyms):** " + ", ".join(syn))
            if ant:
                st.write("**반의어 (Antonyms):** " + ", ".join(ant))
            st.caption("관련 어휘는 일부 단어에만 제공하며, 문맥에 따라 완전히 바꿔 쓸 수는 없습니다.")


def new_pack(data, level):
    pool = data[data["Level"] == level]
    if len(pool) < 20:
        st.error("이 수준에는 20개 이상의 단어가 필요합니다.")
        return
    rows = pool.sample(n=20).to_dict("records")
    st.session_state.pack = [{"word": r["Word"], "meaning": r["Korean meaning (뜻)"], "level": r["Level"]} for r in rows]
    st.session_state.pack_level = level
    st.session_state.phase = "Flashcards"
    st.session_state.card_idx = 0
    st.session_state.card_revealed = False
    st.session_state.quiz_idx = 0
    st.session_state.quiz_attempt = 0
    st.session_state.quiz_feedback = ""
    st.session_state.quiz_resolved = False
    st.session_state.results = {}
    st.session_state.quiz_directions = ["EN → KO", "KO → EN"] * 10
    random.shuffle(st.session_state.quiz_directions)
    st.session_state.answer_key = 0


def go(phase):
    st.session_state.phase = phase
    st.rerun()


try:
    words = load_words()
except Exception as e:
    st.error(f"단어 파일을 읽지 못했습니다: {e}")
    st.stop()

st.markdown('<div class="wp-hero"><h1>📚 Word Passport</h1><p>Choose your level · Learn 20 words · Practice · Review</p></div>', unsafe_allow_html=True)

if "pack" not in st.session_state:
    st.session_state.pack = []
    st.session_state.phase = "Flashcards"

level_label = st.selectbox("🎓 학습 수준 선택", list(LEVELS), index=1)
selected_level = LEVELS[level_label]
level_count = int((words["Level"] == selected_level).sum())
st.caption(f"전체 데이터 {len(words):,}개 · 선택한 수준 {level_count:,}개 · 한 묶음 20개")

left, right = st.columns([1.25, 1])
with left:
    if st.button("🎲 새로운 20개 단어 시작", type="primary", use_container_width=True):
        new_pack(words, selected_level)
        st.rerun()
with right:
    if st.session_state.pack:
        st.caption("현재 묶음: " + {"Elementary": "초등", "MidHigh": "중등", "Extended": "고등"}.get(st.session_state.pack_level, st.session_state.pack_level))
    else:
        st.caption("시작 버튼을 눌러 학습하세요.")

if not st.session_state.pack:
    st.info("난이도를 선택하고 ‘새로운 20개 단어 시작’을 눌러 주세요.")
    st.stop()

if selected_level != st.session_state.pack_level:
    st.warning("현재 학습 중인 묶음은 이전에 선택한 수준입니다. 새로운 수준으로 바꾸려면 ‘새로운 20개 단어 시작’을 눌러 주세요.")

phase = st.radio("학습 단계", ["Flashcards", "Quiz", "Review"], horizontal=True, key="phase")
pack = st.session_state.pack

if phase == "Flashcards":
    idx = st.session_state.card_idx
    item = pack[idx]
    st.progress((idx + 1) / len(pack), text=f"Flashcard {idx + 1} / {len(pack)}")
    if st.session_state.card_revealed:
        st.markdown(f'<div class="wp-card"><div class="wp-word">{html.escape(item["word"])}</div><hr><div class="wp-meaning">{html.escape(item["meaning"])}</div></div>', unsafe_allow_html=True)
        relation_block(item["word"])
    else:
        st.markdown(f'<div class="wp-card"><div class="wp-word">{html.escape(item["word"])}</div><p>뜻을 생각한 후 정답을 확인하세요.</p></div>', unsafe_allow_html=True)
    if st.button("🔄 뜻 숨기기" if st.session_state.card_revealed else "👀 뜻 확인하기", use_container_width=True):
        st.session_state.card_revealed = not st.session_state.card_revealed
        st.rerun()
    a, b = st.columns(2)
    with a:
        if st.button("← 이전 단어", disabled=idx == 0, use_container_width=True):
            st.session_state.card_idx -= 1
            st.session_state.card_revealed = False
            st.rerun()
    with b:
        if st.button("다음 단어 →", disabled=idx == len(pack) - 1, use_container_width=True):
            st.session_state.card_idx += 1
            st.session_state.card_revealed = False
            st.rerun()
    if st.button("✏️ Quiz 시작", type="primary", use_container_width=True):
        go("Quiz")

elif phase == "Quiz":
    idx = st.session_state.quiz_idx
    if idx >= len(pack):
        st.success("🎉 20문제를 모두 풀었습니다!")
        results = st.session_state.results
        perfect = sum(1 for r in results.values() if r["mistakes"] == 0)
        st.metric("첫 시도 정답", f"{perfect} / {len(pack)}")
        if st.button("🔍 오답 복습하기", type="primary", use_container_width=True):
            go("Review")
    else:
        item = pack[idx]
        direction = st.session_state.quiz_directions[idx]
        st.progress((idx + 1) / len(pack), text=f"Quiz {idx + 1} / {len(pack)}")
        if direction == "EN → KO":
            st.markdown(f'<div class="wp-card"><div class="wp-word">{html.escape(item["word"])}</div><p>한국어 뜻을 입력하세요.</p></div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="wp-card"><div class="wp-meaning">{html.escape(item["meaning"])}</div><p>영어 단어를 입력하세요.</p></div>', unsafe_allow_html=True)

        if st.session_state.quiz_attempt == 1 and not st.session_state.quiz_resolved:
            if direction == "KO → EN":
                word = item["word"]
                hint = f"첫 글자: {word[:1].upper()} · 글자 수: {len(word)}"
            else:
                meaning = item["meaning"]
                hint = f"한국어 뜻의 첫 글자: {meaning[:1]} · 첫 번째 뜻의 글자 수: {len(meaning.split(',')[0].strip())}"
            st.warning(f"💡 힌트: {hint} — 한 번 더 도전해 보세요!")

        if st.session_state.quiz_resolved:
            if st.session_state.quiz_feedback == "correct_first":
                st.success("정답! 첫 번째 시도에 맞혔어요.")
            elif st.session_state.quiz_feedback == "correct_second":
                st.warning("힌트 후 정답! 이 단어는 Review에 표시됩니다.")
            else:
                st.error("두 번 모두 틀렸어요. Review에서 다시 공부해 보세요.")
            st.write(f'**정답:** {item["word"]} — {item["meaning"]}')
            relation_block(item["word"])
            if st.button("다음 문제 →" if idx < 19 else "결과 확인 →", type="primary", use_container_width=True):
                st.session_state.quiz_idx += 1
                st.session_state.quiz_attempt = 0
                st.session_state.quiz_resolved = False
                st.session_state.quiz_feedback = ""
                st.session_state.answer_key += 1
                st.rerun()
        else:
            with st.form(key=f"answer_{st.session_state.answer_key}", clear_on_submit=False):
                answer = st.text_input("정답 입력", placeholder="여기에 답을 입력하세요", autocomplete="off")
                submitted = st.form_submit_button("정답 확인", type="primary", use_container_width=True)
            if submitted:
                if not answer.strip():
                    st.warning("답을 입력해 주세요.")
                else:
                    correct = is_correct(answer, item, direction)
                    if correct:
                        mistakes = st.session_state.quiz_attempt
                        st.session_state.results[idx] = {"mistakes": mistakes, "direction": direction, "last_answer": answer}
                        st.session_state.quiz_feedback = "correct_first" if mistakes == 0 else "correct_second"
                        st.session_state.quiz_resolved = True
                    elif st.session_state.quiz_attempt == 0:
                        st.session_state.quiz_attempt = 1
                    else:
                        st.session_state.results[idx] = {"mistakes": 2, "direction": direction, "last_answer": answer}
                        st.session_state.quiz_feedback = "incorrect_second"
                        st.session_state.quiz_resolved = True
                    st.rerun()

else:
    results = st.session_state.results
    if not results:
        st.info("아직 퀴즈 기록이 없습니다. Quiz를 먼저 풀어 주세요.")
        if st.button("Quiz로 이동", type="primary"):
            go("Quiz")
    else:
        wrong = [(i, r) for i, r in results.items() if r["mistakes"] > 0]
        perfect = sum(1 for r in results.values() if r["mistakes"] == 0)
        c1, c2, c3 = st.columns(3)
        c1.metric("풀이 완료", f"{len(results)} / 20")
        c2.metric("첫 시도 정답", perfect)
        c3.metric("복습할 단어", len(wrong))
        st.caption("한 번이라도 틀린 단어는 복습 대상으로 표시합니다.")
        if not wrong:
            st.success("지금까지 틀린 단어가 없어요! 🎉")
        for i, r in sorted(wrong, key=lambda pair: -pair[1]["mistakes"]):
            item = pack[i]
            if r["mistakes"] >= 2:
                st.markdown(f'<div class="wp-error"><strong>🔴 집중 복습 · 2차 오답</strong><br><strong>{html.escape(item["word"])}</strong> — {html.escape(item["meaning"])}<br><small>문제 유형: {html.escape(r["direction"])}</small></div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="wp-warn"><strong>🟠 복습 필요 · 힌트 후 정답</strong><br><strong>{html.escape(item["word"])}</strong> — {html.escape(item["meaning"])}<br><small>문제 유형: {html.escape(r["direction"])}</small></div>', unsafe_allow_html=True)
            relation_block(item["word"])
        if st.button("🔁 같은 20개 단어 퀴즈 다시 풀기", use_container_width=True):
            st.session_state.quiz_idx = 0
            st.session_state.quiz_attempt = 0
            st.session_state.quiz_resolved = False
            st.session_state.quiz_feedback = ""
            st.session_state.results = {}
            st.session_state.answer_key += 1
            go("Quiz")

st.divider()
st.caption("Word Passport · CSV 기반 3,000개 단어 · 학습 결과는 현재 브라우저 세션에서만 유지됩니다.")
