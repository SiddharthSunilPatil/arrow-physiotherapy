# sections/sentiment_physio.py
import streamlit as st
import pandas as pd
import numpy as np
import re
from collections import Counter
import matplotlib.pyplot as plt
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

SIA = SentimentIntensityAnalyzer()

# ---------- helpers ----------
def _label(c: float) -> str:
    if pd.isna(c): return np.nan
    if c >= 0.05:  return "Positive"
    if c <= -0.05: return "Negative"
    return "Neutral"

def _arrow(diff: float, good_when_positive: bool = True):
    if np.isnan(diff):
        return "—", "gray"
    if good_when_positive:
        return ("⬆️", "green") if diff > 0 else ("⬇️", "red")
    else:
        return ("⬇️", "green") if diff > 0 else ("⬆️", "red")

def _normalize_text(s: str) -> str:
    s = str(s)
    s = re.sub(r"\s+", " ", s).strip()
    return s.lower()

def _normalize_text_for_issues(s: str) -> str:
    s = str(s).lower()
    s = re.sub(r"http\S+|www\.\S+", " ", s)
    s = re.sub(r"[^a-z0-9\s']", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def _bigram_phrases(texts, topk=8):
    stop = set("""
        a about above after again against all am an and any are as at be because been before being below
        between both but by could did do does doing down during each few for from further had has have having he
        her here hers herself him himself his how i if in into is it its itself just me more most my myself no nor
        not of off on once only or other our ours ourselves out over own same she should so some such than that the
        their theirs them themselves then there these they this those through to too under until up very was we were
        what when where which while who whom why with you your yours yourself yourselves
    """.split())
    grams = Counter()
    for t in texts:
        toks = [w for w in _normalize_text_for_issues(t).split() if w not in stop and len(w) > 2]
        for i in range(len(toks) - 1):
            grams.update([f"{toks[i]} {toks[i+1]}"])
    return grams.most_common(topk)

# Practical, editable taxonomy (tune keywords as you see real data)
ISSUE_RULES: dict[str, list[str]] = {
    "Wait times": [
        "wait", "waiting", "long wait", "hours", "delay", "queue", "line", "triage", "backlog"
    ],
    "Staff attitude / communication": [
        "rude", "unprofessional", "dismissive", "attitude", "didn't listen", "doesn't listen",
        "listen", "respect", "communication", "condescending", "abrupt"
    ],
    "Care quality / effectiveness": [
        "ineffective", "didn't help", "did not help", "no improvement", "worsened",
        "misdiagnosed", "incorrect diagnosis", "poor treatment", "did nothing", "pain not"
    ],
    "Scheduling / availability": [
        "appointment", "booking", "book", "cancel", "cancellation", "reschedule",
        "availability", "overbooked", "no slot", "fully booked"
    ],
    "Price / insurance": [
        "cost", "expensive", "overcharged", "pricing", "billed", "billing", "insurance",
        "coverage", "deductible", "out of pocket"
    ],
    "Cleanliness / facility": [
        "dirty", "unclean", "cleanliness", "hygiene", "washroom", "restroom",
        "equipment", "maintenance", "crowded", "overcrowded"
    ],
    "Parking / access": [
        "parking", "lot", "pay parking", "no parking", "access", "entrance", "wheelchair"
    ],
    "Follow-up / admin": [
        "paperwork", "referral", "report", "follow up", "follow-up", "response",
        "email", "call back", "no call", "no reply"
    ],
    "Therapist expertise": [
        "inexperienced", "competence", "untrained", "not knowledgeable", "not skilled",
        "lack experience", "poor technique"
    ],
}

def _compile_issue_patterns(rules: dict[str, list[str]]):
    compiled = {}
    for issue, kws in rules.items():
        pats = []
        for k in kws:
            k = k.strip()
            pats.append(re.compile(rf"\b{k}\b", re.I))
        compiled[issue] = pats
    return compiled

ISSUE_PATTERNS = _compile_issue_patterns(ISSUE_RULES)

# ---------- main render ----------
def render(dguid: str, pcr_df: pd.DataFrame):
    """
    Physio reviews only (pcr_with_DGUID.csv assumed).
    Columns expected: DGUID, Text (Rating optional, Place ID optional, Time optional).
    """
    st.header("📝 Local Sentiment — Physio Clinics")
    st.caption(f"DGUID: **{dguid}**")

    required = {"DGUID", "Text"}
    missing = required - set(pcr_df.columns)
    if missing:
        st.error(f"Missing columns in physio reviews: {', '.join(sorted(missing))}")
        return

    # 1) Filter to selected DGUID
    df_local = pcr_df[pcr_df["DGUID"].astype(str) == str(dguid)].copy()
    raw_count = len(df_local)
    if df_local.empty:
        st.info("No physio reviews found for this DGUID.")
        return

    # Clean empties
    df_local["Text"] = df_local["Text"].astype(str)
    df_local["__norm_text"] = df_local["Text"].apply(_normalize_text)
    df_local = df_local[df_local["__norm_text"].str.len() > 0].copy()
    cleaned_count = len(df_local)

    # ---- DEDUPLICATION ----
    # Keep newest by Time if available
    if "Time" in df_local.columns:
        # If Time is epoch seconds or numeric-like, sort descending
        df_local["_time_sort"] = pd.to_numeric(df_local["Time"], errors="coerce")
        df_local = df_local.sort_values("_time_sort", ascending=False, na_position="last")
    else:
        df_local["_time_sort"] = np.nan

    # Choose best key: Place ID + text; else Facility Name + text; else text only
    if "Place ID" in df_local.columns:
        dedupe_keys = ["Place ID", "__norm_text"]
    elif "Facility Name" in df_local.columns:
        dedupe_keys = ["Facility Name", "__norm_text"]
    else:
        dedupe_keys = ["__norm_text"]

    df_local = df_local.drop_duplicates(subset=dedupe_keys, keep="first").copy()
    deduped_count = len(df_local)

    # Sentiment
    scores_local = df_local["Text"].apply(lambda t: SIA.polarity_scores(t)).apply(pd.Series)
    df_local = pd.concat([df_local, scores_local], axis=1)
    df_local["sentiment"] = df_local["compound"].apply(_label)

    # Local counts/shares (ignore neutrals)
    pos_local = int((df_local["sentiment"] == "Positive").sum())
    neg_local = int((df_local["sentiment"] == "Negative").sum())
    den_local = pos_local + neg_local

    ratio_local = (pos_local / neg_local) if neg_local > 0 else np.inf
    pos_share_local = (pos_local / den_local) if den_local > 0 else np.nan
    neg_share_local = (neg_local / den_local) if den_local > 0 else np.nan

    # Provenance caption
    st.caption(
        f"Reviews in this DGUID — raw: **{raw_count}** → cleaned: **{cleaned_count}** "
        f"→ deduped: **{deduped_count}** → non-neutral used: **{den_local}**"
    )

    # 2) GTA baselines (MEAN across DGUIDs of per-DGUID shares)
    scored = pcr_df.copy()
    scored["Text"] = scored["Text"].astype(str)
    scored["__norm_text"] = scored["Text"].apply(_normalize_text)
    scored = scored[scored["__norm_text"].str.len() > 0]

    # (Optional) light dedupe per DGUID for fairer baseline
    if "Place ID" in scored.columns:
        scored = scored.sort_values("DGUID").drop_duplicates(subset=["DGUID", "Place ID", "__norm_text"])
    else:
        scored = scored.sort_values("DGUID").drop_duplicates(subset=["DGUID", "__norm_text"])

    sc = scored["Text"].apply(lambda t: SIA.polarity_scores(t)).apply(pd.Series)
    scored = pd.concat([scored, sc], axis=1)
    scored["sentiment"] = scored["compound"].apply(_label)

    grp = scored.groupby("DGUID")["sentiment"].value_counts().unstack(fill_value=0)
    for col in ["Positive", "Negative"]:
        if col not in grp.columns:
            grp[col] = 0
    grp["den"] = grp["Positive"] + grp["Negative"]
    grp = grp[grp["den"] > 0].copy()
    grp["pos_share"] = grp["Positive"] / grp["den"]
    grp["neg_share"] = grp["Negative"] / grp["den"]

    gta_pos_share_avg = float(grp["pos_share"].mean()) if not grp.empty else np.nan
    gta_neg_share_avg = float(grp["neg_share"].mean()) if not grp.empty else np.nan

    d_pos = pos_share_local - gta_pos_share_avg if not np.isnan(pos_share_local) and not np.isnan(gta_pos_share_avg) else np.nan
    d_neg = neg_share_local - gta_neg_share_avg if not np.isnan(neg_share_local) and not np.isnan(gta_neg_share_avg) else np.nan

    # 3) Display summary
    st.subheader("📊 Summary (Physio only)")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Positive", f"{pos_local:,}")
    c2.metric("Total Negative", f"{neg_local:,}")
    c3.metric("+ / − Ratio", ("∞" if np.isinf(ratio_local) else f"{ratio_local:.2f}"))
    c4.metric("Samples used", f"{den_local:,}")

    c5, c6 = st.columns(2)
    arrow_pos, col_pos = _arrow(d_pos, good_when_positive=True)
    arrow_neg, col_neg = _arrow(d_neg, good_when_positive=False)

    if not np.isnan(pos_share_local):
        c5.markdown(
            f"""**Positivity share (local)**<br>
            {pos_share_local*100:.1f}%<br>
            {arrow_pos} <span style='color:{col_pos}'>{(d_pos*100):+,.1f} pp vs GTA <strong>average</strong></span>""",
            unsafe_allow_html=True,
        )
    else:
        c5.metric("Positivity share", "N/A")

    if not np.isnan(neg_share_local):
        c6.markdown(
            f"""**Negativity share (local)**<br>
            {neg_share_local*100:.1f}%<br>
            {arrow_neg} <span style='color:{col_neg}'>{(d_neg*100):+,.1f} pp vs GTA <strong>average</strong></span>""",
            unsafe_allow_html=True,
        )
    else:
        c6.metric("Negativity share", "N/A")

    if den_local < 10:
        st.caption("⚠️ Fewer than 10 non-neutral reviews in this DGUID — interpret with caution.")

    # 4) Issues mining (themes)
    st.subheader("🔎 Commonly discussed issues (local)")

    df_local["__norm_text_issues"] = df_local["Text"].apply(_normalize_text_for_issues)
    # build issue flags
    issue_cols = []
    for issue, patterns in ISSUE_PATTERNS.items():
        col = f"ISSUE::{issue}"
        issue_cols.append(col)
        df_local[col] = df_local["__norm_text_issues"].apply(lambda t: int(any(p.search(t) for p in patterns)))

    neg_mask = df_local["sentiment"] == "Negative"
    total_neg = int(neg_mask.sum())

    rows = []
    for issue, col in zip(ISSUE_RULES.keys(), issue_cols):
        mentions_all = int(df_local[col].sum())
        mentions_neg = int(df_local.loc[neg_mask, col].sum())
        share_neg = (mentions_neg / total_neg * 100.0) if total_neg > 0 else 0.0

        texts_for_issue = df_local.loc[neg_mask & (df_local[col] == 1), "Text"].tolist()
        top_ph = _bigram_phrases(texts_for_issue, topk=1)
        sample = top_ph[0][0] if top_ph else ""

        rows.append({
            "Issue": issue,
            "Mentions (neg)": mentions_neg,
            "Share of negatives": round(share_neg, 1),
            "All mentions": mentions_all,
            "Example phrase": sample,
        })

    issues_df = pd.DataFrame(rows).sort_values(
        ["Mentions (neg)", "All mentions"], ascending=[False, False]
    )

    if issues_df.empty or (issues_df["Mentions (neg)"].sum() == 0 and issues_df["All mentions"].sum() == 0):
        st.caption("No clear recurring issues detected.")
    else:
        st.dataframe(issues_df, use_container_width=True)

        # simple horizontal bar of top negative mentions
        top = issues_df.head(8)
        fig, ax = plt.subplots(figsize=(7, 4))
        ax.barh(top["Issue"][::-1], top["Mentions (neg)"][::-1])
        ax.set_xlabel("Mentions in negative reviews")
        ax.set_ylabel("")
        ax.set_title("Top issues (negative reviews)")
        st.pyplot(fig)

        # Representative quotes per top issue
        st.subheader("💬 Representative quotes (negative)")
        for issue in top["Issue"].tolist():
            col = f"ISSUE::{issue}"
            examples = df_local.loc[neg_mask & (df_local[col] == 1), "Text"].dropna().astype(str)
            examples = sorted(examples, key=lambda s: len(s))[:3]
            if not examples:
                continue
            with st.expander(issue):
                for e in examples:
                    st.markdown(f"- {e}")

    # Optional: raw reviews
    with st.expander("📄 All local reviews (with sentiment)"):
        st.dataframe(
            df_local[["Text", "compound", "sentiment"]].sort_values("compound", ascending=False),
            use_container_width=True, height=360
        )
