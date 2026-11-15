
"""Word Passport — level-adapted travel vocabulary and reading.
Run: streamlit run app.py
Required files: app.py, vocabulary.csv, requirements.txt
"""
import html
import io
import random
import re
import unicodedata
from pathlib import Path

import pandas as pd
import streamlit as st
from gtts import gTTS

st.set_page_config(page_title="Word Passport", page_icon="📚", layout="centered")

LEVELS = {"초등": "Elementary", "중등": "MidHigh", "고등": "Extended"}
LABELS = {value: key for key, value in LEVELS.items()}
TARGET_COUNTS = {"Elementary": 5, "MidHigh": 8, "Extended": 12}

# 뜻이 일치하는지 검토한 항목만 보여 줍니다. 자동 사전 매칭을 하지 않습니다.
RELATED = {
    "happy": (["glad", "joyful"], ["sad", "unhappy"]),
    "sad": (["unhappy"], ["happy"]),
    "big": (["large", "huge"], ["small"]),
    "small": (["little", "tiny"], ["large", "big"]),
    "fast": (["quick", "rapid"], ["slow"]),
    "slow": (["unhurried"], ["fast", "quick"]),
    "easy": (["simple"], ["difficult"]),
    "difficult": (["hard", "challenging"], ["easy"]),
    "begin": (["start"], ["finish", "end"]),
    "start": (["begin"], ["finish", "end"]),
    "safe": (["secure"], ["dangerous", "unsafe"]),
    "dangerous": (["unsafe", "risky"], ["safe"]),
    "early": (["ahead of time"], ["late"]),
    "late": (["delayed"], ["early"]),
    "rich": (["wealthy"], ["poor"]),
    "poor": (["needy"], ["rich"]),
    "strong": (["powerful"], ["weak"]),
    "weak": (["feeble"], ["strong"]),
    "arrive": (["reach"], ["depart", "leave"]),
    "reserve": (["book"], ["cancel"]),
    "recommend": (["suggest"], []),
    "journey": (["trip"], []),
    "delay": (["postpone"], []),
    "confirm": (["verify"], []),
    "adequate": (["sufficient"], ["inadequate"]),
    "flexible": (["adaptable"], ["rigid"]),
    "valid": (["acceptable"], ["invalid"]),
    "negotiate": (["bargain"], []),
    "diverse": (["varied"], ["uniform"]),
    "anticipate": (["expect"], []),
    "compensate": (["reimburse"], []),
}

