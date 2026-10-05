    decision = result["decision"]
    rule_id = result["rule_id"]
    comment = result["comment"]

    if decision == "ALLOWED":
        decision_text = (
            "✅ Allowed — it should not be removed."
        )
    else:
        decision_text = (
            "❌ Not allowed — it should be removed"
        )

    if language == "Arabic":

        section_text = ARABIC_SECTIONS[
            RULES[rule_id]["section"]
        ]

        rule_text = ARABIC_RULES[
            rule_id
        ]

        decision_label = "Decision:"
        section_label = "Main Guideline Section:"
        rule_label = "Specific Sub-rule:"
        comment_label = "Comment:"

    else:

        section_text = RULES[
            rule_id
        ]["section"]

        rule_text = RULES[
            rule_id
        ]["rule"]

        decision_label = "Decision:"
        section_label = "Main Guideline Section:"
        rule_label = "Specific Sub-rule:"
        comment_label = "Comment:"


    st.markdown(
        f"""
**{decision_label}** {decision_text}

**{section_label}** {section_text}

**{rule_label}** {rule_text}

**{comment_label}** {comment}
"""
    )


    # --------------------------------------------------------
    # COPY COMMENT
    # --------------------------------------------------------

    copy_text = comment.replace("'", "\\'").replace("\n", "\\n")

    components.html(
        f"""
        <script>
        function copyComment() {{
            navigator.clipboard.writeText('{copy_text}');
        }}
        </script>

        <button
            onclick="copyComment()"
            style="
                padding: 8px 16px;
                border-radius: 6px;
                border: 1px solid #ccc;
                background: white;
                cursor: pointer;
                font-size: 14px;
            "
        >
            📋 Copy Comment
        </button>
        """,
        height=50
    )


# ============================================================
# GUIDELINES LINK
# ============================================================

st.markdown(
    f"""
    <div style="margin-top: 20px;">
        <a
            href="{ARTICLE_URL}"
            target="_blank"
            rel="noopener noreferrer"
        >
            Noon Customer Reviews Guidelines
        </a>
    </div>
    """,
    unsafe_allow_html=True
)
