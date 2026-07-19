"""Shared scalar dedoc parse parameters for OCR and benchmark traceability."""

DEDOC_SCALAR_PARAMETERS: dict[str, str] = {
    "pdf_with_text_layer": "auto_tabby",
    "each_page_textual_layer_detection": "True",
    "document_type": "other",
    "structure_type": "tree",
    "need_pdf_table_analysis": "True",
    "need_gost_frame_analysis": "True",
    "need_header_footer_analysis": "True",
    "with_attachments": "True",
}
