import json
import random
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

st.set_page_config(
    page_title="Fishbone Learning Tool",
    page_icon="🐟",
    layout="wide",
)

ROOT = Path(__file__).resolve().parent

with open(ROOT / "data" / "scenarios.json", encoding="utf-8") as file:
    scenario = json.load(file)

st.title("Fishbone Learning Tool")
st.subheader(scenario["title"])
st.info(f"Effect: {scenario['effect']}")

st.caption(
    "BMW category placements follow the lecture example. "
    "Hints and category definitions are draft learning guidance."
)

definitions = {
    "People": "People's knowledge, actions, communication, and perceived impartiality.",
    "Procedure": "The steps and methods used to carry out the work.",
    "Systems": "The systems and information channels supporting the process.",
    "Policy": "Rules and guidelines governing decisions and exceptions.",
    "Environment": "External or surrounding conditions affecting the process.",
    "Equipment": (
        "Often physical tools and devices. In this lecture example, "
        "the category also contains document-related issues."
    ),
}

causes = scenario["causes"]
cause_lookup = {cause["id"]: cause for cause in causes}

# Remember the shuffled order during this browser session.
cause_ids = list(cause_lookup)

saved_order = st.session_state.get("card_order", [])

if (
    len(saved_order) != 5
    or not set(saved_order).issubset(cause_ids)
):
    st.session_state.card_order = random.sample(cause_ids, 5)

# Build the diagram.
fig = go.Figure()
node_info = {}
cause_positions = {}

fig.add_shape(
    type="line",
    x0=0, y0=0, x1=14, y1=0,
    line=dict(color="#CBD5E1", width=4),
)


def add_node(node_id, x, y, label, color, title, explanation):
    node_info[node_id] = {
        "title": title,
        "explanation": explanation,
    }

    fig.add_trace(go.Scatter(
        x=[x],
        y=[y],
        mode="markers+text",
        marker=dict(size=19, color=color),
        text=[label],
        textposition="top center",
        textfont=dict(size=12, color="#E2E8F0"),
        customdata=[node_id],
        hovertext=[title],
        hoverinfo="text",
        showlegend=False,
    ))


positions = [
    (3, 1),
    (7, 1),
    (11, 1),
    (3, -1),
    (7, -1),
    (11, -1),
]

for bone, (base_x, direction) in zip(scenario["bones"], positions):
    tip_x = base_x - 2
    tip_y = direction * 3

    fig.add_shape(
        type="line",
        x0=base_x, y0=0,
        x1=tip_x, y1=tip_y,
        line=dict(color="#0284C7", width=3),
    )

    add_node(
        f"bone_{bone}",
        tip_x, tip_y,
        bone, "#0284C7",
        bone,
        definitions[bone],
    )

    members = [
        cause for cause in causes
        if cause["correct_bone"] == bone
    ]

    for index, cause in enumerate(members):
        fraction = (index + 1) / (len(members) + 1)
        junction_x = base_x - 2 * fraction
        junction_y = direction * 3 * fraction
        node_x = junction_x + 1.0

        fig.add_shape(
            type="line",
            x0=junction_x, y0=junction_y,
            x1=node_x, y1=junction_y,
            line=dict(color="#0D9488", width=2),
        )

        number = causes.index(cause) + 1
        cause_positions[cause["id"]] = (node_x, junction_y)

        add_node(
            cause["id"],
            node_x, junction_y,
            f"C{number}", "#0D9488",
            cause["text"],
            f"Lecture category: {bone}. {cause['hint']}",
        )

# Draw the smaller branch using the relationship stored in JSON.
for sub in scenario.get("sub_causes", []):
    parent_position = cause_positions.get(sub["parent_id"])

    if parent_position:
        parent_x, parent_y = parent_position
        sub_x = parent_x + 0.7
        sub_y = parent_y - 0.8

        fig.add_shape(
            type="line",
            x0=parent_x, y0=parent_y,
            x1=sub_x, y1=sub_y,
            line=dict(color="#9333EA", width=2),
        )

        add_node(
            sub["id"],
            sub_x, sub_y,
            "Sub-cause", "#9333EA",
            sub["text"],
            sub["explanation"],
        )

add_node(
    "effect",
    14, 0,
    "Effect", "#F97316",
    scenario["effect"],
    "The effect is the problem or outcome we want to understand.",
)

