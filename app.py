"""Fishbone learning app. Requires the existing data/scenarios.json file."""
import html
import json
import math
import random
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Fishbone Learning Tool", layout="wide")
ROOT = Path(__file__).resolve().parent
try:
    scenario = json.loads((ROOT / "data" / "scenarios.json").read_text(encoding="utf-8"))
except (OSError, json.JSONDecodeError):
    st.error("Cannot read data/scenarios.json. Keep that file inside the data folder.")
    st.stop()

ALL_CAUSES = scenario["causes"]
BONES = scenario["bones"]
LOOKUP = {c["id"]: c for c in ALL_CAUSES}
LABELS = {c["id"]: f"C{i}" for i, c in enumerate(ALL_CAUSES, 1)}
EFFECT = scenario["effect"]
DEFINITIONS = {
    "People": "People's knowledge, actions, communication, and perceived impartiality.",
    "Procedure": "The steps and methods used to carry out the work.",
    "Systems": "The systems and information channels supporting the process.",
    "Policy": "Rules and guidelines governing decisions and exceptions.",
    "Environment": "External or surrounding conditions affecting the process.",
    "Equipment": "Usually tools and devices. This example also places document-related issues here.",
}
SUBCAUSES = [s for s in scenario.get("sub_causes", []) if s["parent_id"] in LOOKUP]
SUBLABELS = {s["id"]: f"S{i}" for i, s in enumerate(SUBCAUSES, 1)}
PARTS = {
    "effect": {
        "heading": "Effect: the problem being investigated",
        "text": EFFECT,
        "detail": "This is the outcome we want to explain, not a cause. The causes on the bones are possible explanations for customer dissatisfaction.",
    }
}
for bone in BONES:
    PARTS[f"bone_{bone}"] = {
        "heading": f"{bone}: main category",
        "text": DEFINITIONS.get(bone, "A category for organizing possible causes."),
        "detail": "A category groups related causes; it is not itself a confirmed root cause.",
    }
for c in ALL_CAUSES:
    PARTS[c["id"]] = {
        "heading": f"{LABELS[c['id']]} | {c['correct_bone']} | Possible cause",
        "text": c["text"],
        "detail": c["hint"],
    }
for s in SUBCAUSES:
    parent = LOOKUP[s["parent_id"]]
    PARTS[s["id"]] = {
        "heading": f"{SUBLABELS[s['id']]} | {parent['correct_bone']} | Smaller branch",
        "text": s["text"],
        "detail": (
            f"Connected to {LABELS[parent['id']]}: {parent['text']} "
            "It belongs to that cause's branch, not directly to the main spine. "
            "The source diagram shows this connection; confirm its intended causal direction with the professor."
        ),
    }


