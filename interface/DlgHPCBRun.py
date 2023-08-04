import logging
from pathlib import Path
from typing import Any, Callable, Dict

import wx

from ..cfgman import ConfigMan
from ..hdata import HierarchicalData, SchSheet
from .DlgHPCBRun_Base import DlgHPCBRun_Base

logger = logging.getLogger("hierpcb")


def set_checked_default(
    tree: wx.dataview.TreeListCtrl, sheet: SchSheet, ancestor_checked: bool = False
):
    """Set the tree to its default state starting from node `sheet`."""

    sheet.checked = False
    # Skip nodes that don't have list refs:
    if sheet.list_ref:
        # Check if the sheet has a PCB:
        if sheet.pcb and sheet.pcb.is_legal:
            # If an ancestor is checked, this sheet cannot be checked.
            # Otherwise, this is the first sheet from the root to be elligible,
            if not ancestor_checked:
                sheet.checked = True

        tree.SetItemBold(sheet.list_ref, sheet.checked)

    # Recur on the children:
    for _, child in sorted(sheet.children.items()):
        set_checked_default(tree, child, sheet.checked or ancestor_checked)


def is_checkable(tree: wx.dataview.TreeListCtrl, sheet: SchSheet) -> bool:
    """Check if the sheet may be checked."""
    if sheet.pcb and sheet.pcb.is_legal:
        # Now that we know it can be checked, verify that no ancestor is checked:
        node = sheet.parent
        while node is not None and node.list_ref is not None:
            logger.info(f"Checking {node.identifier}: {node.checked}.")
            if node.checked:
                return False
            node = node.parent
        return True
    return False


class DlgHPCBRun(DlgHPCBRun_Base):
    def __init__(self, cfg: ConfigMan, parent: wx.Window, hD: HierarchicalData):
        # Set up the user interface from the designer.
        super().__init__(parent)
        # Populate the dialog with data:
        self.hD = hD

        for sheet in hD.root_sheet.tree_iter(skip_root=True):
            # Look up the parent, if it is in the tree already.
            parent_item: wx.TreeListItem = (
                sheet.parent.list_ref or self.treeApplyTo.GetRootItem()
            )

            # If the sheet has a PCB, mention it in the appropriate column:
            row_text = sheet.human_name
            if sheet.pcb is not None:
                row_text += f": {sheet.pcb.path.relative_to(hD.basedir)}"
                if not sheet.pcb.is_legal:
                    row_text += " No Footprints!"

            item: wx.TreeListItem = self.treeApplyTo.AppendItem(
                parent=parent_item, text=row_text, data=sheet
            )

            # Add the sheet to the tree, in case it is a future parent:
            sheet.list_ref = item

        self.treeApplyTo.ExpandAll()

        # Set the default state of the tree:
        set_checked_default(self.treeApplyTo, hD.root_sheet)

        # Populate the list of available sub-PCBs:
        self.subPCBList.AppendTextColumn("Name")
        self.subPCBList.AppendTextColumn("Anchor Footprint")
        for _, subpcb in sorted(hD.pcb_rooms.items()):
            self.subPCBList.AppendItem(
                [subpcb.path.name, subpcb.get_heuristic_anchor_ref()]
            )

    def handleSelection(self, evt: wx.dataview.TreeListEvent):
        """Handle a click on a tree item."""
        item = evt.GetItem()
        # Get the sheet associated with the item:
        sheet: SchSheet = self.treeApplyTo.GetItemData(item)
        # If the sheet is now unchecked, do nothing:

        if is_checkable(self.treeApplyTo, sheet):
            if sheet.checked:
                sheet.checked = False
                self.treeApplyTo.SetItemBold(sheet.list_ref, sheet.checked)
            else:
                # Check it and uncheck all descendants:
                set_checked_default(self.treeApplyTo, sheet)

    def resetToDefault(self, event):
        """Reset the tree to its default state."""
        set_checked_default(self.treeApplyTo, self.hD.root_sheet)
