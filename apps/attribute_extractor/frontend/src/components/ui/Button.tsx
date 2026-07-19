import type { ReactNode } from 'react';

export function Button({
  children,
  variant = 'primary',
  disabled,
  onClick,
}: {
  children: ReactNode;
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger';
  disabled?: boolean;
  onClick?: () => void;
}) {
  return (
    <button className={`button button--${variant}`} disabled={disabled} type="button" onClick={(event) => {
      event.stopPropagation();
      onClick?.();
    }}>
      {children}
    </button>
  );
}