def fishbone(selected_ids=None, votes=None):
    """Fixed positions: vote counts change emphasis, never category assignment."""
    mini = votes is not None
    chosen = set(LOOKUP if selected_ids is None else selected_ids)
    fig = go.Figure()
    fig.add_shape(type="line", x0=0, y0=0, x1=14, y1=0,
                  line=dict(color="#CBD5E1", width=3))

    def node(node_id, x, y, text, color, size=17, position="top center"):
        info = PARTS[node_id]
        extra = f" | {votes.get(node_id, 0)} voting points" if mini and node_id in LOOKUP else ""
        fig.add_trace(go.Scatter(
            x=[x], y=[y], mode="markers+text", text=[text],
            textposition=position, textfont=dict(size=11 if mini else 13),
            marker=dict(size=size, color=color, line=dict(width=1, color="#CBD5E1")),
            customdata=[node_id],
            hovertext=[html.escape(info["heading"] + extra) + "<br>" + html.escape(info["text"])],
            hoverinfo="text", showlegend=False,
        ))

    positions = [(3, 1), (7, 1), (11, 1), (3, -1), (7, -1), (11, -1)]
    cause_positions = {}
    for bone, (base, direction) in zip(BONES, positions):
        fig.add_shape(type="line", x0=base, y0=0, x1=base-2, y1=direction*3,
                      line=dict(color="#38BDF8", width=2))
        node(f"bone_{bone}", base-2, direction*3, bone, "#0284C7", 14,
             "top center" if direction > 0 else "bottom center")
        members = [c for c in ALL_CAUSES if c["correct_bone"] == bone]
        for i, c in enumerate(members):
            # Coordinates use all members so the layout is stable in both views.
            fraction = (i+1) / (len(members)+1)
            x, y = base-2*fraction, direction*3*fraction
            if c["id"] not in chosen:
                continue
            cx = x + 0.9
            cause_positions[c["id"]] = (cx, y)
            fig.add_shape(type="line", x0=x, y0=y, x1=cx, y1=y,
                          line=dict(color="#5EEAD4", width=1.5))
            count = votes.get(c["id"], 0) if mini else 0
            color = ("#14B8A6" if count else "#64748B") if mini else "#0D9488"
            size = (10 if count == 0 else 16 + 10*math.sqrt(count)) if mini else 18
            label = f"{LABELS[c['id']]}: {count}" if mini else LABELS[c["id"]]
            node(c["id"], cx, y, label, color, size)

    for s in SUBCAUSES:
        if s["parent_id"] in cause_positions:
            px, py = cause_positions[s["parent_id"]]
            sx, sy = px+0.7, py-0.8
            fig.add_shape(type="line", x0=px, y0=py, x1=sx, y1=sy,
                          line=dict(color="#C084FC", width=2))
            node(s["id"], sx, sy, SUBLABELS[s["id"]], "#9333EA", 13)
    node("effect", 14, 0, "Customer<br>dissatisfaction", "#F97316", 25, "bottom center")
    fig.update_layout(
        height=410 if mini else 570,
        margin=dict(l=15, r=20, t=35, b=35),
        xaxis=dict(visible=False, range=[-0.2, 15.5], fixedrange=True),
        yaxis=dict(visible=False, range=[-4, 4], fixedrange=True),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#E2E8F0"), clickmode="event+select", dragmode=False,
    )
    return fig


def selected_id(event):
    points = event.selection.points
    if not points:
        return None
    value = points[0].get("customdata")
    return value[0] if isinstance(value, (list, tuple)) else value


def part_panel(part_id):
    info = PARTS.get(part_id, PARTS["effect"])
    st.markdown(f"**{info['heading']}**")
    st.write(info["text"])
    st.write(info["detail"])


def reset_practice():
    for key in list(st.session_state):
        if key.startswith(("answer_", "feedback_", "vote_")) or key == "card_order":
            del st.session_state[key]


saved = st.session_state.get("card_order", [])
if len(saved) != min(5, len(LOOKUP)) or not set(saved).issubset(LOOKUP):
    st.session_state.card_order = random.sample(list(LOOKUP), min(5, len(LOOKUP)))
PRACTICE = [LOOKUP[cid] for cid in st.session_state.card_order]

st.title("Fishbone Learning Tool")
st.subheader(scenario["title"])
st.info(f"Problem / effect: {EFFECT}")
st.write(
    "When a customer returns a financed vehicle, information about its condition, "
    "wear charges, and residual value can affect customer satisfaction. This fishbone "
    "organizes possible reasons for dissatisfaction in that return process."
)
with st.expander("Key terms"):
    st.write("**Residual value:** the estimated value of the vehicle at the end of the agreement.")
    st.write("**Return protocol:** the return report documenting vehicle condition and damage.")
    st.write("**SF:** an abbreviation in the source diagram; its full meaning is not specified.")

