import { useEffect, useRef } from 'react';
import { useLocation } from 'react-router-dom';
import { pageTitle } from '../navigation';

export function usePageFocus() {
  const { pathname } = useLocation();
  const main = useRef<HTMLElement>(null);
  useEffect(() => {
    document.title = `${pageTitle(pathname)} | OrangeVision`;
    main.current?.focus();
  }, [pathname]);
  return main;
}
