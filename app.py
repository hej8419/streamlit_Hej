
"""Word Passport — vocabulary learning and travel reading.
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

st.set_page_config(
    page_title="Word Passport",
    page_icon="📚",
    layout="centered"
)

# 화면에는 초등·중등·고등으로 표시합니다.
# CSV 내부의 Level 값은 변경하지 않습니다.
LEVELS = {
    "초등": "Elementary",
    "중등": "MidHigh",
    "고등": "Extended"
}

LABELS = {value: key for key, value in LEVELS.items()}

TARGET_COUNTS = {
    "Elementary": 5,
    "MidHigh": 8,
    "Extended": 12
}

# 검토된 유의어와 반의어
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

# 여행 지문은 플래시카드와 별도로 운영합니다.
# {{word}} 형태는 빈칸으로 출제할 목표 어휘입니다.

PASSAGES = {
    "Elementary": [
        {
            "title": "공항으로 가는 길",
            "sentences": [
                (
                    "I have a {{ticket}} and a {{bag}}.",
                    "나는 표와 가방을 가지고 있다."
                ),
                (
                    "I take a {{bus}} with my mom.",
                    "나는 엄마와 버스를 탄다."
                ),
                (
                    "We look at a {{map}}.",
                    "우리는 지도를 본다."
                ),
                (
                    "We {{arrive}} early.",
                    "우리는 일찍 도착한다."
                ),
            ]
        },
        {
            "title": "바닷가 여행",
            "sentences": [
                (
                    "We go to the {{beach}}.",
                    "우리는 해변에 간다."
                ),
                (
                    "I bring some {{water}}.",
                    "나는 물을 조금 가져간다."
                ),
                (
                    "We play with a {{ball}}.",
                    "우리는 공을 가지고 논다."
                ),
                (
                    "I eat an {{apple}}.",
                    "나는 사과를 먹는다."
                ),
                (
                    "I take a {{picture}}.",
                    "나는 사진을 찍는다."
                ),
            ]
        },
        {
            "title": "기차 여행",
            "sentences": [
                (
                    "I buy a {{ticket}}.",
                    "나는 표를 산다."
                ),
                (
                    "I take the {{train}}.",
                    "나는 기차를 탄다."
                ),
                (
                    "I look out the {{window}}.",
                    "나는 창밖을 본다."
                ),
                (
                    "I {{visit}} my friend.",
                    "나는 친구를 방문한다."
                ),
                (
                    "We eat {{lunch}} together.",
                    "우리는 함께 점심을 먹는다."
                ),
            ]
        },
    ],

    "MidHigh": [
        {
            "title": "공항에서 생긴 일",
            "sentences": [
                (
                    "Our {{flight}} was delayed because of heavy rain.",
                    "폭우 때문에 우리 비행기가 지연되었다."
                ),
                (
                    "We waited at the {{airport}} for an update.",
                    "우리는 새 소식을 기다리며 공항에 있었다."
                ),
                (
                    "An employee explained the reason for the {{delay}}.",
                    "직원이 지연 사유를 설명했다."
                ),
                (
                    "She told us to check the new {{schedule}}.",
                    "그녀는 새 일정을 확인하라고 말했다."
                ),
                (
                    "Our boarding {{gate}} had also changed.",
                    "탑승구도 바뀌었다."
                ),
                (
                    "We needed to {{confirm}} the departure time.",
                    "우리는 출발 시간을 확인해야 했다."
                ),
                (
                    "A staff member helped us find the correct {{document}}.",
                    "직원이 올바른 서류를 찾도록 도와주었다."
                ),
                (
                    "We finally reached our {{hotel}} late at night.",
                    "우리는 마침내 밤늦게 호텔에 도착했다."
                ),
            ]
        },
        {
            "title": "호텔 체크인",
            "sentences": [
                (
                    "Before our trip, I called the {{hotel}}.",
                    "여행 전에 나는 호텔에 전화했다."
                ),
                (
                    "I wanted to {{reserve}} a room for two nights.",
                    "나는 이틀 밤 묵을 객실을 예약하고 싶었다."
                ),
                (
                    "The employee asked me to {{confirm}} my name.",
                    "직원은 내 이름을 확인해 달라고 했다."
                ),
                (
                    "She showed me the daily {{schedule}}.",
                    "그녀는 일일 일정을 보여주었다."
                ),
                (
                    "She also offered to {{recommend}} a restaurant.",
                    "그녀는 식당을 추천해 주겠다고도 했다."
                ),
                (
                    "We asked a {{local}} person for directions.",
                    "우리는 현지인에게 길을 물었다."
                ),
                (
                    "Our {{guide}} helped us explore the area.",
                    "우리 안내원이 주변을 둘러보도록 도와주었다."
                ),
                (
                    "It was a pleasant {{experience}}.",
                    "그것은 즐거운 경험이었다."
                ),
            ]
        },
        {
            "title": "박물관 관광",
            "sentences": [
                (
                    "We visited a famous {{museum}} on our trip.",
                    "우리는 여행 중 유명한 박물관을 방문했다."
                ),
                (
                    "Our {{guide}} welcomed us at the entrance.",
                    "안내원이 입구에서 우리를 맞이했다."
                ),
                (
                    "She explained the city's {{past}}.",
                    "그녀는 도시의 오랜 역사를 설명했다."
                ),
                (
                    "We learned about {{foreign}} visitors from the past.",
                    "우리는 과거의 외국인 방문객에 대해 배웠다."
                ),
                (
                    "A {{local}} artist's work was on display.",
                    "현지 예술가의 작품이 전시되어 있었다."
                ),
                (
                    "The tour was a valuable {{experience}}.",
                    "그 관광은 값진 경험이었다."
                ),
                (
                    "We continued our {{journey}} after lunch.",
                    "우리는 점심 식사 후 여행을 계속했다."
                ),
                (
                    "We stayed within our travel {{budget}}.",
                    "우리는 여행 예산을 지켰다."
                ),
            ]
        },
    ],

    "Extended": [
        {
            "title": "해외여행 준비",
            "sentences": [
                (
                    "Before departure, I checked whether my {{passport}} was still {{valid}}.",
                    "출발 전에 나는 여권이 여전히 유효한지 확인했다."
                ),
                (
                    "I tried to {{anticipate}} problems that might occur abroad.",
                    "나는 해외에서 발생할 수 있는 문제를 예상하려고 했다."
                ),
                (
                    "I prepared an {{adequate}} amount of money for emergencies.",
                    "나는 비상시에 쓸 충분한 돈을 준비했다."
                ),
                (
                    "I compared the {{currency}} rates before exchanging cash.",
                    "현금을 환전하기 전에 환율을 비교했다."
                ),
                (
                    "I wanted to be {{flexible}} if my plans changed.",
                    "계획이 바뀌더라도 유연하게 대처하고 싶었다."
                ),
                (
                    "The airline provided {{efficient}} online check-in services.",
                    "항공사는 효율적인 온라인 체크인 서비스를 제공했다."
                ),
                (
                    "Every {{passenger}} needed to bring the correct documents.",
                    "모든 승객은 올바른 서류를 가져와야 했다."
                ),
                (
                    "I hoped to {{explore}} new places during the trip.",
                    "나는 여행 중 새로운 장소를 탐험하고 싶었다."
                ),
                (
                    "I expected to encounter {{diverse}} traditions.",
                    "나는 다양한 전통을 접할 것으로 기대했다."
                ),
                (
                    "I wanted to {{interpret}} unfamiliar customs respectfully.",
                    "나는 낯선 관습을 존중하며 이해하고 싶었다."
                ),
                (
                    "Travel can change a person's {{perspective}}.",
                    "여행은 사람의 관점을 바꿀 수 있다."
                ),
                (
                    "Careful preparation helped me feel confident.",
                    "철저한 준비 덕분에 자신감이 생겼다."
                ),
            ]
        },
        {
            "title": "예상치 못한 호텔 문제",
            "sentences": [
                (
                    "The hotel could not {{accommodate}} our entire group.",
                    "호텔은 우리 일행 전체를 수용할 수 없었다."
                ),
                (
                    "We had to {{negotiate}} with the manager.",
                    "우리는 관리자와 협상해야 했다."
                ),
                (
                    "She offered to {{compensate}} us for the inconvenience.",
                    "그녀는 불편에 대한 보상을 제안했다."
                ),
                (
                    "We remained {{flexible}} and considered other options.",
                    "우리는 유연하게 대처하며 다른 선택지를 고려했다."
                ),
                (
                    "The manager suggested an {{adequate}} replacement room.",
                    "관리자는 충분히 적절한 대체 객실을 제안했다."
                ),
                (
                    "We needed a {{valid}} booking confirmation.",
                    "우리는 유효한 예약 확인서가 필요했다."
                ),
                (
                    "We tried to {{anticipate}} additional difficulties.",
                    "우리는 추가적인 어려움을 예상하려고 했다."
                ),
                (
                    "The staff found an {{efficient}} solution.",
                    "직원들은 효율적인 해결책을 찾았다."
                ),
                (
                    "We decided to {{explore}} the neighborhood while waiting.",
                    "기다리는 동안 우리는 주변 지역을 둘러보기로 했다."
                ),
                (
                    "The city had {{diverse}} places to eat.",
                    "그 도시에는 다양한 식당이 있었다."
                ),
                (
                    "The experience changed our {{perspective}} on travel.",
                    "그 경험은 여행에 대한 우리의 관점을 바꾸었다."
                ),
                (
                    "We learned to {{interpret}} unexpected events more calmly.",
                    "우리는 예상치 못한 일을 더 차분하게 받아들이는 법을 배웠다."
                ),
            ]
        },
        {
            "title": "다양한 문화를 만나는 여행",
            "sentences": [
                (
                    "We planned to {{explore}} a city with diverse traditions.",
                    "우리는 다양한 전통을 지닌 도시를 탐험할 계획이었다."
                ),
                (
                    "Our {{perspective}} changed as we met new people.",
                    "새로운 사람들을 만나면서 우리의 관점이 달라졌다."
                ),
                (
                    "A guide helped us {{interpret}} unfamiliar customs.",
                    "안내원은 낯선 관습을 이해하도록 도와주었다."
                ),
                (
                    "We tried to {{anticipate}} cultural differences.",
                    "우리는 문화적 차이를 미리 예상하려고 했다."
                ),
                (
                    "We kept our plans {{flexible}}.",
                    "우리는 계획을 유연하게 유지했다."
                ),
                (
                    "An {{adequate}} travel budget helped us relax.",
                    "충분한 여행 예산 덕분에 여유를 가질 수 있었다."
                ),
                (
                    "We exchanged our {{currency}} before visiting the market.",
                    "시장에 가기 전에 화폐를 환전했다."
                ),
                (
                    "We made sure our {{passport}} was secure.",
                    "우리는 여권을 안전하게 보관했다."
                ),
                (
                    "Our tickets remained {{valid}} throughout the trip.",
                    "여행 내내 우리 표는 유효했다."
                ),
                (
                    "We chose an {{efficient}} transportation option.",
                    "우리는 효율적인 교통수단을 선택했다."
                ),
                (
                    "Each {{passenger}} followed the guide's instructions.",
                    "각 승객은 안내원의 지시를 따랐다."
                ),
                (
                    "When a problem arose, we learned to {{negotiate}} politely.",
                    "문제가 생겼을 때 우리는 정중하게 협상하는 법을 배웠다."
                ),
            ]
        },
    ],
}

# 디자인
st.markdown(
    """
    <style>
    .block-container {
        max-width: 880px;
        padding-top: 1.4rem;
        padding-bottom: 3rem;
    }
    .hero {
        background: #193b59;
        color: #fff;
        border-radius: 18px;
        padding: 22px;
        margin-bottom: 18px;
    }
    .hero h1 {
        color: #fff;
        margin: 0;
    }
    .hero p {
        color: #d8e9f7;
        margin: 8px 0 0;
    }
    .flash {
        background: #f5f8fd;
        color: #17283e;
        border-radius: 20px;
        padding: 30px 18px;
        text-align: center;
        margin: 15px 0;
    }
    .word {
        font-size: clamp(32px, 6vw, 56px);
        font-weight: 800;
        overflow-wrap: anywhere;
    }
    .meaning {
        font-size: clamp(20px, 4vw, 28px);
        font-weight: 650;
    }
    .sentence {
        border: 1px solid #8b98a8;
        border-radius: 12px;
        padding: 14px;
        margin: 10px 0;
    }
    .english {
        font-size: 1.1rem;
        line-height: 1.75;
    }
    .translation {
        color: #68798d;
        font-size: .94rem;
        margin-top: 5px;
    }
    .blank {
        color: #b45309;
        font-weight: 800;
    }
    </style>
    """,
    unsafe_allow_html=True
)


@st.cache_data(show_spinner=False)
def load_words():
    path = Path(__file__).with_name("vocabulary.csv")

    df = pd.read_csv(
        path,
        dtype=str,
        encoding="utf-8-sig"
    ).fillna("")

    required = {
        "Word",
        "Level",
        "Korean meaning (뜻)"
    }

    if not required.issubset(df.columns):
        raise ValueError(
            f"CSV에 필요한 열이 없습니다: {required - set(df.columns)}"
        )

    return df[
        df["Word"].str.strip().ne("")
        & df["Korean meaning (뜻)"].str.strip().ne("")
    ].copy()


def norm(value):
    return unicodedata.normalize(
        "NFKC",
        str(value)
    ).casefold().strip()


def meaning_ok(answer, meaning):
    variants = [meaning] + re.split(
        r"[,;/、]",
        meaning
    )

    return norm(answer) in {
        norm(v)
        for v in variants
        if v.strip()
    }


def target_words(passage):
    return [
        w
        for sentence, _ in passage["sentences"]
        for w in re.findall(
            r"\{\{([A-Za-z-]+)\}\}",
            sentence
        )
    ]


def full_sentence(sentence):
    return re.sub(
        r"\{\{([A-Za-z-]+)\}\}",
        lambda m: m.group(1),
        sentence
    )


def initialize_pack(df, level):
    """선택한 수준의 전체 CSV에서 20개 단어 추출"""

    pool = df[
        df["Level"] == level
    ].drop_duplicates(subset=["Word"])

    if len(pool) < 20:
        raise ValueError(
            "선택한 수준의 단어가 20개 미만입니다."
        )

    selected = pool.sample(n=20)

    items = [
        {
            "word": row["Word"],
            "meaning": row["Korean meaning (뜻)"]
        }
        for _, row in selected.iterrows()
    ]

    st.session_state.update(
        pack=items,
        level=level,
        phase="Flashcards",
        card_idx=0,
        revealed=False,
        quiz_idx=0,
        quiz_tries=0,
        quiz_done=False,
        quiz_results={},
        spelling_idx=0,
        spelling_tries=0,
        spelling_done=False,
        spelling_results={},
        input_version=(
            st.session_state.get("input_version", 0) + 1
        ),
    )


def initialize_reading(df, level, passage_idx):
    """여행 지문은 플래시카드와 독립적으로 시작"""

    passage = PASSAGES[level][passage_idx]
    targets = target_words(passage)

    if (
        len(targets) != TARGET_COUNTS[level]
        or len(set(targets)) != len(targets)
    ):
        raise ValueError(
            "지문의 목표 어휘 개수 또는 중복 설정이 올바르지 않습니다."
        )

    pool = df[df["Level"] == level].copy()
    pool["_key"] = (
        pool["Word"].str.strip().str.casefold()
    )

    reading_items = []

    for word in targets:
        matched = pool[
            pool["_key"] == word.casefold()
        ]

        if matched.empty:
            raise ValueError(
                f"{LABELS[level]} CSV에서 '{word}'를 찾을 수 없습니다."
            )

        row = matched.iloc[0]

        reading_items.append({
            "word": row["Word"],
            "meaning": row["Korean meaning (뜻)"],
            "level": level
        })

    st.session_state.update(
        reading_items=reading_items,
        reading_level=level,
        reading_passage_idx=passage_idx,
        reading_idx=0,
        reading_tries=0,
        reading_done=False,
        reading_results={},
        reading_full_answers=False,
        input_version=(
            st.session_state.get("input_version", 0) + 1
        ),
        phase="Reading",
    )


def navigate(phase):
    st.session_state.phase = phase
    st.rerun()


@st.cache_data(
    show_spinner=False,
    max_entries=300
)
def audio_bytes(text, accent="US"):
    buffer = io.BytesIO()

    gTTS(
        text=text,
        lang="en",
        tld="com" if accent == "US" else "co.uk"
    ).write_to_fp(buffer)

    return buffer.getvalue()


def audio_player(text, accent="US", label=None):
    if label:
        st.caption(label)

    try:
        st.audio(
            audio_bytes(text, accent),
            format="audio/mp3"
        )
    except Exception:
        st.caption(
            "음성을 불러올 수 없습니다. 인터넷 연결을 확인해 주세요."
        )


def related(word):
    syn, ant = RELATED.get(
        norm(word),
        ([], [])
    )

    st.markdown("**🔎 유의어 · 반의어**")

    st.write(
        "**유의어:** "
        + (", ".join(syn) if syn else "검증된 자료 없음")
    )

    st.write(
        "**반의어:** "
        + (", ".join(ant) if ant else "검증된 자료 없음")
    )

    st.caption(
        "의미가 다른 사전 항목이 섞이지 않도록 "
        "검토된 표현만 제공합니다."
    )


def diagnostic(df):
    st.subheader("🧭 어휘 수준 진단")

    st.caption(
        "각 수준 5문항씩 총 15문항입니다. "
        "공식 평가가 아닌 학습 수준 추천용입니다."
    )

    if "diag_questions" not in st.session_state:
        if st.button(
            "15문항 진단 시작",
            type="primary"
        ):
            rows = []

            for level in LEVELS.values():
                rows.extend(
                    df[
                        df["Level"] == level
                    ].sample(5).to_dict("records")
                )

            random.shuffle(rows)

            meanings = (
                df["Korean meaning (뜻)"]
                .drop_duplicates()
                .tolist()
            )

            questions = []

            for row in rows:
                answer = row["Korean meaning (뜻)"]

                choices = random.sample(
                    [
                        x for x in meanings
                        if x != answer
                    ],
                    3
                ) + [answer]

                random.shuffle(choices)

                questions.append({
                    "word": row["Word"],
                    "answer": answer,
                    "level": row["Level"],
                    "choices": choices
                })

            st.session_state.diag_questions = questions
            st.session_state.diag_idx = 0
            st.session_state.diag_answers = {}

            st.rerun()

        return

    questions = st.session_state.diag_questions
    idx = st.session_state.diag_idx

    if idx == len(questions):
        scores = {
            level: 0
            for level in LEVELS.values()
        }

        for i, q in enumerate(questions):
            scores[q["level"]] += int(
                st.session_state.diag_answers.get(i)
                == q["answer"]
            )

        for level, score in scores.items():
            st.write(
                f"{LABELS[level]}: **{score}/5**"
            )

        if (
            scores["Extended"] >= 3
            and scores["MidHigh"] >= 3
        ):
            suggested = "Extended"

        elif scores["MidHigh"] >= 3:
            suggested = "MidHigh"

        else:
            suggested = "Elementary"

        st.success(
            f"추천 학습 수준: {LABELS[suggested]}"
        )

        if st.button(
            "추천 수준으로 이동",
            type="primary"
        ):
            st.session_state.level_select = LABELS[suggested]
            st.session_state.show_diag = False
            st.rerun()

        if st.button("진단 다시 하기"):
            del st.session_state.diag_questions
            st.rerun()

        return

    q = questions[idx]

    st.progress(
        (idx + 1) / len(questions),
        text=f"{idx + 1}/{len(questions)}"
    )

    st.markdown(f"### {q['word']}")

    with st.form(f"diagnostic_{idx}"):
        choice = st.radio(
            "한국어 뜻을 고르세요",
            q["choices"],
            index=None
        )

        submitted = st.form_submit_button(
            "다음 문제 →",
            type="primary"
        )

    if submitted:
        if choice is None:
            st.warning("답을 선택해 주세요.")
        else:
            st.session_state.diag_answers[idx] = choice
            st.session_state.diag_idx += 1
            st.rerun()


def answer_form(
    stage,
    index,
    prompt,
    answer,
    meaning,
    korean_answer=False
):
    tries_key = f"{stage}_tries"
    done_key = f"{stage}_done"

    st.markdown(prompt)

    if (
        st.session_state[tries_key] == 1
        and not st.session_state[done_key]
    ):
        if korean_answer:
            st.warning(
                f"💡 힌트: 한국어 뜻의 첫 글자는 "
                f"**{meaning[:1]}**입니다."
            )
        else:
            st.warning(
                f"💡 힌트: 첫 글자 "
                f"**{answer[:1].upper()}**, "
                f"글자 수 **{len(answer)}**"
            )

    if st.session_state[done_key]:
        mistakes = st.session_state[
            f"{stage}_results"
        ][index]["mistakes"]

        if mistakes == 0:
            st.success("첫 번째 시도에 정답!")

        elif mistakes == 1:
            st.warning(
                "힌트 후 정답! Review에 추가되었습니다."
            )

        else:
            st.error(
                "두 번 틀렸습니다. Review에서 복습하세요."
            )

        st.write(
            f"**정답:** {answer} — {meaning}"
        )

        if st.button(
            "다음 문제 →",
            key=f"next_{stage}_{index}",
            type="primary"
        ):
            st.session_state[f"{stage}_idx"] += 1
            st.session_state[tries_key] = 0
            st.session_state[done_key] = False
            st.session_state.input_version += 1

            st.rerun()

        return

    with st.form(
        f"answer_{stage}_{index}_"
        f"{st.session_state.input_version}"
    ):
        response = st.text_input(
            "정답 입력",
            autocomplete="off"
        )

        submitted = st.form_submit_button(
            "정답 확인",
            type="primary"
        )

    if submitted:
        if not response.strip():
            st.warning("답을 입력해 주세요.")
            return

        if korean_answer:
            correct = meaning_ok(
                response,
                meaning
            )
        else:
            correct = (
                norm(response) == norm(answer)
            )

        tries = st.session_state[tries_key]

        if correct or tries == 1:
            st.session_state[
                f"{stage}_results"
            ][index] = {
                "mistakes": tries if correct else 2
            }

            st.session_state[done_key] = True

        else:
            st.session_state[tries_key] = 1

        st.rerun()


def render_reading_sentence(
    number,
    english,
    korean,
    completed=0,
    first_blank=0,
    show_answers=False
):
    """빈칸, 한국어 해석, 미국식 발음을 표시"""

    position = [first_blank]

    def replace(match):
        current = position[0]
        position[0] += 1

        if show_answers or current < completed:
            return (
                f"<b>{html.escape(match.group(1))}</b>"
            )

        return (
            f'<span class="blank">'
            f'[{current + 1}] ______'
            f'</span>'
        )

    shown = re.sub(
        r"\{\{([A-Za-z-]+)\}\}",
        replace,
        html.escape(english)
    )

    st.markdown(
        f'<div class="sentence">'
        f'<div class="english">'
        f'<b>{number}.</b> {shown}'
        f'</div>'
        f'<div class="translation">'
        f'{html.escape(korean)}'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True
    )

    audio_player(
        full_sentence(english),
        "US",
        f"🇺🇸 {number}번 문장 발음 듣기"
    )


def reading_view(pack):
    passage = PASSAGES[
        st.session_state.reading_level
    ][
        st.session_state.reading_passage_idx
    ]

    sentences = passage["sentences"]
    targets = target_words(passage)
    idx = st.session_state.reading_idx

    st.subheader(
        f"✈️ 여행 독해 · {passage['title']}"
    )

    st.caption(
        "문장을 하나씩 읽고 해당 문장의 빈칸을 채워 보세요. "
        "문장별 한국어 해석과 미국식 발음을 제공합니다. "
        "발음을 들으면 정답이 들릴 수 있어요."
    )

    if idx < len(targets):
        st.progress(
            (idx + 1) / len(targets),
            text=f"빈칸 {idx + 1}/{len(targets)}"
        )

        first_blank = 0

        for number, (english, korean) in enumerate(
            sentences,
            1
        ):
            sentence_count = len(
                re.findall(
                    r"\{\{([A-Za-z-]+)\}\}",
                    english
                )
            )

            if (
                first_blank <= idx
                < first_blank + sentence_count
            ):
                st.caption(
                    f"문장 {number} / {len(sentences)}"
                )

                render_reading_sentence(
                    number,
                    english,
                    korean,
                    idx,
                    first_blank
                )

                break

            first_blank += sentence_count

        answer = targets[idx]

        item = next(
            x
            for x in st.session_state.reading_items
            if norm(x["word"]) == norm(answer)
        )

        answer_form(
            "reading",
            idx,
            f"**[{idx + 1}] "
            f"이 문장의 빈칸에 들어갈 영어 단어는?**",
            answer,
            item["meaning"]
        )

        return

    # 모든 빈칸을 푼 다음 전체 지문 표시
    st.success(
        "🎉 모든 문장의 빈칸을 완성했어요!"
    )

    st.subheader(
        "📖 전체 여행 지문 다시 보기"
    )

    st.caption(
        "전체 지문과 한국어 해석을 확인하세요. "
        "처음에는 빈칸으로 표시되고, "
        "정답 보기로 전환할 수 있어요."
    )

    show_answers = st.checkbox(
        "전체 지문 정답 보기",
        key="reading_full_answers"
    )

    first_blank = 0

    for number, (english, korean) in enumerate(
        sentences,
        1
    ):
        render_reading_sentence(
            number,
            english,
            korean,
            0,
            first_blank,
            show_answers
        )

        first_blank += len(
            re.findall(
                r"\{\{([A-Za-z-]+)\}\}",
                english
            )
        )

    if st.button(
        "🔁 오답 Review로 이동 →",
        type="primary",
        use_container_width=True
    ):
        navigate("Review")


def review_view(pack):
    st.subheader("🔁 오답 복습")

    wrong = {}

    # Quiz와 Spelling 오답
    for stage in ("quiz", "spelling"):
        results = st.session_state.get(
            f"{stage}_results",
            {}
        )

        for idx, result in results.items():
            if (
                result["mistakes"] > 0
                and idx < len(pack)
            ):
                item = pack[idx]

                wrong.setdefault(
                    norm(item["word"]),
                    {
                        **item,
                        "stages": set()
                    }
                )["stages"].add(stage)

    # Reading 오답
    reading_items = st.session_state.get(
        "reading_items",
        []
    )

    for idx, result in st.session_state.get(
        "reading_results",
        {}
    ).items():
        if (
            result["mistakes"] > 0
            and idx < len(reading_items)
        ):
            item = reading_items[idx]

            wrong.setdefault(
                norm(item["word"]),
                {
                    **item,
                    "stages": set()
                }
            )["stages"].add("reading")

    if not wrong:
        st.success(
            "지금까지 틀린 단어가 없어요!"
        )

    else:
        st.metric(
            "복습할 단어",
            len(wrong)
        )

        for item in wrong.values():
            st.markdown(
                f"**{item['word']}** — "
                f"{item['meaning']}"
            )

            st.caption(
                "오답 단계: "
                + ", ".join(
                    sorted(item["stages"])
                )
            )

            related(item["word"])
            st.divider()

    if st.button(
        "Flashcards로 돌아가기"
    ):
        navigate("Flashcards")


# CSV 불러오기
try:
    words_df = load_words()

except Exception as exc:
    st.error(
        f"vocabulary.csv를 불러올 수 없습니다: {exc}"
    )
    st.stop()


# 메인 화면
st.markdown(
    '<div class="hero">'
    '<h1>📚 Word Passport</h1>'
    '<p>여행으로 배우는 영어 · '
    '수준 진단 · 플래시카드 · 독해 · 복습</p>'
    '</div>',
    unsafe_allow_html=True
)

if "pack" not in st.session_state:
    st.session_state.pack = []

if "show_diag" not in st.session_state:
    st.session_state.show_diag = False

if "reading_items" not in st.session_state:
    st.session_state.reading_items = []


# 사이드바
with st.sidebar:
    st.header("내 학습 현황")

    st.write(
        "현재 수준:",
        LABELS.get(
            st.session_state.get("level"),
            "미선택"
        )
    )

    st.write(
        "현재 랜덤 학습 단어:",
        len(st.session_state.pack),
        "개"
    )

    if st.button("🧭 수준 진단"):
        st.session_state.show_diag = True
        st.rerun()

    if st.button("📚 학습 화면"):
        st.session_state.show_diag = False
        st.rerun()


if st.session_state.show_diag:
    diagnostic(words_df)
    st.stop()


# 학습 수준 선택
level_label = st.selectbox(
    "🎓 학습 수준",
    list(LEVELS),
    key="level_select"
)

selected_level = LEVELS[level_label]


# 플래시카드 학습
st.subheader(
    "📚 단어 학습 — 전체 3,000개 단어 활용"
)

st.caption(
    "초등 800개 · 중등 1,200개 · 고등 1,000개. "
    "선택한 수준에서 20개를 무작위로 뽑습니다."
)

if st.button(
    "🎲 랜덤 20개 단어로 새 학습 시작",
    type="primary",
    use_container_width=True
):
    try:
        initialize_pack(
            words_df,
            selected_level
        )
        st.rerun()

    except ValueError as exc:
        st.error(str(exc))


st.divider()


# 여행 지문 선택
st.subheader(
    "✈️ 여행 독해 — 별도 학습"
)

st.caption(
    "여행 지문의 빈칸은 3,000개 CSV에서 "
    "수준별로 선정한 단어입니다. "
    "랜덤 플래시카드 20개와는 별개입니다."
)

passage_names = [
    p["title"]
    for p in PASSAGES[selected_level]
]

passage_name = st.selectbox(
    "여행 지문 선택",
    passage_names
)

selected_passage_idx = passage_names.index(
    passage_name
)

passage = PASSAGES[
    selected_level
][selected_passage_idx]

st.caption(
    f"{level_label}: "
    f"빈칸 {TARGET_COUNTS[selected_level]}개 · "
    f"지문 {len(passage['sentences'])}문장"
)

if st.button(
    "✈️ 선택한 여행 지문 학습 시작",
    use_container_width=True
):
    try:
        initialize_reading(
            words_df,
            selected_level,
            selected_passage_idx
        )
        st.rerun()

    except ValueError as exc:
        st.error(str(exc))


pack = st.session_state.pack
count = len(pack)

if (
    not pack
    and not st.session_state.get("reading_items")
):
    st.info(
        "랜덤 단어 학습 또는 여행 독해 중 "
        "원하는 활동을 시작해 주세요."
    )
    st.stop()


# 학습 단계
available_phases = [
    "Flashcards",
    "Quiz",
    "Spelling",
    "Reading",
    "Review"
]

if not pack:
    available_phases = [
        "Reading",
        "Review"
    ]

if not st.session_state.get("reading_items"):
    available_phases = [
        x for x in available_phases
        if x != "Reading"
    ]

if st.session_state.get("phase") not in available_phases:
    st.session_state.phase = available_phases[0]

phase = st.radio(
    "학습 단계",
    available_phases,
    horizontal=True,
    key="phase"
)


# Flashcards
if phase == "Flashcards":
    idx = st.session_state.card_idx
    item = pack[idx]

    st.progress(
        (idx + 1) / count,
        text=f"Flashcard {idx + 1}/{count}"
    )

    word = html.escape(item["word"])
    meaning = html.escape(item["meaning"])

    if st.session_state.revealed:
        st.markdown(
            f'<div class="flash">'
            f'<div class="word">{word}</div>'
            f'<hr>'
            f'<div class="meaning">{meaning}</div>'
            f'</div>',
            unsafe_allow_html=True
        )

        st.markdown("**🔊 단어 발음**")

        us, uk = st.columns(2)

        with us:
            audio_player(
                item["word"],
                "US",
                "🇺🇸 미국식"
            )

        with uk:
            audio_player(
                item["word"],
                "GB",
                "🇬🇧 영국식"
            )

        related(item["word"])

    else:
        st.markdown(
            f'<div class="flash">'
            f'<div class="word">{word}</div>'
            f'<p>뜻을 생각해 보세요.</p>'
            f'</div>',
            unsafe_allow_html=True
        )

    if st.button(
        "뜻 숨기기"
        if st.session_state.revealed
        else "👀 뜻 확인하기",
        use_container_width=True
    ):
        st.session_state.revealed = (
            not st.session_state.revealed
        )
        st.rerun()

    a, b = st.columns(2)

    with a:
        if st.button(
            "← 이전",
            disabled=idx == 0,
            use_container_width=True
        ):
            st.session_state.card_idx -= 1
            st.session_state.revealed = False
            st.rerun()

    with b:
        if st.button(
            "다음 →",
            disabled=idx == count - 1,
            use_container_width=True
        ):
            st.session_state.card_idx += 1
            st.session_state.revealed = False
            st.rerun()

    if st.session_state.get("reading_items"):
        if st.button(
            "✈️ 여행 지문 풀기",
            type="primary",
            use_container_width=True
        ):
            navigate("Reading")


# Quiz
elif phase == "Quiz":
    idx = st.session_state.quiz_idx

    if idx == count:
        st.success("Quiz 완료!")

        correct_count = sum(
            v["mistakes"] == 0
            for v in st.session_state.quiz_results.values()
        )

        st.metric(
            "첫 시도 정답",
            f"{correct_count}/{count}"
        )

        if st.button("오답 복습하기"):
            navigate("Review")

    else:
        item = pack[idx]

        st.progress(
            (idx + 1) / count,
            text=f"Quiz {idx + 1}/{count}"
        )

        if idx % 2 == 0:
            answer_form(
                "quiz",
                idx,
                f"### {item['word']}\n"
                f"한국어 뜻을 입력하세요.",
                item["meaning"],
                item["meaning"],
                korean_answer=True
            )

        else:
            answer_form(
                "quiz",
                idx,
                f"### {item['meaning']}\n"
                f"영어 단어를 입력하세요.",
                item["word"],
                item["meaning"]
            )


# Spelling
elif phase == "Spelling":
    idx = st.session_state.spelling_idx

    if idx == count:
        st.success("철자 연습 완료!")

        if st.button("오답 복습하기"):
            navigate("Review")

    else:
        item = pack[idx]

        st.progress(
            (idx + 1) / count,
            text=f"Spelling {idx + 1}/{count}"
        )

        answer_form(
            "spelling",
            idx,
            f"### {item['meaning']}\n"
            f"영어 철자를 입력하세요.",
            item["word"],
            item["meaning"]
        )


# Reading
elif phase == "Reading":
    reading_view(pack)


# Review
else:
    review_view(pack)


st.divider()

st.caption(
    "Word Passport · 3,000개 CSV 단어 기반 · "
    "학습 기록은 현재 브라우저 세션에만 유지됩니다."
)