st.markdown("""
<style>
.activity-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 16px;
    margin: 16px 0 24px;
}
.activity-card {
    background: #171717;
    border: 1px solid #3A2525;
    border-top: 4px solid #EF4444;
    border-radius: 12px;
    padding: 20px;
}
.activity-title {
    color: #F87171;
    font-size: 22px;
    font-weight: 700;
    line-height: 1.3;
    margin-bottom: 12px;
}
.activity-description {
    color: #D1D5DB;
    font-size: 15px;
    font-weight: 400;
    line-height: 1.6;
}
@media (max-width: 900px) {
    .activity-grid {
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }
}
@media (max-width: 550px) {
    .activity-grid {
        grid-template-columns: 1fr;
    }
}
</style>

<h3>How the activity works</h3>

<div class="activity-grid">
    <div class="activity-card">
        <div class="activity-title">1. Read the diagram</div>
        <div class="activity-description">
            Identify the effect, categories, causes, and smaller branches.
        </div>
    </div>
    <div class="activity-card">
        <div class="activity-title">2. Sort five causes</div>
        <div class="activity-description">
            Match each cause to its category in the example.
        </div>
    </div>
    <div class="activity-card">
        <div class="activity-title">3. Prioritize causes</div>
        <div class="activity-description">
            Spend four points on the causes you want to investigate.
        </div>
    </div>
    <div class="activity-card">
        <div class="activity-title">4. Test with data</div>
        <div class="activity-description">
            Change the numbers to see whether the pattern supports
            or challenges a suspected cause.
        </div>
    </div>
</div>
""", unsafe_allow_html=True)
st.caption(
    "Based on Dr. Mi Kyong Newsom's Analyze: Root Cause Analysis slides, pages 22-25 and 38-40. "
    "Hints and category definitions are supplementary guidance. Some category placements can be debated."
)
st.header("Understand the fishbone")
st.write(
    "The orange head is the effect. Blue bones are categories. Teal circles are possible causes. "
    "Purple circles are smaller branches attached to a cause. Click a circle for its category and explanation."
)
st.caption("C numbers are stable reference labels, not rankings or scores. S labels identify smaller branches.")
left, right = st.columns([3, 1])
with left:
    event = st.plotly_chart(fishbone(), key="reference_fishbone_v2", width="stretch",
                           theme=None, on_select="rerun", selection_mode="points",
                           config={"displayModeBar": False})
with right:
    st.subheader("Diagram details")
    clicked = selected_id(event)
    if clicked and clicked != st.session_state.get("last_reference_click"):
        st.session_state.detail_part = clicked
        st.session_state.last_reference_click = clicked
    if st.session_state.get("detail_part") not in PARTS:
        st.session_state.detail_part = "effect"
    st.selectbox("Choose a part, or click its circle", list(PARTS),
                 format_func=lambda key: PARTS[key]["heading"], key="detail_part")
    part_panel(st.session_state.detail_part)
with st.expander("Read all causes and their categories"):
    st.table([{"ID": LABELS[c["id"]], "Category": c["correct_bone"], "Possible cause": c["text"]}
              for c in ALL_CAUSES])
    for sub in SUBCAUSES:
        parent = LOOKUP[sub["parent_id"]]
        st.write(f"**{SUBLABELS[sub['id']]} -> {LABELS[parent['id']]} -> {parent['correct_bone']}**")
        part_panel(sub["id"])

st.divider()
st.header("Level 1: Sort five causes")
st.write("Choose the category used in this example.")
st.button("Start a new practice round", on_click=reset_practice)
columns = st.columns(len(PRACTICE))
correct_count = 0
for i, (column, cause) in enumerate(zip(columns, PRACTICE), 1):
    cid = cause["id"]
    answer_key, feedback_key = f"answer_{cid}", f"feedback_{cid}"
    with column.container(border=True):
        st.markdown(f"**Question {i} | {LABELS[cid]}**")
        st.write(cause["text"])
        answer = st.selectbox("Category", ["Choose..."] + BONES, key=answer_key)
        if st.button("Check answer", key=f"check_{cid}"):
            if answer == "Choose...":
                st.warning("Choose a category first.")
            else:
                st.session_state[feedback_key] = {"choice": answer, "correct": answer == cause["correct_bone"]}
        result = st.session_state.get(feedback_key)
        if result and result["choice"] == answer:
            is_correct = result["correct"]
            color = "#16A34A" if is_correct else "#DC2626"
            st.markdown(f'''<style>
            .st-key-{answer_key} [data-baseweb="select"] > div {{border: 2px solid {color} !important;}}
            </style>''', unsafe_allow_html=True)
            if is_correct:
                correct_count += 1
                st.success("Correct: " + cause["correct_bone"])
            else:
                st.error("Incorrect for this example. Answer: " + cause["correct_bone"])
                st.info("Hint: " + cause["hint"])
                st.caption("Change your selection and check again.")

