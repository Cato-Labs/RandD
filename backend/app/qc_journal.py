"""QC turnover-inspection journal tools.

The agent records checklist outcomes and pins photos while the inspector walks
the property in ANY order. The frontend routes each call to the matching form
item by label (see frontend InspectionView). Photos come from the inspector's
live device camera: whatever the camera saw when the call is made.

CHECKLIST_ITEMS is the authoritative inventory of the live form
(frontend/public/inspection.html) — section -> exact item labels. Each item
holds ONE narrative note and up to three photos: one "before", one "after",
and "evidence" (default).
"""

from strands import tool

_VALID_RESULTS = ("PASS", "FAIL", "NA")
_VALID_TAGS = ("before", "after", "evidence")

# Exact labels from the live form. Keys are sections (with subsections flattened
# as "HouseKeeping / <group>"). Labels must be passed verbatim to the tools.
CHECKLIST_ITEMS: dict[str, list[str]] = {
    "Hot Tub": ["Up and Working", "Full", "Fresh", "Clear", "103"],
    "HouseKeeping / Kitchen": [
        "Dishes, glasses, and silverware are clean",
        "Pots, pans are clean",
        "Dishwasher is Empty",
        "Sink is Cleaned & Free from Food",
        "Garbage Disposal is Clear & Fresh",
        "Refrigerator is Cold and Clean",
        "Oven is Clean",
    ],
    "HouseKeeping / Bathrooms": [
        "Towels are displayed",
        "Floors are mopped",
        "Bath tub shower is clean",
        "Toilet is clean and fresh",
        "Sink and mirrors are wiped off",
    ],
    "HouseKeeping / Bedroom": [
        "All Beds are made properly w/ skirts",
        "Remotes are in holders",
        "Closets are organized",
    ],
    "HouseKeeping / Home": [
        "House smells Normal Fresh",
        "All surfaces cleaned or dusted",
        "All floor have been vacuumed or mopped.",
        "The house is clean and organized.",
        "The home is open and welcoming",
        "Carpets Look Good no Stains",
    ],
    "HouseKeeping / Outdoors": [
        "Walk ways and Drive way Cleaned off",
        "Garbage cans are Put Away",
        "Yard is Maintained",
        "BBQ has been Cleaned",
        "Outdoor furniture arranged",
        "Windows are presentable",
    ],
    "Utilities": ["Gas", "Wi-Fi", "Power", "Water"],
    "Gifts": ["Coffee & Cream", "Deodorant set up"],
}

_ALL_LABELS = {label for labels in CHECKLIST_ITEMS.values() for label in labels}


def _closest_label(item: str) -> str | None:
    """Exact match first, then case/whitespace-insensitive."""
    if item in _ALL_LABELS:
        return item
    folded = " ".join(item.lower().split())
    for label in _ALL_LABELS:
        if " ".join(label.lower().split()) == folded:
            return label
    return None


@tool
def list_checklist_items() -> str:
    """List every line item on the live turnover-inspection form, by section.

    Call this before recording results or attaching photos so you use the
    exact item labels the form expects. Each item holds one narrative note
    and up to three photos: one "before", one "after", and "evidence".

    Returns:
        str: Sections with their exact item labels.
    """
    lines = []
    for section, labels in CHECKLIST_ITEMS.items():
        lines.append(f"# {section}")
        lines.extend(f"- {label}" for label in labels)
    return "\n".join(lines)


@tool
def record_checklist_result(
    item: str,
    result: str,
    note: str = "",
    attach_photo: bool = False,
    photo_tag: str = "evidence",
) -> str:
    """Record one turnover-inspection checklist item on the live QC form.

    Call once per checklist item, in whatever order the inspector works.
    The form routes the update by the item's exact label (see
    list_checklist_items), checks/unchecks it, stores the note, and (when
    attach_photo is true) pins the latest device-camera frame to that item.

    Args:
        item: Exact checklist item label, e.g. "Oven is Clean".
        result: PASS, FAIL, or NA.
        note: The item's narrative note (one per item; replaces prior note).
        attach_photo: Attach the most recent camera frame to this item.
            Use for every FAIL, anything notable, and all safety items.
        photo_tag: "before", "after", or "evidence" (default).

    Returns:
        str: Confirmation of what was recorded.
    """
    label = _closest_label(item)
    if label is None:
        return (
            f"Unknown item {item!r} — call list_checklist_items and use an exact label."
        )
    result_upper = result.strip().upper()
    if result_upper not in _VALID_RESULTS:
        return f"Invalid result {result!r} — use PASS, FAIL, or NA."
    tag = photo_tag.strip().lower()
    if tag not in _VALID_TAGS:
        tag = "evidence"
    parts = [f"Recorded {label!r}: {result_upper}"]
    if note:
        parts.append(f"note saved: {note}")
    if attach_photo:
        parts.append(f"latest camera frame pinned as {tag}")
    return " — ".join(parts)


@tool
def attach_item_photo(item: str, photo_tag: str = "evidence", note: str = "") -> str:
    """Pin the photo you just took onto a specific form line item.

    Sends the most recent device-camera frame (the last streamed frame or
    snap) to the named checklist item. Each item holds up to three photos —
    one "before", one "after", and "evidence" (the default). Sending a new
    before/after photo replaces the previous one of that tag.

    Args:
        item: Exact checklist item label (see list_checklist_items).
        photo_tag: "before", "after", or "evidence" (default).
        note: Optionally also set/replace the item's narrative note.

    Returns:
        str: Confirmation of where the photo was pinned.
    """
    label = _closest_label(item)
    if label is None:
        return (
            f"Unknown item {item!r} — call list_checklist_items and use an exact label."
        )
    tag = photo_tag.strip().lower()
    if tag not in _VALID_TAGS:
        tag = "evidence"
    parts = [f"Latest camera frame pinned to {label!r} as {tag}"]
    if note:
        parts.append(f"note saved: {note}")
    return " — ".join(parts)
