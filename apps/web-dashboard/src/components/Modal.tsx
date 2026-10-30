import React, { useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import { X } from 'lucide-react';

/*
 * Shared modal dialog.
 *
 * Rendered through a portal into <body>, so no ancestor can trap it: the layout row and notebook
 * area create their own stacking contexts (isolation: isolate), and a dialog rendered inside them
 * was painted underneath the top bar no matter how high its z-index. Layering comes from the
 * --z-modal token (above the top bar and popovers). Sizing is viewport-relative and the body scrolls
 * internally; Escape and backdrop clicks close only the topmost dialog; focus moves into the dialog,
 * stays there while tabbing, and returns to where it was when it closes.
 */

export type ModalSize = 'sm' | 'md' | 'lg' | 'xl' | 'full';
const MODAL_WIDTHS: Record<ModalSize, number> = { sm: 420, md: 560, lg: 720, xl: 960, full: 1240 };

// Open dialogs, innermost last: keyboard and backdrop handling apply to the topmost only
const openModalStack: symbol[] = [];

const FOCUSABLE =
  'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

interface ModalProps {
  onClose: () => void;
  /** Accessible name of the dialog. */
  label: string;
  size?: ModalSize;
  /** Fill the available height (dashboard-style dialogs) instead of fitting the content. */
  fullHeight?: boolean;
  closeOnBackdrop?: boolean;
  closeOnEscape?: boolean;
  /** data-testid for the backdrop element. */
  testId?: string;
  /** data-testid for the dialog panel. */
  panelTestId?: string;
  children: React.ReactNode;
}

export const Modal: React.FC<ModalProps> = ({
  onClose,
  label,
  size = 'md',
  fullHeight = false,
  closeOnBackdrop = true,
  closeOnEscape = true,
  testId,
  panelTestId,
  children,
}) => {
  const panelRef = useRef<HTMLDivElement>(null);
  const idRef = useRef(Symbol('modal'));
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;
  const backdropPressRef = useRef(false);

  useEffect(() => {
    const id = idRef.current;
    openModalStack.push(id);
    const previouslyFocused = document.activeElement as HTMLElement | null;

    // Move focus into the dialog unless its content already focused something (e.g. autoFocus)
    if (panelRef.current && !panelRef.current.contains(document.activeElement)) {
      panelRef.current.focus();
    }

    const isTopmost = () => openModalStack[openModalStack.length - 1] === id;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!isTopmost()) return;
      if (e.key === 'Escape' && closeOnEscape) {
        e.preventDefault();
        e.stopPropagation();
        onCloseRef.current();
        return;
      }
      if (e.key === 'Tab' && panelRef.current) {
        // Keep keyboard focus inside the dialog
        const focusable = Array.from(panelRef.current.querySelectorAll<HTMLElement>(FOCUSABLE)).filter(
          (el) => el.offsetParent !== null
        );
        if (focusable.length === 0) {
          e.preventDefault();
          return;
        }
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        const active = document.activeElement;
        if (e.shiftKey && (active === first || active === panelRef.current)) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && active === last) {
          e.preventDefault();
          first.focus();
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown, true);

    return () => {
      window.removeEventListener('keydown', handleKeyDown, true);
      const index = openModalStack.indexOf(id);
      if (index !== -1) openModalStack.splice(index, 1);
      if (previouslyFocused && document.contains(previouslyFocused)) previouslyFocused.focus();
    };
  }, [closeOnEscape]);

  return createPortal(
    <div
      className="pcs-modal-backdrop"
      data-testid={testId}
      // Close only when the press both starts and ends on the backdrop, so selecting text in an
      // input and releasing the mouse outside the dialog does not close it
      onMouseDown={(e) => {
        backdropPressRef.current = e.target === e.currentTarget;
      }}
      onClick={(e) => {
        const pressedBackdrop = backdropPressRef.current;
        backdropPressRef.current = false;
        if (closeOnBackdrop && pressedBackdrop && e.target === e.currentTarget) onClose();
      }}
    >
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-label={label}
        tabIndex={-1}
        data-testid={panelTestId}
        className={`pcs-modal${fullHeight ? ' pcs-modal--full-height' : ''}`}
        style={{ '--modal-width': `${MODAL_WIDTHS[size]}px` } as React.CSSProperties}
      >
        {children}
      </div>
    </div>,
    document.body
  );
};

interface ModalHeaderProps {
  title: React.ReactNode;
  subtitle?: React.ReactNode;
  icon?: React.ReactNode;
  /** Background of the icon tile, e.g. the feature's accent colour. */
  iconBackground?: string;
  /** Extra controls shown before the close button. */
  actions?: React.ReactNode;
  onClose?: () => void;
  closeLabel?: string;
}

export const ModalHeader: React.FC<ModalHeaderProps> = ({
  title,
  subtitle,
  icon,
  iconBackground,
  actions,
  onClose,
  closeLabel = 'Close',
}) => (
  <div className="pcs-modal-header">
    {icon && (
      <div className="pcs-modal-icon" style={iconBackground ? { backgroundColor: iconBackground, color: '#ffffff' } : undefined}>
        {icon}
      </div>
    )}
    <div className="pcs-modal-heading">
      <h2 className="pcs-modal-title">{title}</h2>
      {subtitle && <div className="pcs-modal-subtitle">{subtitle}</div>}
    </div>
    {actions && <div className="pcs-modal-actions">{actions}</div>}
    {onClose && (
      <button type="button" className="pcs-modal-close" onClick={onClose} aria-label={closeLabel} title={closeLabel}>
        <X size={16} />
      </button>
    )}
  </div>
);

export const ModalBody: React.FC<{ children: React.ReactNode; padded?: boolean }> = ({ children, padded = true }) => (
  <div className={`pcs-modal-body${padded ? '' : ' pcs-modal-body--flush'}`}>{children}</div>
);

export const ModalFooter: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div className="pcs-modal-footer">{children}</div>
);