st.progress(correct_count / len(PRACTICE))
st.write(f"{correct_count} of {len(PRACTICE)} causes correctly placed and checked.")

st.divider()
st.header("Level 2: Prioritize with four voting points")
st.write(
    "Voting asks what to investigate first; there is no single correct allocation. "
    "Give more points to a cause you think deserves attention. For a test, try 2, 1, 1, 0, 0."
)
if correct_count < len(PRACTICE):
    st.info(f"Complete all {len(PRACTICE)} sorting questions correctly to unlock voting.")
else:
    st.caption("One participant has four points. A classroom team would combine all participants' votes.")
    votes = {}
    vote_columns = st.columns(len(PRACTICE))
    for column, cause in zip(vote_columns, PRACTICE):
        with column:
            st.markdown(f"**{LABELS[cause['id']]} | {cause['correct_bone']}**")
            st.write(cause["text"])
            votes[cause["id"]] = st.number_input("Voting points", min_value=0, max_value=4,
                                                  value=0, step=1, key=f"vote_{cause['id']}")
    total = sum(votes.values())
    st.metric("Points allocated", f"{total} / 4")
    if total < 4:
        st.info(f"{4-total} points remain. The diagram below updates while you allocate them.")
    elif total > 4:
        st.error(f"Remove {total-4} points. The diagram shows a draft until the total is four.")
    else:
        st.success("Four points allocated. Your priorities are ready.")

    results_column, diagram_column = st.columns([1.15, 1])
    with results_column:
        st.subheader("Your voting results" if total == 4 else "Draft voting results")
        ranked = sorted(PRACTICE, key=lambda c: votes[c["id"]], reverse=True)
        st.table([{
            "Cause": LABELS[c["id"]] + ": " + c["text"],
            "Points": votes[c["id"]],
            "Share of four-point budget": f"{votes[c['id']]/4:.0%}",
        } for c in ranked])
        if total == 4:
            positive = [c for c in ranked if votes[c["id"]] > 0]
            cutoff = votes[positive[min(3, len(positive))-1]["id"]]
            shortlist = [c for c in positive if votes[c["id"]] >= cutoff]
            st.markdown("**Priorities for investigation**")
            for c in shortlist:
                st.write(f"- {LABELS[c['id']]}: {c['text']}")
            if len(shortlist) > 3:
                st.caption("A tie at the third-place cutoff includes all tied causes; the team can discuss how to proceed.")
            elif len(shortlist) < 3:
                st.caption("Fewer than three causes received votes. Only those receiving votes are shortlisted.")
    with diagram_column:
        st.subheader("Priorities for investigation")
        live_event = st.plotly_chart(fishbone([c["id"] for c in PRACTICE], votes),
                                    key="live_vote_fishbone", width="stretch", theme=None,
                                    on_select="rerun", selection_mode="points",
                                    config={"displayModeBar": False})
        st.caption("Larger cause circles mean more votes. Grey means zero votes. Equal votes have equal emphasis.")
        st.caption("Cause positions and categories stay fixed. Purple smaller branches are context and receive no separate votes.")
        live_clicked = selected_id(live_event)
        if live_clicked:
            part_panel(live_clicked)
    st.info("Votes prioritize investigation; they do not confirm root causes. Next, use observations and appropriate statistical testing.")

st.divider()
st.header("Does the data support the cause?")
st.caption("Fictional learning simulation, separate from the BMW example and your voting results.")
st.write(
    "**Possible cause:** Reports sent by mail or fax may arrive late more often than electronic reports. "
    "Change the observed counts below and watch the rates and comparison change."
)