# 각 문장은 (영어, 한국어) 형태입니다.
# {{word}}는 플래시카드 및 빈칸 문제로 연결됩니다.
# 해당 수준의 vocabulary.csv에 실제 존재하는 단어만 목표 어휘로 사용합니다.
PASSAGES = {
    "Elementary": [
        {"title": "공항으로 가는 길", "sentences": [
            ("I have a {{ticket}} and a {{bag}}.", "나는 표와 가방을 가지고 있다."),
            ("I take a {{bus}} with my mom.", "나는 엄마와 버스를 탄다."),
            ("We look at a {{map}}.", "우리는 지도를 본다."),
            ("We {{arrive}} early.", "우리는 일찍 도착한다."),
        ]},
        {"title": "바닷가 여행", "sentences": [
            ("We go to the {{beach}}.", "우리는 해변에 간다."),
            ("I bring some {{water}}.", "나는 물을 조금 가져간다."),
            ("We play with a {{ball}}.", "우리는 공을 가지고 논다."),
            ("I eat an {{apple}}.", "나는 사과를 먹는다."),
            ("I take a {{picture}}.", "나는 사진을 찍는다."),
        ]},
        {"title": "기차 여행", "sentences": [
            ("I buy a {{ticket}}.", "나는 표를 산다."),
            ("I take the {{train}}.", "나는 기차를 탄다."),
            ("I look out the {{window}}.", "나는 창밖을 본다."),
            ("I {{visit}} my friend.", "나는 친구를 방문한다."),
            ("We eat {{lunch}} together.", "우리는 함께 점심을 먹는다."),
        ]},
    ],
    "MidHigh": [
        {"title": "공항에서 생긴 일", "sentences": [
            ("Our {{flight}} was delayed because of heavy rain.", "폭우 때문에 우리 비행기가 지연되었다."),
            ("We waited at the {{airport}} for an update.", "우리는 새 소식을 기다리며 공항에 있었다."),
            ("An employee explained the reason for the {{delay}}.", "직원이 지연 사유를 설명했다."),
            ("She told us to check the new {{schedule}}.", "그녀는 새 일정을 확인하라고 말했다."),
            ("Our boarding {{gate}} had also changed.", "탑승구도 바뀌었다."),
            ("We needed to {{confirm}} the departure time.", "우리는 출발 시간을 확인해야 했다."),
            ("A staff member helped us find the correct {{document}}.", "직원이 올바른 서류를 찾도록 도와주었다."),
            ("We finally reached our {{hotel}} late at night.", "우리는 마침내 밤늦게 호텔에 도착했다."),
        ]},
        {"title": "호텔 체크인", "sentences": [
            ("Before our trip, I called the {{hotel}}.", "여행 전에 나는 호텔에 전화했다."),
            ("I wanted to {{reserve}} a room for two nights.", "나는 이틀 밤 묵을 객실을 예약하고 싶었다."),
            ("The employee asked me to {{confirm}} my name.", "직원은 내 이름을 확인해 달라고 했다."),
            ("She showed me the daily {{schedule}}.", "그녀는 일일 일정을 보여주었다."),
            ("She also offered to {{recommend}} a restaurant.", "그녀는 식당을 추천해 주겠다고도 했다."),
            ("We asked a {{local}} person for directions.", "우리는 현지인에게 길을 물었다."),
            ("Our {{guide}} helped us explore the area.", "우리 안내원이 주변을 둘러보도록 도와주었다."),
            ("It was a pleasant {{experience}}.", "그것은 즐거운 경험이었다."),
        ]},
        {"title": "박물관 관광", "sentences": [
            ("We visited a famous {{museum}} on our trip.", "우리는 여행 중 유명한 박물관을 방문했다."),
            ("Our {{guide}} welcomed us at the entrance.", "안내원이 입구에서 우리를 맞이했다."),
            ("She explained the city's {{past}}.", "그녀는 도시의 오랜 역사를 설명했다."),
            ("We learned about {{foreign}} visitors from the past.", "우리는 과거의 외국인 방문객에 대해 배웠다."),
            ("A {{local}} artist's work was on display.", "현지 예술가의 작품이 전시되어 있었다."),
            ("The tour was a valuable {{experience}}.", "그 관광은 값진 경험이었다."),
            ("We continued our {{journey}} after lunch.", "우리는 점심 식사 후 여행을 계속했다."),
            ("We stayed within our travel {{budget}}.", "우리는 여행 예산을 지켰다."),
        ]},
    ],
    "Extended": [
        {"title": "해외여행 준비", "sentences": [
            ("Before departure, I checked whether my {{passport}} was still {{valid}}.", "출발 전에 나는 여권이 여전히 유효한지 확인했다."),
            ("I tried to {{anticipate}} problems that might occur abroad.", "나는 해외에서 발생할 수 있는 문제를 예상하려고 했다."),
            ("I prepared an {{adequate}} amount of money for emergencies.", "나는 비상시에 쓸 충분한 돈을 준비했다."),
            ("I compared the {{currency}} rates before exchanging cash.", "현금을 환전하기 전에 환율을 비교했다."),
            ("I wanted to be {{flexible}} if my plans changed.", "계획이 바뀌더라도 유연하게 대처하고 싶었다."),
            ("The airline provided {{efficient}} online check-in services.", "항공사는 효율적인 온라인 체크인 서비스를 제공했다."),
            ("Every {{passenger}} needed to bring the correct documents.", "모든 승객은 올바른 서류를 가져와야 했다."),
            ("I hoped to {{explore}} new places during the trip.", "나는 여행 중 새로운 장소를 탐험하고 싶었다."),
            ("I expected to encounter {{diverse}} traditions.", "나는 다양한 전통을 접할 것으로 기대했다."),
            ("I wanted to {{interpret}} unfamiliar customs respectfully.", "나는 낯선 관습을 존중하며 이해하고 싶었다."),
            ("Travel can change a person's {{perspective}}.", "여행은 사람의 관점을 바꿀 수 있다."),
            ("Careful preparation helped me feel confident.", "철저한 준비 덕분에 자신감이 생겼다."),
        ]},
        {"title": "예상치 못한 호텔 문제", "sentences": [
            ("The hotel could not {{accommodate}} our entire group.", "호텔은 우리 일행 전체를 수용할 수 없었다."),
            ("We had to {{negotiate}} with the manager.", "우리는 관리자와 협상해야 했다."),
            ("She offered to {{compensate}} us for the inconvenience.", "그녀는 불편에 대한 보상을 제안했다."),
            ("We remained {{flexible}} and considered other options.", "우리는 유연하게 대처하며 다른 선택지를 고려했다."),
            ("The manager suggested an {{adequate}} replacement room.", "관리자는 충분히 적절한 대체 객실을 제안했다."),
            ("We needed a {{valid}} booking confirmation.", "우리는 유효한 예약 확인서가 필요했다."),
            ("We tried to {{anticipate}} additional difficulties.", "우리는 추가적인 어려움을 예상하려고 했다."),
            ("The staff found an {{efficient}} solution.", "직원들은 효율적인 해결책을 찾았다."),
            ("We decided to {{explore}} the neighborhood while waiting.", "기다리는 동안 우리는 주변 지역을 둘러보기로 했다."),
            ("The city had {{diverse}} places to eat.", "그 도시에는 다양한 식당이 있었다."),
            ("The experience changed our {{perspective}} on travel.", "그 경험은 여행에 대한 우리의 관점을 바꾸었다."),
            ("We learned to {{interpret}} unexpected events more calmly.", "우리는 예상치 못한 일을 더 차분하게 받아들이는 법을 배웠다."),
        ]},
        {"title": "다양한 문화를 만나는 여행", "sentences": [
            ("We planned to {{explore}} a city with diverse traditions.", "우리는 다양한 전통을 지닌 도시를 탐험할 계획이었다."),
            ("Our {{perspective}} changed as we met new people.", "새로운 사람들을 만나면서 우리의 관점이 달라졌다."),
            ("A guide helped us {{interpret}} unfamiliar customs.", "안내원은 낯선 관습을 이해하도록 도와주었다."),
            ("We tried to {{anticipate}} cultural differences.", "우리는 문화적 차이를 미리 예상하려고 했다."),
            ("We kept our plans {{flexible}}.", "우리는 계획을 유연하게 유지했다."),
            ("An {{adequate}} travel budget helped us relax.", "충분한 여행 예산 덕분에 여유를 가질 수 있었다."),
            ("We exchanged our {{currency}} before visiting the market.", "시장에 가기 전에 화폐를 환전했다."),
            ("We made sure our {{passport}} was secure.", "우리는 여권을 안전하게 보관했다."),
            ("Our tickets remained {{valid}} throughout the trip.", "여행 내내 우리 표는 유효했다."),
            ("We chose an {{efficient}} transportation option.", "우리는 효율적인 교통수단을 선택했다."),
            ("Each {{passenger}} followed the guide's instructions.", "각 승객은 안내원의 지시를 따랐다."),
            ("When a problem arose, we learned to {{negotiate}} politely.", "문제가 생겼을 때 우리는 정중하게 협상하는 법을 배웠다."),
        ]},
    ],
}

