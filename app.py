"""Modified with the help of Github Copilot AI and reviewed by a human."""

from PIL import Image
import streamlit as st
import streamlit_nested_layout
import streamlit_javascript as st_js
from streamlit_sparrow_labeling import st_sparrow_labeling
from streamlit_sparrow_labeling import DataProcessor
from streamlit_sparrow_labeling.utils.file_handling import (
    load_config_dataframe,
    load_annotated_config_dataframe,
)
import json
import math
import os
import csv
import pandas as pd

st.set_page_config(page_title="Sparrow Labeling", layout="wide")


def save_and_continue(config_row, selected_classes, save_sections, doc_type, save_file):
    data = {
        "index": config_row.name,
        "opportunityId": config_row["opportunityId"],
        "attachmentId": config_row["attachmentId"],
        "image_file_path": config_row["image_file_path"],
        "ocr_file_path": config_row["ocr_file_path"],
        "fileName": config_row["fileName"],
        "class_1": selected_classes[0],
        "class_2": selected_classes[1],
        "class_3": selected_classes[2],
        "annotated_text": json.dumps(save_sections),
        "doc_type": doc_type,
    }
    df = pd.DataFrame([data])
    df.set_index("index", inplace=True)
    if not os.path.exists(save_file):
        df.to_csv(save_file)
    else:
        existing_df = load_annotated_config_dataframe(save_file)
        match_index = existing_df.loc[
            existing_df["image_file_path"] == df["image_file_path"]
        ].index
        if len(match_index) > 0:
            existing_df.update(pd.DataFrame([data], index=match_index))
        else:
            existing_df = pd.concat(
                [existing_df, pd.DataFrame([data], index=match_index)],
                ignore_index=False,
            )
        df.to_csv(save_file)
    return df


def run(img_file, rects_file, config, annotated_config, current_index):
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

    col1, col2 = st.columns([2, 1])
    with col1:
        st.text(f"Image Path: {config.loc[current_index, 'image_file_path']}")

    with col2:
        with st.form(key="index_form"):
            st.text_input(
                f"Jump to index (annotated max {max(annotated_config.index)})",
                value=str(current_index),
                key="jump_index",
            )
            submit_jump = st.form_submit_button("Jump")
            if submit_jump:
                st.session_state["current_index"] = int(
                    st.session_state.get("jump_index")
                )
                st.session_state.pop("image_state", None)
                st.rerun()

    # Set classes
    doc_type_classes = [
        "title page",
        "table of contents",
        "form",
        "narrative",
        "acronym list",
        "clause list",
        "attachment list",
        "pay schedule",
        "delivery info",
        "background",
        "requirements",
        "scope",
        "table",
        "blank",
        "other",
        "None",
    ]
    # Select out annotated row
    print(f"current_index: {current_index}; annotated_config: {annotated_config.index}")
    if current_index in annotated_config.index:
        annotated_row = annotated_config.loc[current_index]
        ci1, ci2, ci3 = check_existing_classes(annotated_row, doc_type_classes)
        doc_type = annotated_row["doc_type"]
        parsed_text = json.loads(annotated_row["annotated_text"])
        print(
            f"ci1: {ci1} ci2: {ci2} ci3: {ci3} doc type: {doc_type} parsed_text: {parsed_text}"
        )
    else:
        annotated_row = None
        ci1, ci2, ci3 = 0, None, None
        doc_type = ""
        parsed_text = []

    # Meta data columns
    col1, col2, col3 = st.columns([2, 2, 2])
    with col1:
        show_ocr_boxes = st.checkbox("Show OCR Boxes", True)

    with col2:
        st.text(f"File Name:   {config.loc[current_index, 'fileName']}")

    with col3:
        im_p = config.loc[current_index, "image_file_path"]
        pn = im_p.split("_")[-1].split(".")[0]
        st.text(f"Page Number:  {pn}")

    # Highlevel manipulate data columns
    col1, col2 = st.columns([1, 1])
    with col1:
        assign_labels = st.checkbox("Assign Labels", True)
        mode = "transform" if assign_labels else "rect"

    with col2:
        use_existing_annotations = st.checkbox("Use Existing Annotations", False)

    # Lower level manipulate data columns
    col1, col2 = st.columns([4, 6])
    with col1:
        with st.container():
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
                height=height * 2,  # Increase the canvas height
                width=width * 2,  # Increase the canvas width
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
        with st.container():
            if parsed_text:
                for i, section in enumerate(parsed_text):
                    st.text(f"Text {i + 1}")
                    st.text(section["text"])
                    st.text(f"Label {i + 1}")
                    st.text(section["label"])
                    st.markdown("---")

    with col2:
        with st.container():
            doc_type = st.text_input("Document Type", key="doc_type", value=doc_type)

            print(f"current_index: {current_index}")
            print(f"ci1: {ci1}, ci2: {ci2}, ci3: {ci3}")
            class_1 = st.selectbox(
                "Class 1", doc_type_classes, key="class_1", index=ci1
            )
            class_2 = st.selectbox(
                "Class 2",
                doc_type_classes,
                key="class_2",
                index=ci2,  # len(classes) - 1
            )
            class_3 = st.selectbox(
                "Class 3",
                doc_type_classes,
                key="class_3",
                index=ci3,  # len(classes) - 1
            )

        with st.container():
            labels = [
                "section header",
                "title",
                "table of contents",
                "form field",
                "appendix title",
                "section title",
                "section description header",
                "clause list title",  # for the lines that say FAR clauses included...
                "contract type",
                "table",
                "other",
            ]
            with st.form(key="fields_form"):
                save_sections = []  # Save the annotated selections
                for i, rect in enumerate(result_rects.rects_data["words"]):
                    selected_text = get_selected_words(rect, image_state["words"])
                    joined_text = join_text(selected_text)

                    st.text_area(
                        f"Text {i + 1}",
                        joined_text,
                        key=f"text_{i}",
                        height=100,
                    )
                    st.selectbox(
                        f"Label {i + 1}",
                        labels,
                        key=f"label_{i}",
                    )
                    st.markdown("---")

                    save_sections.append(
                        {
                            "text": st.session_state.get(f"text_{i}", ""),
                            "label": st.session_state.get(f"label_{i}", ""),
                        }
                    )

                if (
                    (use_existing_annotations)
                    & (annotated_row is not None)
                    & (save_sections == [])
                ):
                    save_sections = parsed_text
                submit_button = st.form_submit_button(
                    "Save and Continue", type="primary"
                )
                back_button = st.form_submit_button("Back")
                next_index_button = st.form_submit_button("Next")
                # get indexes
                temp_index = st.session_state["config_data"].index.get_loc(
                    current_index
                )
                next_index = st.session_state["config_data"].iloc[temp_index + 1].name
                prev_index = st.session_state["config_data"].iloc[temp_index - 1].name
                # save or continue
                if submit_button:
                    st.session_state["annotated_config_data"] = save_and_continue(
                        config.loc[current_index],
                        [class_1, class_2, class_3],
                        save_sections,
                        doc_type,
                        st.session_state["save_file_path"],
                    )
                    # next_index = (current_index + 1) % len(config)
                    st.session_state["current_index"] = next_index
                    st.session_state.pop("image_state", None)
                    st.rerun()
                if back_button:
                    # prev_index = (current_index - 1) % len(config)
                    st.session_state["current_index"] = prev_index
                    st.session_state.pop("image_state", None)
                    st.rerun()
                if next_index_button:
                    # next_index = (current_index + 1) % len(config)
                    st.session_state["current_index"] = next_index
                    st.session_state.pop("image_state", None)
                    st.rerun()