def set_simulation(values):
    for key, value in zip(("sim_mail_total", "sim_mail_late", "sim_electronic_total", "sim_electronic_late"), values):
        st.session_state[key] = value


preset_columns = st.columns(3)
preset_columns[0].button("Starting example", on_click=set_simulation, args=((40, 12, 40, 4),))
preset_columns[1].button("Equal rates, different counts", on_click=set_simulation, args=((40, 12, 80, 24),))
preset_columns[2].button("Reverse the pattern", on_click=set_simulation, args=((40, 4, 40, 12),))
for key, default in {"sim_mail_total": 40, "sim_mail_late": 12,
                     "sim_electronic_total": 40, "sim_electronic_late": 4}.items():
    if key not in st.session_state:
        st.session_state[key] = default

mail_column, electronic_column = st.columns(2)
with mail_column:
    st.subheader("Mail or fax")
    mail_total = st.slider("Reports reviewed", 10, 400, key="sim_mail_total")
    mail_late = st.slider("Late reports", 0, 400, key="sim_mail_late")
with electronic_column:
    st.subheader("Electronic")
    electronic_total = st.slider("Reports reviewed", 10, 400, key="sim_electronic_total")
    st.session_state.sim_electronic_late = min(st.session_state.sim_electronic_late, electronic_total)
    electronic_late = st.slider("Late reports", 0, electronic_total, key="sim_electronic_late")
st.caption("Late counts are limited to the number reviewed; lowering a total also caps its late count.")
mail_rate = 100 * mail_late / mail_total
electronic_rate = 100 * electronic_late / electronic_total
gap = mail_rate - electronic_rate
first, second, third = st.columns(3)
first.metric("Mail / fax late rate", f"{mail_rate:.1f}%")
second.metric("Electronic late rate", f"{electronic_rate:.1f}%")
third.metric("Mail / fax minus electronic", f"{gap:+.1f} pp")
st.caption("pp means percentage points: the difference between two percentages.")
comparison = go.Figure(go.Bar(
    x=["Mail or fax", "Electronic"], y=[mail_rate, electronic_rate],
    marker_color=["#F97316", "#38BDF8"],
    text=[f"{mail_rate:.1f}%", f"{electronic_rate:.1f}%"], textposition="auto",
))
comparison.update_layout(
    height=340, margin=dict(t=35, b=20), title="Percentage of reports arriving late",
    yaxis=dict(title="Late reports (%)", range=[0, 100]),
    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
)
st.plotly_chart(comparison, key="simulation_comparison", width="stretch")
if abs(gap) < 0.000001:
    st.info("Both groups have the same observed late rate. These counts show no difference between delivery methods.")
elif gap > 0:
    st.info(f"The mail/fax late rate is {gap:.1f} percentage points higher. This pattern is consistent with the suspected cause, but does not establish it.")
else:
    st.info(f"The electronic late rate is {abs(gap):.1f} percentage points higher. This pattern is opposite to the suspected cause.")
with st.expander("Show the calculations"):
    st.write(f"Mail/fax: {mail_late} / {mail_total} x 100 = {mail_rate:.1f}%")
    st.write(f"Electronic: {electronic_late} / {electronic_total} x 100 = {electronic_rate:.1f}%")
    st.write(f"Difference: {mail_rate:.1f}% - {electronic_rate:.1f}% = {gap:.1f} percentage points")
st.warning(
    "These simulated patterns are not statistical verification. Real root-cause validation requires actual data, "
    "an appropriate statistical test, and investigation of other explanations. Equal sample rates do not prove the methods are equivalent."
)
st.subheader("Try these challenges")
st.write("- Make both groups have the same percentage despite different counts.")
st.write("- Make electronic delivery have the higher late rate.")
st.write("- Double both the reviewed and late counts for one group. Does its rate change?")
st.caption("Progress and votes last for this session; this version does not save or aggregate classroom results.")