st.markdown("""<style>
.block-container{max-width:880px;padding-top:1.4rem;padding-bottom:3rem}
.hero{background:#193b59;color:#fff;border-radius:18px;padding:22px;margin-bottom:18px}
.hero h1{color:#fff;margin:0}.hero p{color:#d8e9f7;margin:8px 0 0}
.flash{background:#f5f8fd;color:#17283e;border-radius:20px;padding:30px 18px;text-align:center;margin:15px 0}
.word{font-size:clamp(32px,6vw,56px);font-weight:800;overflow-wrap:anywhere}
.meaning{font-size:clamp(20px,4vw,28px);font-weight:650}
.sentence{border:1px solid #8b98a8;border-radius:12px;padding:14px;margin:10px 0}
.english{font-size:1.1rem;line-height:1.75}.translation{color:#68798d;font-size:.94rem;margin-top:5px}
.blank{color:#b45309;font-weight:800}
/* Five-stage journey */
.step-track{display:flex;gap:7px;flex-wrap:wrap;margin:12px 0}
.step-pill{padding:9px 12px;border-radius:22px;font-size:.82rem;font-weight:650}
.step-pill.active{background:#cf6a9c;color:white;box-shadow:0 4px 12px #db9bbb66}
.step-pill.done{background:#f7d4e4;color:#81405f}
.step-pill.future{background:#fff9fc;color:#aa91a0;border:1px solid #f3d6e4}
/* Cherry blossom theme: all effects stay behind learning content. */
.stApp{background:linear-gradient(145deg,#fff7fb 0%,#fff0f6 50%,#fffafc 100%);color:#59364b}
[data-testid="stSidebar"]{background:#ffedf5}
[data-testid="stSidebar"] *{color:#713e59}
h1,h2,h3{color:#8c3d67!important}
.hero{background:linear-gradient(120deg,#c85b91,#f5a7c8);box-shadow:0 10px 28px #cf7ea33b}
.hero h1{color:#fff!important}.hero p{color:#fff4f8}
.flash{background:#fff9fc;border:1px solid #f1b8d2;box-shadow:0 8px 20px #eeb0cd33}
.sentence{background:#fffafd;border-color:#f0bad3}
.translation{color:#855e73}
.blank{color:#b64b84}
.stButton>button[kind="primary"]{background:#c85b91;border-color:#c85b91}
.stButton>button[kind="primary"]:hover{background:#ad477b;border-color:#ad477b}
.petal-field{position:fixed;inset:0;pointer-events:none;z-index:0;overflow:hidden}
.petal{position:absolute;top:-12vh;left:var(--x);font-size:var(--size);opacity:.4;animation:petal-fall var(--duration) linear infinite;animation-delay:var(--delay);filter:blur(.15px)}
@keyframes petal-fall{0%{transform:translate3d(0,-10vh,0) rotate(0deg)}100%{transform:translate3d(var(--drift),115vh,0) rotate(540deg)}}
@media(prefers-reduced-motion:reduce){.petal{animation:none;display:none}}
[data-testid="stMainBlockContainer"], [data-testid="stSidebarContent"]{position:relative;z-index:1}
</style>""", unsafe_allow_html=True)

