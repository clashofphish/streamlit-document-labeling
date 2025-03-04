from PIL import Image
import streamlit as st
import streamlit_nested_layout
import streamlit_javascript as st_js
from streamlit_sparrow_labeling import st_sparrow_labeling
from streamlit_sparrow_labeling import DataProcessor
from streamlit_sparrow_labeling.utils.file_handling import load_config_dataframe
import json
import math
import os
import csv
import pandas as pd

st.set_page_config(page_title="Sparrow Labeling", layout="wide")


def save_and_continue(config, current_index, selected_classes, save_sections, doc_type):
    save_file = "annotations.csv"
    row = config.iloc[current_index]
    data = {
        "attachmentId": row["attachmentId"],
        "image_file_path": row["image_file_path"],
        "ocr_file_path": row["ocr_file_path"],
        "class_1": selected_classes[0],
        "class_2": selected_classes[1],
        "class_3": selected_classes[2],
        "annotated_text": json.dumps(save_sections),
        "doc_type": doc_type,
    }
    if not os.path.exists(save_file):
        with open(save_file, "w") as f:
            writer = csv.DictWriter(f, fieldnames=data.keys())
            writer.writeheader()
            writer.writerow(data)
    else:
        with open(save_file, "r") as f:
            existing_data = [row for row in csv.DictReader(f)]
        existing_ids = [row["attachmentId"] for row in existing_data]
        if data["attachmentId"] in existing_ids:
            existing_data = [
                row if row["attachmentId"] != data["attachmentId"] else data
                for row in existing_data
            ]
            with open(save_file, "w") as f:
                writer = csv.DictWriter(f, fieldnames=data.keys())
                writer.writeheader()
                writer.writerows(existing_data)
        else:
            with open(save_file, "a") as f:
                writer = csv.DictWriter(f, fieldnames=data.keys())
                writer.writerow(data)


def run(img_file, rects_file, labels, config, current_index):
    ui_width = st_js.st_javascript("window.innerWidth")

    docImg = Image.open(img_file)

    if (
        "image_state" not in st.session_state
        or st.session_state["current_index"] != current_index
    ):
        with open(rects_file, "r") as f:
            image_state = json.load(f)
            st.session_state["image_state"] = image_state
            st.session_state["current_index"] = current_index
    else:
        image_state = st.session_state["image_state"]

    show_ocr_boxes = st.checkbox("Show OCR Boxes", True)

    assign_labels = st.checkbox("Assign Labels", True)
    mode = "transform" if assign_labels else "rect"

    col1, col2 = st.columns([4, 6])

    with col1:
        height = 1296  # 1024
        width = 864  # 792

        doc_height = image_state["meta"]["image_size"]["height"]
        doc_width = image_state["meta"]["image_size"]["width"]

        canvas_width = canvas_available_width(ui_width)

        initial_rects = (
            image_state
            if show_ocr_boxes
            else {"meta": image_state["meta"], "words": []}
        )

        result_rects = st_sparrow_labeling(
            fill_color="rgba(0, 0, 0, 0)",  # No fill color
            stroke_width=2,
            stroke_color="rgba(255, 0, 0, 1)",  # Red stroke color
            background_image=docImg,
            initial_rects=initial_rects,
            height=height * 1.5,  # Increase the canvas height
            width=width * 1.5,  # Increase the canvas width
            drawing_mode=mode,
            display_toolbar=True,
            update_streamlit=True,
            canvas_width=canvas_width,
            doc_height=doc_height,
            doc_width=doc_width,
            image_rescale=True,
            key="doc_annotation",
        )

        st.caption(
            "Check 'Assign Labels' to enable editing of labels and values, move and resize the boxes to annotate the document.\n\nDraw a selection box around a set of OCR bounding boxes to concatenate the text within those boxes."
        )

    with col2:
        with st.container():
            doc_type = st.text_input("Document Type", key="doc_type")
            classes = [
                "title page",
                "table of contents",
                "form",
                "table",
                "narrative",
                "acronym list",
                "clause list",
                "requirements",
                "scope",
                "pay schedule",
                "background",
                "other",
                "None",
            ]
            class_1 = st.selectbox("Class 1", classes, key="class_1")
            class_2 = st.selectbox(
                "Class 2", classes, key="class_2", index=len(classes) - 1
            )
            class_3 = st.selectbox(
                "Class 3", classes, key="class_3", index=len(classes) - 1
            )

        with st.container():
            if result_rects is not None:
                print(f"**Result Rects: {result_rects.rects_data}")
                with st.form(key="fields_form"):
                    save_sections = []  # Save the annotated selections
                    for i, rect in enumerate(result_rects.rects_data["words"]):
                        print(f"**Rect: {rect}")
                        print(f"**Saved State: {[k for k in image_state.keys()]}")
                        selected_text = get_selected_words(rect, image_state["words"])
                        joined_text = join_text(selected_text)
                        print(f"**Selected Text: {selected_text}")
                        st.text_area(
                            f"Text {i + 1}",
                            joined_text,
                            key=f"text_{i}",
                            height=100,
                        )
                        st.text_input(
                            f"Label {i + 1}",
                            key=f"label_{i}",
                        )
                        st.markdown("---")

                        save_sections.append(
                            {
                                "text": st.session_state.get(f"text_{i}", ""),
                                "label": st.session_state.get(f"label_{i}", ""),
                            }
                        )

                    submit = st.form_submit_button("Save and Continue", type="primary")
                    back = st.form_submit_button("Back")
                    if submit:
                        save_and_continue(
                            config,
                            current_index,
                            [class_1, class_2, class_3],
                            save_sections,
                            doc_type,
                        )
                        next_index = (current_index + 1) % len(config)
                        st.session_state["current_index"] = next_index
                        st.session_state.pop("image_state", None)
                        st.rerun()
                    if back:
                        prev_index = (current_index - 1) % len(config)
                        st.session_state["current_index"] = prev_index
                        st.session_state.pop("image_state", None)
                        st.rerun()


