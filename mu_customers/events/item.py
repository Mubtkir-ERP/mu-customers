def clear_auto_description(doc, method=None):
	if not doc.description:
		return
	desc = doc.description.strip()
	if desc == (doc.item_name or "").strip() or desc == (doc.item_code or "").strip():
		doc.description = ""