# Static, lightweight CSS animation: no JavaScript, network assets or image files.
PETALS = [
    ("5%", "15s", "-5s", "36px", "18px"),
    ("15%", "21s", "-13s", "-42px", "15px"),
    ("28%", "18s", "-7s", "55px", "22px"),
    ("40%", "24s", "-19s", "-30px", "16px"),
    ("52%", "17s", "-10s", "48px", "19px"),
    ("64%", "22s", "-3s", "-58px", "14px"),
    ("77%", "20s", "-16s", "40px", "20px"),
    ("91%", "25s", "-9s", "-35px", "17px"),
]
petal_markup = "".join(
    f'<span class="petal" style="--x:{x};--duration:{duration};'
    f'--delay:{delay};--drift:{drift};--size:{size}">🌸</span>'
    for x, duration, delay, drift, size in PETALS
)
st.markdown(f'<div class="petal-field" aria-hidden="true">{petal_markup}</div>', unsafe_allow_html=True)


@st.cache_data(show_spinner=False)
def load_words():
    path = Path(__file__).with_name("vocabulary.csv")
    df = pd.read_csv(path, dtype=str, encoding="utf-8-sig").fillna("")
    required = {"Word", "Level", "Korean meaning (뜻)"}
    if not required.issubset(df.columns):
        raise ValueError(f"CSV에 필요한 열이 없습니다: {required - set(df.columns)}")
    return df[df["Word"].str.strip().ne("") & df["Korean meaning (뜻)"].str.strip().ne("")].copy()


def norm(value):
    return unicodedata.normalize("NFKC", str(value)).casefold().strip()


def meaning_ok(answer, meaning):
    variants = [meaning] + re.split(r"[,;/、]", meaning)
    return norm(answer) in {norm(v) for v in variants if v.strip()}


def target_words(passage):
    return [w for sentence, _ in passage["sentences"] for w in re.findall(r"\{\{([A-Za-z-]+)\}\}", sentence)]


def full_sentence(sentence):
    return re.sub(r"\{\{([A-Za-z-]+)\}\}", lambda m: m.group(1), sentence)


def initialize_pack(df, level):
    """Choose 20 words from the full CSV level, independently of Reading."""
    pool = df[df["Level"] == level].drop_duplicates(subset=["Word"])
    if len(pool) < 20:
        raise ValueError("선택한 수준의 단어가 20개 미만입니다.")
    selected = pool.sample(n=20)
    items = [
        {"word": row["Word"], "meaning": row["Korean meaning (뜻)"]}
        for _, row in selected.iterrows()
    ]
    st.session_state.update(
        pack=items, level=level, phase="Flashcards",
        card_idx=0, revealed=False, flash_seen=set(),
        quiz_idx=0, quiz_tries=0, quiz_done=False, quiz_results={},
        spelling_idx=0, spelling_tries=0, spelling_done=False, spelling_results={},
        input_version=st.session_state.get("input_version", 0) + 1,
    )


def initialize_reading(df, level, passage_idx):
    """Create a separate Reading session using curated words in the CSV."""
    passage = PASSAGES[level][passage_idx]
    targets = target_words(passage)
    if len(targets) != TARGET_COUNTS[level] or len(set(targets)) != len(targets):
        raise ValueError("지문의 목표 어휘 개수 또는 중복 설정이 올바르지 않습니다.")
    pool = df[df["Level"] == level].copy()
    pool["_key"] = pool["Word"].str.strip().str.casefold()
    reading_items = []
    for word in targets:
        matched = pool[pool["_key"] == word.casefold()]
        if matched.empty:
            raise ValueError(f"{LABELS[level]} CSV에서 '{word}'를 찾을 수 없습니다.")
        row = matched.iloc[0]
        reading_items.append({"word": row["Word"], "meaning": row["Korean meaning (뜻)"], "level": level})
    st.session_state.update(
        reading_items=reading_items, reading_level=level, reading_passage_idx=passage_idx,
        reading_idx=0, reading_tries=0, reading_done=False, reading_results={},
        reading_full_answers=False,
        input_version=st.session_state.get("input_version", 0) + 1,
        phase="Reading",
    )


def navigate(phase):
    st.session_state.phase = phase
    st.session_state.pop("_phase_choice", None)
    st.rerun()


@st.cache_data(show_spinner=False, max_entries=300)
def audio_bytes(text, accent="US"):
    buffer = io.BytesIO()
    gTTS(text=text, lang="en", tld="com" if accent == "US" else "co.uk").write_to_fp(buffer)
    return buffer.getvalue()


def audio_player(text, accent="US", label=None):
    if label:
        st.caption(label)
    try:
        st.audio(audio_bytes(text, accent), format="audio/mp3")
    except Exception:
        st.caption("음성을 불러올 수 없습니다. 인터넷 연결을 확인해 주세요.")


def related(word):
    syn, ant = RELATED.get(norm(word), ([], []))
    st.markdown("**🔎 유의어 · 반의어**")
    st.write("**유의어:** " + (", ".join(syn) if syn else "검증된 자료 없음"))
    st.write("**반의어:** " + (", ".join(ant) if ant else "검증된 자료 없음"))
    st.caption("의미가 다른 사전 항목이 섞이지 않도록 검토된 표현만 제공합니다.")