fig.update_layout(
    height=570,
    margin=dict(l=20, r=20, t=35, b=35),
    xaxis=dict(visible=False, range=[-0.2, 15]),
    yaxis=dict(visible=False, range=[-4, 4]),
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    clickmode="event+select",
    dragmode=False,
)

diagram, panel = st.columns([3, 1])

with diagram:
    st.write("Click a circle to explore the diagram.")

    event = st.plotly_chart(
        fig,
        use_container_width=True,
        key="bmw_diagram",
        on_select="rerun",
        selection_mode="points",
    )

    st.caption(
        "Blue: categories · Teal: causes · "
        "Purple: smaller branch · Orange: effect"
    )

with panel:
    st.subheader("Explore")

    points = event.selection.points

    if points:
        node_id = points[0].get("customdata")

        if isinstance(node_id, list):
            node_id = node_id[0]

        info = node_info.get(node_id)

        if info:
            st.markdown(f"**{info['title']}**")
            st.write(info["explanation"])
    else:
        st.info("Click a category, cause, smaller branch, or effect.")

st.caption(
    "Fishbone diagrams organize possible causes. "
    "Data is needed to establish which are real root causes."
)

st.divider()
st.header("Level 1: Sort the causes")
st.write(
    "Match each cause to its category in the lecture example. "
    "You can explore the diagram above for help."
)

# Use the same five causes for sorting and voting.
causes = [
    cause_lookup[cause_id]
    for cause_id in st.session_state.card_order
]

correct_count = 0
question_columns = st.columns(5)

for card_number, cause_id in enumerate(st.session_state.card_order, start=1):
    cause = cause_lookup[cause_id]
    widget_key = f"answer_{cause_id}"
    feedback_key = f"feedback_{cause_id}"

    with question_columns[card_number - 1].container(border=True):
        st.markdown(f"**{card_number}. {cause['text']}**")

        choice = st.selectbox(
            "Choose a category",
            ["Choose…"] + scenario["bones"],
            key=widget_key,
        )

        if st.button("Check answer", key=f"check_{cause_id}"):
            if choice == "Choose…":
                st.warning("Choose a category first.")
            else:
                st.session_state[feedback_key] = {
                    "choice": choice,
                    "correct": choice == cause["correct_bone"],
                }

        feedback = st.session_state.get(feedback_key)

        if feedback and feedback["choice"] == choice:
            is_correct = feedback["correct"]
            color = "#15803D" if is_correct else "#DC2626"

            st.markdown(
                f"""
                <style>
                .st-key-{widget_key} [data-baseweb="select"] > div {{
                    border: 2px solid {color} !important;
                }}
                </style>
                """,
                unsafe_allow_html=True,
            )

            if is_correct:
                correct_count += 1
                st.success("Correct!")
                st.write(cause["hint"])
            else:
                st.error(
                    f"Lecture answer: {cause['correct_bone']}."
                )
                st.info(f"Hint: {cause['hint']}")
                st.write("Change your selection and try again.")
                st.divider()
st.header("Level 2: Prioritize with four voting points")

voting_causes = [
    cause_lookup[cause_id]
    for cause_id in st.session_state.card_order
]

if correct_count < len(voting_causes):
    st.info("Complete all five sorting questions correctly to unlock voting.")
else:
    st.write(
        "Spend exactly 4 points on the causes you want to investigate. "
        "You can give more than one point to a cause."
    )

    votes = {}
    vote_columns = st.columns(len(voting_causes))

    for column, cause in zip(vote_columns, voting_causes):
        with column:
            votes[cause["id"]] = st.number_input(
                cause["text"],
                min_value=0,
                max_value=4,
                value=0,
                step=1,
                key=f"vote_{cause['id']}",
            )

    total = sum(votes.values())
    st.metric("Points allocated", f"{total} / 4")

    if total < 4:
        st.info(f"You have {4 - total} points left.")
    elif total > 4:
        st.error(f"Remove {total - 4} points.")

    if total == 4:
        ranked = sorted(
            [
                cause for cause in voting_causes
                if votes[cause["id"]] > 0
            ],
            key=lambda cause: votes[cause["id"]],
            reverse=True,
        )

        st.subheader("Your voting results")

        st.table([
            {
                "Cause": cause["text"],
                "Points": votes[cause["id"]],
                "Share of votes": f"{votes[cause['id']] / 4:.0%}",
            }
            for cause in ranked
        ])

        cutoff = votes[ranked[min(3, len(ranked)) - 1]["id"]]
        shortlist = [
            cause for cause in ranked
            if votes[cause["id"]] >= cutoff
        ]

        st.write("**Priorities for investigation:**")
        for cause in shortlist:
            st.write(f"• {cause['text']}")

        if len(shortlist) > 3:
            st.caption("All causes tied at the third-place cutoff are included.")
        elif len(shortlist) < 3:
            st.caption("Only causes receiving points are included.")

        st.info(
            "These are your individual priorities. A team would combine "
            "participants' votes. Votes do not prove a root cause—"
            "the next step is verification with data."
        )

