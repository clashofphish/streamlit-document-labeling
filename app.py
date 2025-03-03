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

st.set_page_config(page_title="Sparrow Labeling", layout="wide")


def save_and_continue(config, current_index, selected_classes, result_rects):
    save_file = "annotations.csv"
    row = config.iloc[current_index]
    data = {
        "attachmentId": row["attachmentId"],
        "image_file_path": row["image_file_path"],
        "ocr_file_path": row["ocr_file_path"],
        "class_1": selected_classes[0],
        "class_2": selected_classes[1],
        "class_3": selected_classes[2],
        "rects_data": json.dumps(result_rects.rects_data),
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


def run(img_file, rects_file, labels, show_ocr_boxes, config, current_index):
    ui_width = st_js.st_javascript("window.innerWidth")

    docImg = Image.open(img_file)

    if (
        "saved_state" not in st.session_state
        or st.session_state["current_index"] != current_index
    ):
        with open(rects_file, "r") as f:
            saved_state = json.load(f)
            st.session_state["saved_state"] = saved_state
            st.session_state["current_index"] = current_index
    else:
        saved_state = st.session_state["saved_state"]

    assign_labels = st.checkbox("Assign Labels", True)
    mode = "transform" if assign_labels else "rect"

    data_processor = DataProcessor()

    col1, col2 = st.columns([4, 6])

    with col1:
        height = 1296  # 1024  # 1296
        width = 864  # 792  # 864

        doc_height = saved_state["meta"]["image_size"]["height"]
        doc_width = saved_state["meta"]["image_size"]["width"]

        canvas_width = canvas_available_width(ui_width)

        initial_rects = (
            saved_state
            if show_ocr_boxes
            else {"meta": saved_state["meta"], "words": []}
        )

        result_rects = st_sparrow_labeling(
            fill_color="rgba(0, 151, 255, 0.3)",
            stroke_width=2,
            stroke_color="rgba(0, 50, 255, 0.7)",
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
            "Check 'Assign Labels' to enable editing of labels and values, move and resize the boxes to "
            "annotate the document."
        )
        st.caption(
            "Add annotations by clicking and dragging on the document, when 'Assign Labels' is unchecked."
        )

    with col2:
        with st.container():
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
                with st.form(key="fields_form"):
                    if (
                        result_rects.current_rect_index is not None
                        and result_rects.current_rect_index != -1
                    ):
                        st.write(
                            "Selected Field: ",
                            result_rects.rects_data["words"][
                                result_rects.current_rect_index
                            ]["value"],
                        )
                        st.markdown("---")

                    if ui_width > 1500:
                        render_form_wide(
                            result_rects.rects_data["words"],
                            labels,
                            result_rects,
                            data_processor,
                        )
                    elif ui_width > 1000:
                        render_form_avg(
                            result_rects.rects_data["words"],
                            labels,
                            result_rects,
                            data_processor,
                        )
                    elif ui_width > 500:
                        render_form_narrow(
                            result_rects.rects_data["words"],
                            labels,
                            result_rects,
                            data_processor,
                        )
                    else:
                        render_form_mobile(
                            result_rects.rects_data["words"],
                            labels,
                            result_rects,
                            data_processor,
                        )

                    submit = st.form_submit_button("Save and Continue", type="primary")
                    back = st.form_submit_button("Back")
                    if submit:
                        save_and_continue(
                            config,
                            current_index,
                            [class_1, class_2, class_3],
                            result_rects,
                        )
                        next_index = (current_index + 1) % len(config)
                        st.session_state["current_index"] = next_index
                        st.session_state.pop("saved_state", None)
                        st.rerun()
                    if back:
                        prev_index = (current_index - 1) % len(config)
                        st.session_state["current_index"] = prev_index
                        st.session_state.pop("saved_state", None)
                        st.rerun()


def render_form_wide(words, labels, result_rects, data_processor):
    col1_form, col2_form, col3_form, col4_form = st.columns([1, 1, 1, 1])
    num_rows = math.ceil(len(words) / 4)

    for i, rect in enumerate(words):
        if i < num_rows:
            with col1_form:
                render_form_element(rect, labels, i, result_rects, data_processor)
        elif i < num_rows * 2:
            with col2_form:
                render_form_element(rect, labels, i, result_rects, data_processor)
        elif i < num_rows * 3:
            with col3_form:
                render_form_element(rect, labels, i, result_rects, data_processor)
        else:
            with col4_form:
                render_form_element(rect, labels, i, result_rects, data_processor)


def render_form_avg(words, labels, result_rects, data_processor):
    col1_form, col2_form, col3_form = st.columns([1, 1, 1])
    num_rows = math.ceil(len(words) / 3)

    for i, rect in enumerate(words):
        if i < num_rows:
            with col1_form:
                render_form_element(rect, labels, i, result_rects, data_processor)
        elif i < num_rows * 2:
            with col2_form:
                render_form_element(rect, labels, i, result_rects, data_processor)
        else:
            with col3_form:
                render_form_element(rect, labels, i, result_rects, data_processor)


def render_form_narrow(words, labels, result_rects, data_processor):
    col1_form, col2_form = st.columns([1, 1])
    num_rows = math.ceil(len(words) / 2)

    for i, rect in enumerate(words):
        if i < num_rows:
            with col1_form:
                render_form_element(rect, labels, i, result_rects, data_processor)
        else:
            with col2_form:
                render_form_element(rect, labels, i, result_rects, data_processor)


def render_form_mobile(words, labels, result_rects, data_processor):
    for i, rect in enumerate(words):
        render_form_element(rect, labels, i, result_rects, data_processor)


def render_form_element(rect, labels, i, result_rects, data_processor):
    print(f"**Rect example: {rect}")
    default_index = 0
    if rect["label"]:
        default_index = labels.index(rect["labels"])

    value = st.text_input(
        "Value",
        rect["value"],
        key=f"field_value_{i}",
        disabled=False if i == result_rects.current_rect_index else True,
    )
    label = st.selectbox(
        "Label",
        labels,
        key=f"label_{i}",
        index=default_index,
        disabled=False if i == result_rects.current_rect_index else True,
    )
    st.markdown("---")

    data_processor.update_rect_data(result_rects.rects_data, i, value, label)


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

    show_ocr_boxes = st.checkbox("Show OCR Boxes", True)
    current_index = st.session_state.get("current_index", 0)
    run(
        config.loc[current_index, "image_file_path"],
        config.loc[current_index, "ocr_file_path"],
        custom_labels,
        show_ocr_boxes,
        config,
        current_index,
    )