def diagnostic(df):
    st.subheader("🧭 어휘 수준 진단")
    st.caption("각 수준 5문항씩 총 15문항입니다. 공식 평가가 아닌 학습 수준 추천용입니다.")
    if "diag_questions" not in st.session_state:
        if st.button("15문항 진단 시작", type="primary"):
            rows = []
            for level in LEVELS.values():
                rows.extend(df[df["Level"] == level].sample(5).to_dict("records"))
            random.shuffle(rows)
            meanings = df["Korean meaning (뜻)"].drop_duplicates().tolist()
            questions = []
            for row in rows:
                answer = row["Korean meaning (뜻)"]
                choices = random.sample([x for x in meanings if x != answer], 3) + [answer]
                random.shuffle(choices)
                questions.append({"word": row["Word"], "answer": answer, "level": row["Level"], "choices": choices})
            st.session_state.diag_questions = questions
            st.session_state.diag_idx = 0
            st.session_state.diag_answers = {}
            st.rerun()
        return
    questions = st.session_state.diag_questions
    idx = st.session_state.diag_idx
    if idx == len(questions):
        scores = {level: 0 for level in LEVELS.values()}
        for i, q in enumerate(questions):
            scores[q["level"]] += int(st.session_state.diag_answers.get(i) == q["answer"])
        for level, score in scores.items():
            st.write(f"{LABELS[level]}: **{score}/5**")
        if scores["Extended"] >= 3 and scores["MidHigh"] >= 3:
            suggested = "Extended"
        elif scores["MidHigh"] >= 3:
            suggested = "MidHigh"
        else:
            suggested = "Elementary"
        st.success(f"추천 학습 수준: {LABELS[suggested]}")
        st.info("추천은 참고용입니다. 왼쪽 메뉴에서 1. 초등, 2. 중등, 3. 고등 중 원하는 수준을 직접 선택하세요.")
        if st.button("진단 다시 하기"):
            del st.session_state.diag_questions
            st.rerun()
        return
    q = questions[idx]
    st.progress((idx + 1) / len(questions), text=f"{idx + 1}/{len(questions)}")
    st.markdown(f"### {q['word']}")
    with st.form(f"diagnostic_{idx}"):
        choice = st.radio("한국어 뜻을 고르세요", q["choices"], index=None)
        submitted = st.form_submit_button("다음 문제 →", type="primary")
    if submitted:
        if choice is None:
            st.warning("답을 선택해 주세요.")
        else:
            st.session_state.diag_answers[idx] = choice
            st.session_state.diag_idx += 1
            st.rerun()


def answer_form(stage, index, prompt, answer, meaning, korean_answer=False):
    tries_key = f"{stage}_tries"
    done_key = f"{stage}_done"
    st.markdown(prompt)
    nickname = st.session_state.get("nickname", "학습자")
    if st.session_state[tries_key] == 1 and not st.session_state[done_key]:
        st.info(f"🌷 {nickname}님, 아직 한 번 더 기회가 있어요! 힌트를 보고 다시 도전해 봐요.")
        if korean_answer:
            st.warning(f"💡 힌트: 한국어 뜻의 첫 글자는 **{meaning[:1]}**입니다.")
        else:
            st.warning(f"💡 힌트: 첫 글자 **{answer[:1].upper()}**, 글자 수 **{len(answer)}**")
    if st.session_state[done_key]:
        mistakes = st.session_state[f"{stage}_results"][index]["mistakes"]
        if mistakes == 0:
            st.success("첫 번째 시도에 정답!")
        elif mistakes == 1:
            st.success(f"🌸 {nickname}님, 다시 도전해서 맞혔어요! Review에서도 복습해 봐요.")
        else:
            st.info(f"🌱 {nickname}님, 틀린 단어는 배울 기회예요. 정답을 확인하고 Review에서 다시 만나 봐요!")
        st.write(f"**정답:** {answer} — {meaning}")
        if st.button("다음 문제 →", key=f"next_{stage}_{index}", type="primary"):
            st.session_state[f"{stage}_idx"] += 1
            st.session_state[tries_key] = 0
            st.session_state[done_key] = False
            st.session_state.input_version += 1
            st.rerun()
        return
    with st.form(f"answer_{stage}_{index}_{st.session_state.input_version}"):
        response = st.text_input("정답 입력", autocomplete="off")
        submitted = st.form_submit_button("정답 확인", type="primary")
    if submitted:
        if not response.strip():
            st.warning("답을 입력해 주세요.")
            return
        correct = meaning_ok(response, meaning) if korean_answer else norm(response) == norm(answer)
        tries = st.session_state[tries_key]
        if correct or tries == 1:
            st.session_state[f"{stage}_results"][index] = {"mistakes": tries if correct else 2}
            st.session_state[done_key] = True
        else:
            st.session_state[tries_key] = 1
        st.rerun()