st.divider()
st.caption("Fictional learning simulation — not BMW company data.")

st.write(
    "**Possible cause:** Reports sent by mail or fax may arrive late "
    "more often than electronic reports. Change the numbers to explore."
)

mail_column, electronic_column = st.columns(2)

with mail_column:
    st.subheader("Mail or fax")

    mail_total = st.slider(
        "Reports reviewed",
        min_value=10,
        max_value=200,
        value=40,
        key="sim_mail_total",
    )

    mail_late = st.slider(
        "Late reports",
        min_value=0,
        max_value=200,
        value=12,
        key="sim_mail_late",
    )

with electronic_column:
    st.subheader("Electronic")

    electronic_total = st.slider(
        "Reports reviewed",
        min_value=10,
        max_value=200,
        value=40,
        key="sim_electronic_total",
    )

    electronic_late = st.slider(
        "Late reports",
        min_value=0,
        max_value=200,
        value=4,
        key="sim_electronic_late",
    )

valid_data = (
    mail_late <= mail_total
    and electronic_late <= electronic_total
)

if not valid_data:
    st.error(
        "Late reports cannot exceed reports reviewed. "
        "Lower the late count or increase the total."
    )
else:
    mail_rate = mail_late / mail_total * 100
    electronic_rate = electronic_late / electronic_total * 100
    gap = mail_rate - electronic_rate

    first, second, third = st.columns(3)

    first.metric("Mail / fax late rate", f"{mail_rate:.1f}%")
    second.metric("Electronic late rate", f"{electronic_rate:.1f}%")
    third.metric("Mail / fax minus electronic", f"{gap:+.1f} pp")

    comparison = go.Figure(go.Bar(
        x=["Mail or fax", "Electronic"],
        y=[mail_rate, electronic_rate],
        marker_color=["#F97316", "#0284C7"],
        text=[f"{mail_rate:.1f}%", f"{electronic_rate:.1f}%"],
        textposition="auto",
    ))

    comparison.update_layout(
        title="Percentage of reports arriving late",
        yaxis=dict(
            title="Late reports (%)",
            range=[0, 100],
        ),
        xaxis_title="Delivery method",
        height=350,
        showlegend=False,
    )

    st.plotly_chart(
        comparison,
        use_container_width=True,
        key="simulation_comparison",
    )

    if abs(gap) < 0.000001:
        st.info(
            "Both groups have the same observed late-report rate. "
            "These numbers show no difference between delivery methods."
        )
    elif gap > 0:
        st.info(
            f"The mail/fax late rate is {gap:.1f} percentage points higher. "
            "This pattern is consistent with the suspected cause, "
            "but does not establish it."
        )
    else:
        st.info(
            f"The electronic late rate is {abs(gap):.1f} percentage points higher. "
            "These numbers show the opposite pattern to the suspected cause."
        )

    with st.expander("Show the calculations"):
        st.write(
            f"Mail/fax: {mail_late} ÷ {mail_total} × 100 "
            f"= {mail_rate:.1f}%"
        )
        st.write(
            f"Electronic: {electronic_late} ÷ {electronic_total} × 100 "
            f"= {electronic_rate:.1f}%"
        )
        st.write(
            f"Difference: {mail_rate:.1f}% − {electronic_rate:.1f}% "
            f"= {gap:.1f} percentage points"
        )

    st.warning(
        "Changing simulated numbers explores possible patterns. "
        "Validating a real cause requires actual observations, "
        "an appropriate statistical test, and checking other explanations."
    )

st.subheader("Try these challenges")
st.write("• Make both groups have the same late-report percentage.")
st.write("• Make electronic delivery have the higher late-report rate.")
st.write(
    "• Double both the total and late counts for one group. "
    "Does its percentage change?"
)