def get_selected_words(selection_rect, words):
    selected_texts = []
    for word in words:
        if is_within_selection(selection_rect, word["rect"]):
            selected_texts.append(
                {
                    "line_n": word["line_n"],
                    "word_n": word["word_n"],
                    "text": word["text"],
                }
            )
    return selected_texts


def is_within_selection(selection_rect, word_rect):
    return (
        word_rect["x1"] >= selection_rect["rect"]["x1"]
        and word_rect["y1"] >= selection_rect["rect"]["y1"]
        and word_rect["x2"] <= selection_rect["rect"]["x2"]
        and word_rect["y2"] <= selection_rect["rect"]["y2"]
    )


def join_text(selected_words):
    array_of_words = pd.DataFrame(selected_words, columns=["line_n", "word_n", "text"])
    array_of_words.sort_values(by=["line_n", "word_n"], inplace=True)
    words_by_line = array_of_words.groupby("line_n")["text"].apply(
        lambda x: " ".join(x)
    )
    return "\n".join(words_by_line)


def canvas_available_width(ui_width):
    # Get ~40% of the available width, if the UI is wider than 500px
    if ui_width > 500:
        return math.floor(38 * ui_width / 100)
    else:
        return ui_width


if __name__ == "__main__":
    custom_labels = ["", "item", "item_price", "subtotal", "tax", "total"]
    data_config_dir = os.path.abspath(
        os.path.join(
            "..",
            "anx_llm_research",
            "fine_tuning",
            "modeling_data",
            "contract_files",
            "converted_files_sot01a.csv",
        )
    )
    config = load_config_dataframe(data_config_dir)
    print(f"**Config: {config.loc[0, 'image_file_path']}")

    current_index = st.session_state.get("current_index", 0)
    run(
        config.loc[current_index, "image_file_path"],
        config.loc[current_index, "ocr_file_path"],
        custom_labels,
        config,
        current_index,
    )