def render_reading_sentence(number, english, korean, completed=0, first_blank=0, show_answers=False):
    """Display a sentence with its blanks, Korean translation, and US audio."""
    position = [first_blank]

    def replace(match):
        current = position[0]
        position[0] += 1
        if show_answers or current < completed:
            return f"<b>{html.escape(match.group(1))}</b>"
        return f'<span class="blank">[{current + 1}] ______</span>'

    shown = re.sub(r"\{\{([A-Za-z-]+)\}\}", replace, html.escape(english))
    st.markdown(
        f'<div class="sentence"><div class="english"><b>{number}.</b> {shown}</div>'
        f'<div class="translation">{html.escape(korean)}</div></div>',
        unsafe_allow_html=True,
    )
    audio_player(full_sentence(english), "US", f"🇺🇸 {number}번 문장 발음 듣기")


def reading_view(pack):
    passage = PASSAGES[st.session_state.reading_level][st.session_state.reading_passage_idx]
    sentences = passage["sentences"]
    targets = target_words(passage)
    idx = st.session_state.reading_idx
    st.subheader(f"✈️ 여행 독해 · {passage['title']}")
    st.caption("문장을 하나씩 읽고 해당 문장의 빈칸을 채워 보세요. 문장별 한국어 해석과 미국식 발음을 제공합니다. 발음을 들으면 정답이 들릴 수 있어요.")

    if idx < len(targets):
        st.progress((idx + 1) / len(targets), text=f"빈칸 {idx + 1}/{len(targets)}")
        # Find the sentence containing the current blank. Multiple blanks in
        # one sentence are answered consecutively before advancing.
        first_blank = 0
        for number, (english, korean) in enumerate(sentences, 1):
            sentence_count = len(re.findall(r"\{\{([A-Za-z-]+)\}\}", english))
            if first_blank <= idx < first_blank + sentence_count:
                st.caption(f"문장 {number} / {len(sentences)}")
                render_reading_sentence(number, english, korean, idx, first_blank)
                break
            first_blank += sentence_count
        answer = targets[idx]
        item = next(x for x in st.session_state.reading_items if norm(x["word"]) == norm(answer))
        answer_form("reading", idx, f"**[{idx + 1}] 이 문장의 빈칸에 들어갈 영어 단어는?**", answer, item["meaning"])
        return

    # Completed reading: show the ENTIRE passage with blanks again, before Review.
    st.success("🎉 모든 문장의 빈칸을 완성했어요!")
    st.subheader("📖 전체 여행 지문 다시 보기")
    st.caption("전체 지문과 한국어 해석을 확인하세요. 처음에는 빈칸으로 표시되고, 정답 보기로 전환할 수 있어요.")
    show_answers = st.checkbox("전체 지문 정답 보기", key="reading_full_answers")
    first_blank = 0
    for number, (english, korean) in enumerate(sentences, 1):
        render_reading_sentence(number, english, korean, 0, first_blank, show_answers)
        first_blank += len(re.findall(r"\{\{([A-Za-z-]+)\}\}", english))
    if st.button("🔁 오답 Review로 이동 →", type="primary", use_container_width=True):
        navigate("Review")


def review_view(pack):
    st.subheader("🔁 오답 복습")
    wrong = {}
    for stage in ("quiz", "spelling"):
        for idx, result in st.session_state.get(f"{stage}_results", {}).items():
            if result["mistakes"] > 0 and idx < len(pack):
                item = pack[idx]
                wrong.setdefault(norm(item["word"]), {**item, "stages": set()})["stages"].add(stage)
    for idx, result in st.session_state.get("reading_results", {}).items():
        reading_items = st.session_state.get("reading_items", [])
        if result["mistakes"] > 0 and idx < len(reading_items):
            item = reading_items[idx]
            wrong.setdefault(norm(item["word"]), {**item, "stages": set()})["stages"].add("reading")
    if not wrong:
        st.success("지금까지 틀린 단어가 없어요!")
    else:
        st.metric("복습할 단어", len(wrong))
        for item in wrong.values():
            st.markdown(f"**{item['word']}** — {item['meaning']}")
            st.caption("오답 단계: " + ", ".join(sorted(item["stages"])))
            related(item["word"])
            st.divider()
    if pack and st.button("Flashcards로 돌아가기"):
        navigate("Flashcards")


try:
    words_df = load_words()
except Exception as exc:
    st.error(f"vocabulary.csv를 불러올 수 없습니다: {exc}")
    st.stop()

st.markdown('<div class="hero"><h1>🌸 Word Passport</h1><p>3,000개 단어 · 수준 진단 · 플래시카드 · 퀴즈 · 스펠링 · 여행 독해 · 리뷰</p></div>', unsafe_allow_html=True)