def check_existing_classes(current_config_row, classes):
    index1 = 0
    index2 = classes.index("None")
    index3 = classes.index("None")
    try:
        if current_config_row["class_1"] in classes:
            index1 = classes.index(current_config_row["class_1"])
    except KeyError:
        print("KeyError")
        pass
    try:
        if current_config_row["class_2"] in classes:
            index2 = classes.index(current_config_row["class_2"])
    except KeyError:
        pass
    try:
        if current_config_row["class_3"] in classes:
            index3 = classes.index(current_config_row["class_3"])
    except KeyError:
        pass
    return index1, index2, index3


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
    config_file_name = "converted_files_sot01a_start7pages.csv"
    annotated_data_file_name = "annotated_files_sot01a.01.csv"

    data_file_dir = os.path.abspath(
        os.path.join(
            "..",
            "anx_llm_research",
            "fine_tuning",
            "modeling_data",
            "contract_files",
        )
    )
    save_file_path = os.path.join(data_file_dir, annotated_data_file_name)
    st.session_state.setdefault("data_file_dir", data_file_dir)
    st.session_state.setdefault("save_file_path", save_file_path)

    if "config_data" not in st.session_state:
        data_config_file_path = os.path.join(
            data_file_dir,
            config_file_name,
        )
        st.session_state["config_data"] = load_config_dataframe(data_config_file_path)

        st.session_state["annotated_config_data"] = (
            load_annotated_config_dataframe(save_file_path)
            if os.path.exists(save_file_path)
            else None
        )
        if st.session_state["annotated_config_data"] is not None:
            print(st.session_state["annotated_config_data"].index)
            annotated_index = max(st.session_state["annotated_config_data"].index)
            print(f"annotated_index: {annotated_index}")
            temp_index = st.session_state["config_data"].index.get_loc(annotated_index)
            config_index = st.session_state["config_data"].iloc[temp_index + 1].name
            st.session_state["current_index"] = config_index

    current_index = st.session_state.get("current_index", 0)
    run(
        st.session_state["config_data"].loc[current_index, "image_file_path"],
        st.session_state["config_data"].loc[current_index, "ocr_file_path"],
        st.session_state["config_data"],
        st.session_state["annotated_config_data"],
        current_index,
    )
