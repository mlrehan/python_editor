interface EditSnapshot {
  value: string;
  selectionStart: number;
  selectionEnd: number;
}

interface EditRecord {
  before: EditSnapshot;
  after: EditSnapshot;
}

// Recent programmatic edits per textarea, used to restore their selections on undo/redo
const MAX_RECORDS = 200;
const editRecords = new WeakMap<HTMLTextAreaElement, EditRecord[]>();

// Native undo/redo puts the text back but leaves its own selection (often just the changed range or
// a collapsed caret). Like VS Code, restore the selection the user had in that state, so e.g. a
// multi-line selection stays selected after undoing Ctrl+/.
function handleHistoryInput(this: HTMLTextAreaElement, event: Event) {
  const inputType = (event as InputEvent).inputType;
  if (inputType !== 'historyUndo' && inputType !== 'historyRedo') return;
  const records = editRecords.get(this);
  if (!records) return;
  const value = this.value;
  for (let i = records.length - 1; i >= 0; i--) {
    const snapshot = inputType === 'historyUndo' ? records[i].before : records[i].after;
    if (snapshot.value === value) {
      this.setSelectionRange(snapshot.selectionStart, snapshot.selectionEnd);
      return;
    }
  }
}

function remember(el: HTMLTextAreaElement, record: EditRecord) {
  let records = editRecords.get(el);
  if (!records) {
    records = [];
    editRecords.set(el, records);
    el.addEventListener('input', handleHistoryInput);
  }
  records.push(record);
  if (records.length > MAX_RECORDS) records.splice(0, records.length - MAX_RECORDS);
}

/**
 * Applies a programmatic edit to a <textarea> so it becomes part of the browser's native undo/redo
 * history (Ctrl+Z, Ctrl+Shift+Z, Ctrl+Y), exactly like typing.
 *
 * Assigning `el.value = ...` bypasses the browser's editing pipeline: the change is not recorded
 * and Chromium even discards the existing undo history. Instead, only the smallest changed range is
 * selected and replaced with the native `insertText` / `delete` editing commands, which the browser
 * records as one undoable step (and which fire a normal `input` event). The selections before and
 * after the edit are restored when undo/redo returns to those states.
 *
 * Returns true when the edit went through the native history; false when the browser does not
 * support it and the value had to be assigned directly (the edit still applies, without undo).
 */
export function applyTextareaEdit(
  el: HTMLTextAreaElement,
  newValue: string,
  selectionStart: number,
  selectionEnd: number = selectionStart
): boolean {
  const oldValue = el.value;
  const before: EditSnapshot = { value: oldValue, selectionStart: el.selectionStart, selectionEnd: el.selectionEnd };
  let recorded = true;

  if (oldValue !== newValue) {
    // Smallest range that differs: common prefix and (non-overlapping) common suffix
    const limit = Math.min(oldValue.length, newValue.length);
    let prefix = 0;
    while (prefix < limit && oldValue[prefix] === newValue[prefix]) prefix++;
    let suffix = 0;
    while (
      suffix < limit - prefix &&
      oldValue[oldValue.length - 1 - suffix] === newValue[newValue.length - 1 - suffix]
    ) {
      suffix++;
    }
    const replaceEnd = oldValue.length - suffix;
    const insertion = newValue.substring(prefix, newValue.length - suffix);

    if (document.activeElement !== el) el.focus();
    el.setSelectionRange(prefix, replaceEnd);
    try {
      recorded =
        insertion.length > 0
          ? document.execCommand('insertText', false, insertion)
          : document.execCommand('delete', false);
    } catch {
      recorded = false;
    }
    if (!recorded || el.value !== newValue) {
      recorded = false;
      el.value = newValue;
    }
  }

  el.setSelectionRange(selectionStart, selectionEnd);
  if (recorded && oldValue !== newValue) {
    remember(el, { before, after: { value: newValue, selectionStart, selectionEnd } });
  }
  return recorded;
}