# The nickname is intentionally session-only: no account or personal data collection.
if not st.session_state.get("nickname"):
    st.subheader("🌷 나만의 Word Passport 만들기")
    st.write("처음 오셨군요! 학습할 때 불리고 싶은 별명을 입력해 주세요.")
    with st.form("nickname_welcome"):
        entered_nickname = st.text_input("별명", max_chars=20, placeholder="예: Cherry")
        start = st.form_submit_button("🌸 학습 시작하기", type="primary")
    if start:
        clean_nickname = entered_nickname.strip()
        if clean_nickname:
            st.session_state.nickname = clean_nickname
            st.rerun()
        else:
            st.warning("별명을 입력해 주세요.")
    st.stop()

st.caption(f"🌸 {st.session_state.nickname}님의 Word Passport에 오신 걸 환영해요!")
if "pack" not in st.session_state:
    st.session_state.pack = []
if "reading_items" not in st.session_state:
    st.session_state.reading_items = []
if "menu_page" not in st.session_state:
    st.session_state.menu_page = "🧭 수준 진단"

MENU = ["🧭 수준 진단", "1. 초등", "2. 중등", "3. 고등"]
with st.sidebar:
    st.title("🌸 Word Passport")
    st.caption(f"안녕하세요, {st.session_state.nickname}님!")
    with st.expander("별명 변경"):
        changed_nickname = st.text_input("새 별명", value=st.session_state.nickname, max_chars=20, key="new_nickname")
        if st.button("별명 저장"):
            if changed_nickname.strip():
                st.session_state.nickname = changed_nickname.strip()
                st.rerun()
            else:
                st.warning("별명을 입력해 주세요.")
    st.caption("학습 메뉴")
    selected_page = st.radio("이동할 페이지", MENU, key="menu_page", label_visibility="collapsed")
    st.divider()
    st.caption("수준 진단은 추천만 제공하며, 학습 수준은 직접 선택할 수 있습니다.")

if selected_page == "🧭 수준 진단":
    diagnostic(words_df)
    st.stop()

level_label = selected_page.split(". ", 1)[1]
selected_level = LEVELS[level_label]

# 다른 수준으로 이동하면 이전 수준의 학습 문제가 섞이지 않게 합니다.
if st.session_state.get("active_level") != selected_level:
    st.session_state.active_level = selected_level
    st.session_state.pack = []
    st.session_state.reading_items = []
    st.session_state.phase = "Flashcards"
    st.session_state.pop("_phase_choice", None)
    for stage in ("quiz", "spelling", "reading"):
        st.session_state[f"{stage}_results"] = {}
    st.session_state.pop("reading_full_answers", None)

st.header(f"{selected_page} 학습")
pool_count = words_df[words_df["Level"] == selected_level]["Word"].nunique()
st.caption(f"{level_label} 수준: CSV에 등록된 단어 {pool_count:,}개 · 플래시카드 20개씩 랜덤 학습")

# 학습은 Flashcards → Quiz → Spelling → Reading → Review 순서입니다.
# 여행 지문 단어는 전체 수준별 CSV에서 별도로 발췌합니다.
pack = st.session_state.pack
count = len(pack)
if not pack:
    st.info("먼저 아래 버튼을 눌러 이 수준의 단어 20개를 무작위로 뽑아 주세요.")
    if st.button("🎲 랜덤 20개 학습 시작", type="primary", use_container_width=True):
        try:
            initialize_pack(words_df, selected_level)
            st.rerun()
        except ValueError as exc:
            st.error(str(exc))
    st.stop()

st.caption("학습 순서: ① Flashcards → ② Quiz → ③ Spelling → ④ Reading → ⑤ Review")
if st.button("🔄 이 수준에서 새 단어 20개 뽑기"):
    initialize_pack(words_df, selected_level)
    st.session_state.reading_items = []
    st.session_state.reading_results = {}
    st.session_state.pop("reading_full_answers", None)
    st.rerun()

phases = ["Flashcards", "Quiz", "Spelling", "Reading", "Review"]
phase = st.session_state.get("phase", "Flashcards")
if phase not in phases:
    phase = "Flashcards"
    st.session_state.phase = phase

# 단계는 진행 표시로 보여 주고, 이동은 학습 화면 하단 버튼으로 합니다.
step = phases.index(phase)
step_labels = ["① Flashcards", "② Quiz", "③ Spelling", "④ Reading", "⑤ Review"]
st.markdown(
    '<div class="step-track">' + ''.join(
        f'<div class="step-pill {"active" if i == step else "done" if i < step else "future"}">{label}</div>'
        for i, label in enumerate(step_labels)
    ) + '</div>',
    unsafe_allow_html=True,
)
st.progress((step + 1) / len(phases), text=f"학습 여정 {step + 1}/5 · {phase}")

# 이전에 공부한 단계로 돌아갈 수 있습니다. Review도 언제든 확인할 수 있습니다.
with st.expander("📖 이전 단계 복습 / 오답 Review 바로가기"):
    if st.button("🔁 오답 Review 열기", key="review_shortcut"):
        navigate("Review")
    for old in phases[:step]:
        if st.button(f"↩ {old} 다시 보기", key=f"back_{old}"):
            navigate(old)
    if phase == "Review":
        for old in phases[:-1]:
            if st.button(f"↩ {old} 복습", key=f"review_back_{old}"):
                navigate(old)

