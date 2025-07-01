import streamlit as st
import streamlit.components.v1 as stc

copy_id = 0


def copy_button(text_to_copy: str):
    global copy_id
    st.markdown(
        f"""<button class="copy-button" id="st-key-copy-button-{copy_id}" data="{text_to_copy}">⧉</button>""",
        unsafe_allow_html=True,
    )
    copy_id += 1


def enable_copy_buttons():
    copy_buttons_script = """
        <script>
            const parentDOM = window.parent.document;

            const buttons = parentDOM.getElementsByClassName("copy-button");
            console.log(buttons);
            for (let button of buttons) {
                button.addEventListener("click", () => {
                    const data = button.getAttribute("data");
                    navigator.clipboard.writeText(data).then(() => {
                        console.log("Copied:", data);
                        button.innerText = "✓";
                        setTimeout(() => button.innerText = "⧉", 1000);
                    }).catch(err => {
                        console.error("Copy failed:", err);
                    });
                })
            }
        </script>
    """

    stc.html(copy_buttons_script, height=0)