if phase == "Reading":
    if not st.session_state.reading_items:
        st.subheader("✈️ 여행 지문 선택")
        st.caption("여행 지문은 3,000개 CSV에서 해당 수준에 맞는 단어를 별도로 선정했습니다. 랜덤 플래시카드 20개와는 독립적입니다.")
        passage_names = [p["title"] for p in PASSAGES[selected_level]]
        passage_name = st.selectbox("읽을 여행 지문", passage_names, key=f"passage_{selected_level}")
        passage_idx = passage_names.index(passage_name)
        passage = PASSAGES[selected_level][passage_idx]
        st.caption(f"{len(passage['sentences'])}문장 · 빈칸 {TARGET_COUNTS[selected_level]}개")
        if st.button("✈️ 여행 지문 시작", type="primary"):
            try:
                initialize_reading(words_df, selected_level, passage_idx)
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))
        st.stop()
    if st.button("다른 여행 지문 선택"):
        st.session_state.reading_items = []
        st.session_state.reading_results = {}
        st.session_state.pop("reading_full_answers", None)
        st.rerun()

if phase == "Flashcards":
    idx = st.session_state.card_idx
    st.session_state.setdefault("flash_seen", set()).add(idx)
    item = pack[idx]
    st.progress((idx + 1) / count, text=f"Flashcard {idx + 1}/{count}")
    word = html.escape(item["word"])
    meaning = html.escape(item["meaning"])
    if st.session_state.revealed:
        st.markdown(f'<div class="flash"><div class="word">{word}</div><hr><div class="meaning">{meaning}</div></div>', unsafe_allow_html=True)
        st.markdown("**🔊 단어 발음**")
        us, uk = st.columns(2)
        with us:
            audio_player(item["word"], "US", "🇺🇸 미국식")
        with uk:
            audio_player(item["word"], "GB", "🇬🇧 영국식")
        related(item["word"])
    else:
        st.markdown(f'<div class="flash"><div class="word">{word}</div><p>뜻을 생각해 보세요.</p></div>', unsafe_allow_html=True)
    if st.button("뜻 숨기기" if st.session_state.revealed else "👀 뜻 확인하기", use_container_width=True):
        st.session_state.revealed = not st.session_state.revealed
        st.rerun()
    a, b = st.columns(2)
    with a:
        if st.button("← 이전", disabled=idx == 0, use_container_width=True):
            st.session_state.card_idx -= 1
            st.session_state.revealed = False
            st.rerun()
    with b:
        if st.button("다음 →", disabled=idx == count - 1, use_container_width=True):
            st.session_state.card_idx += 1
            st.session_state.revealed = False
            st.rerun()
    viewed = len(st.session_state.flash_seen)
    st.caption(f"살펴본 카드: {viewed}/{count}개")
    if viewed == count:
        st.success(f"🌸 {st.session_state.nickname}님, 단어 {count}개를 모두 살펴봤어요! 이제 기억나는 단어를 확인해 볼까요? 틀려도 괜찮아요.")
        if st.button("🌷 Quiz 시작하기 →", type="primary", use_container_width=True):
            navigate("Quiz")
    else:
        st.info("🌱 카드를 모두 살펴보면 Quiz 시작 버튼이 나타나요. 이전 카드는 언제든 다시 볼 수 있어요.")

elif phase == "Quiz":
    idx = st.session_state.quiz_idx
    if idx == count:
        st.success("Quiz 완료!")
        st.metric("첫 시도 정답", f'{sum(v["mistakes"] == 0 for v in st.session_state.quiz_results.values())}/{count}')
        if st.button("다음 단계: Spelling →"):
            navigate("Spelling")
    else:
        item = pack[idx]
        st.progress((idx + 1) / count, text=f"Quiz {idx + 1}/{count}")
        if idx % 2 == 0:
            answer_form("quiz", idx, f'### {item["word"]}\n한국어 뜻을 입력하세요.', item["meaning"], item["meaning"], korean_answer=True)
        else:
            answer_form("quiz", idx, f'### {item["meaning"]}\n영어 단어를 입력하세요.', item["word"], item["meaning"])

elif phase == "Spelling":
    idx = st.session_state.spelling_idx
    if idx == count:
        st.success("철자 연습 완료!")
        if st.button("다음 단계: Reading →"):
            navigate("Reading")
    else:
        item = pack[idx]
        st.progress((idx + 1) / count, text=f"Spelling {idx + 1}/{count}")
        answer_form("spelling", idx, f'### {item["meaning"]}\n영어 철자를 입력하세요.', item["word"], item["meaning"])

elif phase == "Reading":
    reading_view(pack)

else:
    review_view(pack)

st.divider()
st.caption("Word Passport · 3,000개 CSV 단어 기반 · 학습 기록은 현재 브라우저 세션에만 유지됩니다.")
